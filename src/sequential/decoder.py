"""
Sequential Rank Stream Decoder.

Supports v4 (current), v3 (previous), and v2 (legacy) formats.

v4: VARIANT_MULT=16, 4-bit variant [caps:1][trailing:3], 8 trailing codes.
    Rare trailing stored in extra section word (trailing appended to stored word).
v3: VARIANT_MULT=32, 5-bit variant [caps:1][trailing:4], 16 trailing codes.
    Extra section stores words with ORIGINAL CASING.
v2: VARIANT_MULT=32, inline word bytes for rank=0 tokens (lowercased).
"""

from typing import Optional
from ..wordid.dictionary import Dictionary


VERSION_V4 = 0x04
VERSION_V3 = 0x03
VERSION_V2 = 0x02

# v3 trailing codes — hardcoded for backward compat, do not change
_TRAIL_STR_V3 = {
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

# v4 trailing codes (3 bits, 8 values — rare trailing is in extra section word)
_TRAIL_STR_V4 = {
    0: "",    # T_NONE
    1: ".",   # T_PERIOD
    2: ",",   # T_COMMA
    3: "!",   # T_EXCLAIM
    4: "?",   # T_QUESTION
    5: "'",   # T_SQUOTE
    6: '"',   # T_DQUOTE
    7: '."',  # T_PERIOD_DQ
}

# Keep for any external code that imports _TRAIL_STR from this module
_TRAIL_STR = _TRAIL_STR_V3


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
        """Decode blob to text. Handles v4, v3, and v2 formats."""
        if not blob or len(blob) < 4:
            return ""

        version = blob[0]
        if version == VERSION_V4:
            return self._decode_v4(blob)
        elif version == 0x05:
            return self._decode_v5(blob)
        elif version == VERSION_V3:
            return self._decode_v3(blob)
        elif version == VERSION_V2:
            return self._decode_v2(blob)
        else:
            raise ValueError("Unsupported sequential format version: %d" % version)

    def _decode_v4(self, blob: bytes) -> str:
        """
        Decode v4 merged-varint blob.

        Layout: [0x04][count:3][main_stream][extra_section]
          unified = rank * 16 + variant  (VARIANT_MULT=16)
          variant: 4-bit — bit 3 = caps, bits 0-2 = trailing code (0-7)
          rank=0: extra section word (original casing; rare trailing appended by encoder)
          rank>0: known word (title case from caps bit, trailing from lower 3 bits)
        """
        _VM = 16
        count = (blob[1] << 16) | (blob[2] << 8) | blob[3]
        if count == 0:
            return ""

        # Pass 1: scan main stream
        offset = 4
        token_data = []  # (rank, is_cap, trail_code)

        for _ in range(count):
            if offset >= len(blob):
                token_data.append((0, False, 0))
                continue
            unified, consumed = _decode_varint(blob, offset)
            offset += consumed

            rank = unified // _VM
            variant = unified % _VM
            is_cap = bool((variant >> 3) & 1)  # bit 3
            trail = variant & 0x07              # bits 0-2
            token_data.append((rank, is_cap, trail))

        # Pass 2: read extra section
        extra_words = []
        while offset < len(blob):
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
                # Extra section: original casing (and rare trailing) already in word
                if extra_idx < len(extra_words):
                    word = extra_words[extra_idx]
                    extra_idx += 1
                else:
                    word = "[UNK]"
            else:
                word = self.dictionary.rank_to_word(rank)
                if word is None:
                    word = "[RANK:%d]" % rank
                if is_cap and word and word[0].islower():
                    word = word[0].upper() + word[1:]

            trailing = _TRAIL_STR_V4.get(trail, "")
            words.append(word + trailing)

        return " ".join(words)

    def _decode_v5(self, blob: bytes) -> str:
        """
        Decode v5 blank-system blob.

        Layout: [0x05][count:3][n_blanks:2][blank_section:n_blanks*2][main_stream][extra_section]

        blank_section entries (2 bytes each):
          [rank: 1]       -- tier-1 rank (1-7)
          [delta_pos: 1]  -- position delta from previous blank (or from 0)

        The decoder interleaves blanked tokens back into the stream at their
        original positions. Blanked tokens are always: caps=lower, trail=T_NONE.
        """
        _VM = 16
        if len(blob) < 6:
            return ""

        count = (blob[1] << 16) | (blob[2] << 8) | blob[3]
        if count == 0:
            return ""

        n_blanks = (blob[4] << 8) | blob[5]
        offset = 6

        # Read blank section: reconstruct (absolute_position, rank) pairs
        blanks = {}  # position -> rank
        abs_pos = 0
        for _ in range(n_blanks):
            if offset + 1 >= len(blob):
                break
            rank = blob[offset]
            delta = blob[offset + 1]
            abs_pos += delta
            blanks[abs_pos] = rank
            offset += 2

        # Read main stream (non-blank tokens)
        n_main = count - n_blanks
        main_token_data = []  # (rank, is_cap, trail)
        for _ in range(n_main):
            if offset >= len(blob):
                main_token_data.append((0, False, 0))
                continue
            unified, consumed = _decode_varint(blob, offset)
            offset += consumed
            rank = unified // _VM
            variant = unified % _VM
            is_cap = bool((variant >> 3) & 1)
            trail = variant & 0x07
            main_token_data.append((rank, is_cap, trail))

        # Read extra section
        extra_words = []
        while offset < len(blob):
            wlen = blob[offset]
            offset += 1
            if offset + wlen > len(blob):
                break
            word = blob[offset:offset + wlen].decode('utf-8', errors='replace')
            extra_words.append(word)
            offset += wlen

        # Reconstruct all tokens in order
        extra_idx = 0
        main_idx = 0
        words = []

        for token_pos in range(count):
            if token_pos in blanks:
                # This is a blanked tier-1 token
                rank = blanks[token_pos]
                word = self.dictionary.rank_to_word(rank)
                if word is None:
                    word = "[RANK:%d]" % rank
                # Blanked tokens are always lowercase, no trailing
                words.append(word)
            else:
                # Normal main-stream token
                if main_idx >= len(main_token_data):
                    words.append("[MISSING]")
                    main_idx += 1
                    continue
                rank, is_cap, trail = main_token_data[main_idx]
                main_idx += 1

                if rank == 0:
                    if extra_idx < len(extra_words):
                        word = extra_words[extra_idx]
                        extra_idx += 1
                    else:
                        word = "[UNK]"
                else:
                    word = self.dictionary.rank_to_word(rank)
                    if word is None:
                        word = "[RANK:%d]" % rank
                    if is_cap and word and word[0].islower():
                        word = word[0].upper() + word[1:]

                trailing = _TRAIL_STR_V4.get(trail, "")
                words.append(word + trailing)

        return " ".join(words)

    def _decode_v3(self, blob: bytes) -> str:
        """
        Decode v3 merged-varint blob.

        Layout: [0x03][count:3][main_stream][extra_section]
          main_stream: LEB128 per token, = rank*32 + variant
            - rank=0: extra section word (original casing, trailing from variant)
            - rank>0: known word (title case from caps bit, trailing from lower 4 bits)
          extra_section: length-prefixed UTF-8 strings with original casing
        """
        _VM = 32
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

            rank = unified // _VM
            variant = unified % _VM
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

            trailing = _TRAIL_STR_V3.get(trail, "")
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
