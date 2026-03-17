"""
Binary Blob Decoder: byte blob -> structured data.

Reverses the BlobEncoder to reconstruct all document components
from the compressed binary format.
"""

import struct
from typing import List, Tuple, Optional
from dataclasses import dataclass

from ..pipeline.config import VERSION, FLAG_HAS_UNKNOWN_WORDS
from ..wordid.word_id_codec import WordIdCodec
from ..wordid.unknown_handler import UnknownHandler
from ..serializer.encoder import WordEntry, PunctEntry
from .bitpack import unpack_positions, packed_size


@dataclass
class DecodedBlob:
    """All data extracted from a compressed blob."""
    version: int
    total_tokens: int
    unique_words: int
    line_count: int
    checksum: int
    flags: int
    word_entries: List[WordEntry]
    cap_bitmap: bytes
    punct_entries: List[PunctEntry]
    morph_flags: dict = None  # {token_index: flag} sparse map
    blank_data: dict = None   # {blanks: [...], partition_checksums: {...}}


class BlobDecoder:

    def __init__(self):
        self.codec = WordIdCodec()

    def decode(self, blob: bytes) -> DecodedBlob:
        """Decode a compressed blob back into structured data."""
        # Parse header (16 bytes)
        if len(blob) < 16:
            raise ValueError(f"Blob too small for header: {len(blob)} bytes")

        (version, total_tokens, unique_words, line_count,
         checksum, word_table_len, _reserved, flags) = struct.unpack(
            '>BHHHIHHB', blob[:16]
        )

        if version != VERSION:
            raise ValueError(f"Unsupported version: {version}")

        offset = 16  # skip header (14 bytes + 2 padding)

        # Parse word table
        from ..pipeline.config import FLAG_BITPACKED_POSITIONS
        bitpacked = bool(flags & FLAG_BITPACKED_POSITIONS)
        word_table_end = offset + word_table_len
        word_entries = self._decode_word_table(blob, offset, word_table_end, unique_words, bitpacked)
        offset = word_table_end

        # Parse structural metadata
        cap_bitmap, punct_entries, morph_flags, blank_data, offset = (
            self._decode_structural_metadata(blob, offset, total_tokens)
        )

        return DecodedBlob(
            version=version,
            total_tokens=total_tokens,
            unique_words=unique_words,
            line_count=line_count,
            checksum=checksum,
            flags=flags,
            word_entries=word_entries,
            cap_bitmap=cap_bitmap,
            punct_entries=punct_entries,
            morph_flags=morph_flags,
            blank_data=blank_data,
        )

    def _decode_word_table(
        self, data: bytes, offset: int, end: int, count: int,
        bitpacked: bool = False
    ) -> List[WordEntry]:
        """Decode the word table section."""
        entries = []

        for _ in range(count):
            if offset >= end:
                break

            # Decode word ID
            if self.codec.is_unknown_marker(data, offset):
                word, consumed = UnknownHandler.decode(data, offset)
                offset += consumed
                rank = None
            else:
                rank, consumed = self.codec.decode_rank(data, offset)
                offset += consumed
                word = ""  # will be resolved from dictionary

            if bitpacked:
                # New compact format: [count:1] [bitpacked 11-bit positions]
                pos_count = data[offset]
                offset += 1
                psize = packed_size(pos_count)
                packed_data = data[offset:offset + psize]
                combined = unpack_positions(packed_data, pos_count)
                offset += psize

                vert_positions = [p[0] for p in combined]
                horiz_positions = [p[1] for p in combined]

                entries.append(WordEntry(
                    rank=rank,
                    word=word,
                    vert_positions=vert_positions,
                    horiz_positions=horiz_positions,
                    combined_positions=combined,
                ))
            else:
                # Legacy format: separate vert/horiz with length headers
                vert_len = struct.unpack('>H', data[offset:offset + 2])[0]
                offset += 2
                vert_raw = data[offset:offset + vert_len]
                vert_positions = self._decode_positions_raw(data, offset, vert_len)
                offset += vert_len

                horiz_len = struct.unpack('>H', data[offset:offset + 2])[0]
                offset += 2
                horiz_raw = data[offset:offset + horiz_len]
                horiz_positions = self._decode_positions_raw(data, offset, horiz_len)
                offset += horiz_len

                entries.append(WordEntry(
                    rank=rank,
                    word=word,
                    vert_positions=vert_positions,
                    horiz_positions=horiz_positions,
                    vert_encoded=vert_raw,
                    horiz_encoded=horiz_raw,
                ))

        return entries

    def _decode_positions_raw(self, data: bytes, offset: int, length: int) -> List[int]:
        """Phase 1: decode raw uint16 positions."""
        positions = []
        end = offset + length
        while offset + 1 < end:
            pos = struct.unpack('>H', data[offset:offset + 2])[0]
            positions.append(pos)
            offset += 2
        return positions

    def _decode_structural_metadata(
        self, data: bytes, offset: int, total_tokens: int
    ) -> Tuple[bytes, List[PunctEntry], dict, dict, int]:
        """Decode capitalization bitmap, punctuation table, and morph flags."""
        # Capitalization bitmap
        bitmap_len = (total_tokens + 7) // 8
        cap_bitmap = data[offset:offset + bitmap_len]
        offset += bitmap_len

        # Punctuation table
        if offset + 2 > len(data):
            return cap_bitmap, [], {}, offset

        punct_count = struct.unpack('>H', data[offset:offset + 2])[0]
        offset += 2

        punct_entries = []
        for _ in range(punct_count):
            if offset + 2 > len(data):
                break
            token_idx = struct.unpack('>H', data[offset:offset + 2])[0]
            offset += 2

            lead_len = data[offset]
            offset += 1
            leading = data[offset:offset + lead_len].decode('utf-8')
            offset += lead_len

            trail_len = data[offset]
            offset += 1
            trailing = data[offset:offset + trail_len].decode('utf-8')
            offset += trail_len

            punct_entries.append(PunctEntry(
                token_index=token_idx,
                leading_punct=leading,
                trailing_punct=trailing,
            ))

        # Morphology flags (sparse: {token_index: flag})
        morph_flags = {}
        if offset + 2 <= len(data):
            morph_count = struct.unpack('>H', data[offset:offset + 2])[0]
            offset += 2
            for _ in range(morph_count):
                if offset + 3 > len(data):
                    break
                idx = struct.unpack('>H', data[offset:offset + 2])[0]
                offset += 2
                flag = data[offset]
                offset += 1
                morph_flags[idx] = flag

        # Blank data (Phase 4): line_word_counts + constraint markers
        blank_data = None
        if offset + 2 <= len(data):
            lwc_count = struct.unpack('>H', data[offset:offset + 2])[0]
            offset += 2

            if lwc_count > 0:
                # Read line word counts
                line_word_counts = []
                for _ in range(lwc_count):
                    line_word_counts.append(data[offset])
                    offset += 1

                # Read blank count
                blank_count = struct.unpack('>H', data[offset:offset + 2])[0]
                offset += 2

                blanks = []
                for _ in range(blank_count):
                    # Constraint bytes (length-prefixed)
                    cb_len = struct.unpack('>H', data[offset:offset + 2])[0]
                    offset += 2
                    constraint_bytes = data[offset:offset + cb_len]
                    offset += cb_len
                    # Occurrence count
                    occ_count = struct.unpack('>H', data[offset:offset + 2])[0]
                    offset += 2
                    blanks.append({
                        'constraint_bytes': constraint_bytes,
                        'occurrence_count': occ_count,
                    })

                # Read gap assignment
                gap_count = struct.unpack('>H', data[offset:offset + 2])[0]
                offset += 2
                gap_assignment = []
                for _ in range(gap_count):
                    gap_assignment.append(data[offset])
                    offset += 1

                blank_data = {
                    'line_word_counts': line_word_counts,
                    'blanks': blanks,
                    'gap_assignment': gap_assignment,
                }

        return cap_bitmap, punct_entries, morph_flags, blank_data, offset
