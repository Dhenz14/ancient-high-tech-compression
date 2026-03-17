"""
Binary Blob Encoder: structured data -> byte blob.

Format:
  [HEADER 16 bytes] [WORD TABLE variable] [STRUCTURAL METADATA variable]

Word table entries store pre-encoded position bytes (from coordinate encoder
or raw uint16 fallback). The serializer is encoding-agnostic.
"""

import struct
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

from ..pipeline.config import VERSION, FLAG_HAS_UNKNOWN_WORDS
from ..wordid.word_id_codec import WordIdCodec
from ..wordid.unknown_handler import UnknownHandler
from .bitpack import pack_positions, packed_size


@dataclass
class WordEntry:
    """A word's encoding data for serialization."""
    rank: Optional[int]             # None if unknown word
    word: str                       # the actual word (needed for unknowns)
    vert_positions: List[int]       # vertical (line) positions (raw)
    horiz_positions: List[int]      # horizontal (word index) positions (raw)
    vert_encoded: Optional[bytes] = None   # pre-encoded vertical bytes
    horiz_encoded: Optional[bytes] = None  # pre-encoded horizontal bytes
    combined_positions: Optional[List[tuple]] = None  # (row, slot) pairs for bitpacking


@dataclass
class PunctEntry:
    """Punctuation attached to a token."""
    token_index: int
    leading_punct: str
    trailing_punct: str


