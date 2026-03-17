"""
Sequential Rank Stream Decoder.

Supports v3 (merged varint) and v2 (legacy merged varint) formats.

v3 extra section stores words with ORIGINAL CASING (no transformation needed).
v2 extra section stores lowercased words (title case applied from variant bit).
"""

from typing import Optional
from ..wordid.dictionary import Dictionary

VERSION_V3 = 0x03
VERSION_V2 = 0x02

VARIANT_MULT = 32

# Trailing punct code -> string
_TRAIL_STR = {
    0:  "",
    1:  ".",
    2:  ",",
    3:  "!",
    4:  "?",
    5:  ";",
    6:  ":",
    7:  '"',
    8:  "'",
    9:  ")",
    10: "]",
    11: "-",
    12: "...",
    13: '."',
    14: ',"',
    15: '?"',
}


def _decode_varint(data: bytes, offset: int):
    """LEB128 varint decode. Returns (value, bytes_consumed)."""
    value = 0
    shift = 0
    consumed = 0
    while offset < len(data):
        byte = data[offset]
        value |= (byte & 0x7F) << shift
        offset += 1
        consumed += 1
        shift += 7
        if not (byte & 0x80):
            break
    return value, consumed


class SequentialDecoder:
    """Decode a sequential rank stream blob to text."""

    def __init__(self, dictionary: Optional[Dictionary] = None):
        self.dictionary = dictionary or Dictionary()

    def decode(self, blob: bytes) -> str:
        """Decode blob to text. Handles v3 and v2 formats."""
        if not blob or len(blob) < 4:
            return ""

        version = blob[0]
        if version == VERSION_V3:
            return self._decode_v3(blob)
        elif version == VERSION_V2:
            return self._decode_v2(blob)
        else:
            raise ValueError("Unsupported sequential format version: %d" % version)

    def _decode_v3(self, blob: bytes) -> str:
        """
        Decode v3 merged-varint blob.

        Layout: [0x03][count:3][main_stream][extra_section]
          main_stream: LEB128 per token, = rank*32 + variant
            - rank=0: extra section word (original casing, trailing from variant)
            - rank>0: known word (title case from caps bit, trailing from lower 4 bits)
          extra_section: length-prefixed UTF-8 strings with original casing
        """
        count = (blob[1] << 16) | (blob[2] << 8) | blob[3]
        if count == 0:
            return ""

        # Pass 1: scan main stream, record all token data
        offset = 4
        token_data = []  # (rank, is_cap, trail_code)

        for _ in range(count):
            if offset >= len(blob):
                token_data.append((0, False, 0))
                continue
            unified, consumed = _decode_varint(blob, offset)
            offset += consumed

            rank = unified // VARIANT_MULT
            variant = unified % VARIANT_MULT
            is_cap = bool(variant & 0x10)
            trail = variant & 0x0F
            token_data.append((rank, is_cap, trail))

        # Pass 2: read extra section (original-cased words)
        extra_words = []
        while offset < len(blob):
            if offset >= len(blob):
                break
            wlen = blob[offset]
            offset += 1
            if offset + wlen > len(blob):
                break
            word = blob[offset:offset + wlen].decode('utf-8', errors='replace')
            extra_words.append(word)
            offset += wlen

        # Pass 3: reconstruct
        extra_idx = 0
        words = []

        for rank, is_cap, trail in token_data:
            if rank == 0:
                # Extra section: original casing preserved, no transformation
                if extra_idx < len(extra_words):
                    word = extra_words[extra_idx]
                    extra_idx += 1
                else:
                    word = "[UNK]"
            else:
                word = self.dictionary.rank_to_word(rank)
                if word is None:
                    word = "[RANK:%d]" % rank
                # Apply title case if caps bit set
                if is_cap and word and word[0].islower():
                    word = word[0].upper() + word[1:]

            trailing = _TRAIL_STR.get(trail, "")
            words.append(word + trailing)

        return " ".join(words)

    def _decode_v2(self, blob: bytes) -> str:
        """
        Decode v2 legacy blob.

        Layout: [0x02][count:3][merged_varint_stream]
          rank=0 + variant in stream → unknown word with inline bytes (lowercased)
          Caps bit applies title case; ALL CAPS not supported in v2.
        """
        _V2_TRAIL_STR = {
            0: "", 1: ".", 2: ",", 3: "!", 4: "?", 5: ";", 6: ":",
            7: "",   # open quote (v2 didn't encode leading punct — limitation)
            8: '"',  # close quote
            9: "",   # open paren
            10: ")", 11: "-", 12: "...",
        }

        count = (blob[1] << 16) | (blob[2] << 8) | blob[3]
        if count == 0:
            return ""

        offset = 4
        words = []

        for _ in range(count):
            if offset >= len(blob):
                break
            unified, consumed = _decode_varint(blob, offset)
            offset += consumed

            rank = unified // 32
            variant = unified % 32
            is_cap = bool(variant & 0x10)
            trail = variant & 0x0F

            if rank == 0:
                if offset < len(blob):
                    wlen = blob[offset]
                    offset += 1
                    word = blob[offset:offset + wlen].decode('utf-8', errors='replace')
                    offset += wlen
                else:
                    word = "[UNK]"
                if is_cap and word and word[0].islower():
                    word = word[0].upper() + word[1:]
            else:
                word = self.dictionary.rank_to_word(rank)
                if word is None:
                    word = "[RANK:%d]" % rank
                if is_cap and word and word[0].islower():
                    word = word[0].upper() + word[1:]

            trailing = _V2_TRAIL_STR.get(trail, "")
            words.append(word + trailing)

        return " ".join(words)
