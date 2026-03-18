"""
Sequential Rank Stream v5 — Blank System Prototype.

Omits tier-1 tokens (ranks 1-7, lowercase, no trailing punct) from the main stream
and stores them in a compact "blank section" before the main stream.

V5 blob format:
  [0x05: 1]          version byte
  [count: 3]         total token count (including blanked tokens)
  [n_blanks: 2]      number of tier-1 tokens that were blanked
  [blank_section]    n_blanks × 2 bytes: [rank: 1][delta_pos: 1]
                       rank: 1-7 (which tier-1 word)
                       delta_pos: distance from previous blank's position (or 0)
                       Tokens with delta_pos > 255 are NOT blanked (fallback to main stream).
  [main_stream]      varints for non-blank tokens (same encoding as v4)
  [extra_section]    length-prefixed UTF-8 words (same as v4)

Tier-1 blanking criteria (token must meet ALL):
  - rank in {1, 2, 3, 4, 5, 6, 7}
  - caps == C_LOWER (lowercase)
  - trail == T_NONE (no trailing punctuation)
  - lead == L_NONE (no leading punctuation)
  - delta from previous blank <= 255
"""

from typing import Optional
from ..wordid.dictionary import Dictionary
from .encoder import (
    SequentialEncoder,
    C_LOWER, C_UPPER, C_MIXED, C_TITLE,
    L_NONE,
    T_NONE,
    VARIANT_MULT,
    _V4_RARE_TRAIL, _TRAIL_STRING, _LEAD_CHAR,
)


VERSION_V5 = 0x05

# Tier-1 ranks: the(1), of(2), and(3), to(4), a(5), in(6), that(7)
TIER1_RANKS = frozenset(range(1, 8))


def _encode_varint_into(buf: bytearray, value: int):
    """Append LEB128 varint to buffer in-place."""
    while value >= 0x80:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    buf.append(value & 0x7F)


def encode_v5(text: str, dictionary: Optional[Dictionary] = None) -> bytes:
    """
    Encode text using the V5 blank system.

    Eligible tier-1 tokens are removed from the main stream and stored in
    a compact blank section. All other tokens are encoded identically to v4.
    """
    if dictionary is None:
        dictionary = Dictionary()

    encoder = SequentialEncoder(dictionary)

    if not text or not text.strip():
        return bytes([VERSION_V5, 0, 0, 0, 0, 0])  # count=0, n_blanks=0

    tokens = encoder._tokenize(text)
    count = len(tokens)

    blank_section = bytearray()   # pairs of (rank, delta_pos)
    main_buf = bytearray()
    extra_buf = bytearray()

    prev_blank_pos = 0
    n_blanks = 0

    for token_pos, (original, word, caps, lead, trail) in enumerate(tokens):
        rank = dictionary.word_to_rank(word)
        is_rare_trail = trail in _V4_RARE_TRAIL
        go_extra = (rank is None) or (caps in (C_UPPER, C_MIXED)) or (lead != L_NONE) or is_rare_trail

        # Check if this token qualifies for blanking
        if (not go_extra
                and rank in TIER1_RANKS
                and caps == C_LOWER
                and trail == T_NONE
                and lead == L_NONE):
            delta = token_pos - prev_blank_pos
            if delta <= 255:
                blank_section.append(rank)
                blank_section.append(delta)
                prev_blank_pos = token_pos
                n_blanks += 1
                continue  # skip main stream

        # Normal v4 encoding
        if not go_extra:
            is_cap = 1 if caps == C_TITLE else 0
            variant = (is_cap << 3) | (trail & 0x07)
            unified = rank * VARIANT_MULT + variant
            _encode_varint_into(main_buf, unified)
        else:
            # rare trailing: strip it and send word to extra section
            rare_trail_str = ''
            effective_trail = trail
            if is_rare_trail:
                rare_trail_str = _TRAIL_STRING[trail]
                effective_trail = T_NONE

            variant = effective_trail & 0x07
            _encode_varint_into(main_buf, variant)

            lead_char = _LEAD_CHAR.get(lead, '')
            extra_word = lead_char + original + rare_trail_str
            wb = extra_word.encode('utf-8')
            if len(wb) > 255:
                wb = wb[:255]
            extra_buf.append(len(wb))
            extra_buf.extend(wb)

    buf = bytearray()
    buf.append(VERSION_V5)
    buf.extend(count.to_bytes(3, 'big'))
    buf.extend(n_blanks.to_bytes(2, 'big'))
    buf.extend(blank_section)
    buf.extend(main_buf)
    buf.extend(extra_buf)
    return bytes(buf)