class BlobEncoder:

    def __init__(self):
        self.codec = WordIdCodec()

    def encode(
        self,
        word_entries: List[WordEntry],
        total_tokens: int,
        line_count: int,
        checksum: int,
        cap_bitmap: bytes,
        punct_entries: List[PunctEntry],
        morph_flags: Optional[List[int]] = None,
        blank_data: Optional[dict] = None,
    ) -> bytes:
        """
        Encode all data into a single binary blob.

        Returns the complete compressed byte blob.
        """
        # Encode word table
        word_table_bytes = self._encode_word_table(word_entries)

        # Encode structural metadata
        struct_bytes = self._encode_structural_metadata(
            cap_bitmap, punct_entries, morph_flags, blank_data
        )

        # Check for unknown words and morphology
        flags = 0
        for entry in word_entries:
            if entry.rank is None:
                flags |= FLAG_HAS_UNKNOWN_WORDS
                break
        if morph_flags and any(f != 0 for f in morph_flags):
            from ..pipeline.config import FLAG_HAS_MORPHOLOGY
            flags |= FLAG_HAS_MORPHOLOGY
        if blank_data:
            from ..pipeline.config import FLAG_HAS_BLANKS
            flags |= FLAG_HAS_BLANKS
        # Check if any entry uses bitpacked positions
        if any(e.combined_positions is not None for e in word_entries):
            from ..pipeline.config import FLAG_BITPACKED_POSITIONS
            flags |= FLAG_BITPACKED_POSITIONS

        # Build header (16 bytes exactly)
        # Format: B(1)+H(2)+H(2)+H(2)+I(4)+H(2)+H(2)+B(1) = 16
        header = struct.pack('>BHHHIHHB',
            VERSION,                    # B:  uint8  version
            total_tokens,               # H:  uint16 total tokens
            len(word_entries),           # H:  uint16 unique words
            line_count,                 # H:  uint16 line count
            checksum & 0xFFFFFFFF,      # I:  uint32 checksum
            len(word_table_bytes),      # H:  uint16 word table length
            0,                          # H:  uint16 reserved
            flags,                      # B:  uint8  flags
        )

        return header + word_table_bytes + struct_bytes

    def _encode_word_table(self, entries: List[WordEntry]) -> bytes:
        """Encode the word table section."""
        buf = bytearray()

        for entry in entries:
            # Word ID
            if entry.rank is not None:
                buf.extend(self.codec.encode_rank(entry.rank))
            else:
                buf.extend(UnknownHandler.encode(entry.word))

            # Positions: use bitpacked combined if available, else legacy separate
            if entry.combined_positions is not None:
                # New compact format: [count:1] [bitpacked 11-bit positions]
                count = len(entry.combined_positions)
                packed = pack_positions(entry.combined_positions)
                buf.append(count & 0xFF)
                buf.extend(packed)
            else:
                # Legacy format: separate vert/horiz with length headers
                if entry.vert_encoded is not None:
                    vert_bytes = entry.vert_encoded
                else:
                    vert_bytes = self._encode_positions_raw(entry.vert_positions)
                buf.extend(struct.pack('>H', len(vert_bytes)))
                buf.extend(vert_bytes)

                if entry.horiz_encoded is not None:
                    horiz_bytes = entry.horiz_encoded
                else:
                    horiz_bytes = self._encode_positions_raw(entry.horiz_positions)
                buf.extend(struct.pack('>H', len(horiz_bytes)))
                buf.extend(horiz_bytes)

        return bytes(buf)

    def _encode_positions_raw(self, positions: List[int]) -> bytes:
        """Phase 1: encode positions as raw uint16 values."""
        buf = bytearray()
        for pos in positions:
            buf.extend(struct.pack('>H', pos))
        return bytes(buf)

    def _encode_structural_metadata(
        self, cap_bitmap: bytes, punct_entries: List[PunctEntry],
        morph_flags: Optional[List[int]] = None,
        blank_data: Optional[dict] = None,
    ) -> bytes:
        """Encode capitalization bitmap, punctuation table, and morph flags."""
        buf = bytearray()

        # Capitalization bitmap
        buf.extend(cap_bitmap)

        # Punctuation table
        active = [p for p in punct_entries if p.leading_punct or p.trailing_punct]
        buf.extend(struct.pack('>H', len(active)))

        for entry in active:
            buf.extend(struct.pack('>H', entry.token_index))
            lead_bytes = entry.leading_punct.encode('utf-8')
            trail_bytes = entry.trailing_punct.encode('utf-8')
            buf.append(len(lead_bytes))
            buf.extend(lead_bytes)
            buf.append(len(trail_bytes))
            buf.extend(trail_bytes)

        # Morphology flags (Phase 3): sparse encoding
        if morph_flags:
            active_morph = [(i, f) for i, f in enumerate(morph_flags) if f != 0]
            buf.extend(struct.pack('>H', len(active_morph)))
            for idx, flag in active_morph:
                buf.extend(struct.pack('>H', idx))
                buf.append(flag)
        else:
            buf.extend(struct.pack('>H', 0))

        # Blank data (Phase 4): line_word_counts + blanked word constraints
        if blank_data and blank_data.get('blanks'):
            blanks = blank_data['blanks']
            line_word_counts = blank_data.get('line_word_counts', [])

            # Line word counts: [count, count, ...] as uint8 per line
            # This lets the decoder reconstruct the full grid and find gaps
            buf.extend(struct.pack('>H', len(line_word_counts)))
            for count in line_word_counts:
                buf.append(min(count, 255))

            # Number of blanked words
            buf.extend(struct.pack('>H', len(blanks)))

            # Each blank: constraint_bytes + occurrence_count(uint16)
            for blank in blanks:
                constraint_bytes = blank['constraint_bytes']
                buf.extend(struct.pack('>H', len(constraint_bytes)))
                buf.extend(constraint_bytes)
                buf.extend(struct.pack('>H', blank['occurrence_count']))

            # Gap assignment: 1 byte per gap, value = blank_index
            gap_assignment = blank_data.get('gap_assignment', [])
            buf.extend(struct.pack('>H', len(gap_assignment)))
            for idx in gap_assignment:
                buf.append(idx & 0xFF)
        else:
            buf.extend(struct.pack('>H', 0))  # zero line counts = no blanks

        return bytes(buf)


def build_cap_bitmap(is_capitalized: List[bool]) -> bytes:
    """Build capitalization bitmap from list of booleans."""
    n_bytes = (len(is_capitalized) + 7) // 8
    bitmap = bytearray(n_bytes)
    for i, is_cap in enumerate(is_capitalized):
        if is_cap:
            byte_idx = i // 8
            bit_idx = 7 - (i % 8)
            bitmap[byte_idx] |= (1 << bit_idx)
    return bytes(bitmap)
