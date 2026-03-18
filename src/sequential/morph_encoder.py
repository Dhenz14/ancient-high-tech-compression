"""
Sequential Rank Stream v6 — Morphological Fallback Encoder.

V6 is identical to v4 except the extra section supports morph-compressed entries.
When an unknown word can be expressed as base_form + morph_flag (where base_form
is in the dictionary), it is stored in 3 bytes instead of 1 + word_length bytes.

V6 extra section entry types:
  Normal word:  [length: 1 (1-254)][word bytes: length]   — same as v4
  Morph escape: [0x00: 1][base_rank: LEB128][flag_caps: 1]
                  base_rank:  dictionary rank of the base form
                  flag_caps:  bits 6-0 = morph_flag, bit 7 = is_title_case

Morph encoding criteria (ALL must hold):
  - rank is None  (word is not directly in dictionary)
  - caps in (C_LOWER, C_TITLE)  (simple casing; ALL CAPS / mixed skipped)
  - lead == L_NONE  (no leading punctuation)
  - not is_rare_trail  (rare trailing punct goes in stored word in v4; skip here)
  - lemmatize(word) returns (base, flag) where flag != MORPH_BASE
  - base is in dictionary (has a valid rank)
  - morph encoding is strictly shorter than raw encoding

Savings: for "computerized" (12 chars = 13 bytes raw), morph gives 3 bytes → saves 10.
"""

from typing import Optional
from ..wordid.dictionary import Dictionary
from ..morphology.lemmatizer import Lemmatizer, MORPH_BASE
from .encoder import (
    SequentialEncoder,
    C_LOWER, C_TITLE, C_UPPER, C_MIXED,
    L_NONE,
    T_NONE,
    VARIANT_MULT,
    _V4_RARE_TRAIL, _TRAIL_STRING, _LEAD_CHAR,
)


VERSION_V6 = 0x06


def _varint_len(value: int) -> int:
    """Number of bytes a LEB128 varint will occupy."""
    if value < 0x80:
        return 1
    if value < 0x4000:
        return 2
    return 3  # sufficient for all ranks up to 249,777


def _encode_varint_into(buf: bytearray, value: int):
    """Append LEB128 varint to buffer in-place."""
    while value >= 0x80:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    buf.append(value & 0x7F)


def encode_v6(text: str, dictionary: Optional[Dictionary] = None) -> bytes:
    """
    Encode text using V6 morphological fallback format.

    Identical to v4 except extra-section unknown words are compressed using
    morph encoding when possible. All other tokens encode identically to v4.

    Args:
        text: Input text.
        dictionary: Optional dictionary (uses default if None).

    Returns:
        V6 blob bytes.
    """
    if dictionary is None:
        dictionary = Dictionary()

    encoder = SequentialEncoder(dictionary)
    lemmatizer = Lemmatizer(dictionary)

    if not text or not text.strip():
        return bytes([VERSION_V6, 0, 0, 0])

    tokens = encoder._tokenize(text)
    count = len(tokens)

    main_buf = bytearray()
    extra_buf = bytearray()
    n_morph_used = 0  # track whether any morph escape was written

    for original, word, caps, lead, trail in tokens:
        rank = dictionary.word_to_rank(word)
        is_rare_trail = trail in _V4_RARE_TRAIL

        # Determine extra section path (same logic as v4)
        go_extra = (rank is None) or (caps in (C_UPPER, C_MIXED)) or (lead != L_NONE) or is_rare_trail

        if not go_extra:
            # Normal main-stream token (identical to v4)
            is_cap = 1 if caps == C_TITLE else 0
            variant = (is_cap << 3) | (trail & 0x07)
            unified = rank * VARIANT_MULT + variant
            _encode_varint_into(main_buf, unified)
            continue

        # Extra section token — write rank=0 marker in main stream
        effective_trail = trail
        rare_trail_str = ''
        if is_rare_trail:
            rare_trail_str = _TRAIL_STRING[trail]
            effective_trail = T_NONE

        variant = effective_trail & 0x07
        _encode_varint_into(main_buf, variant)

        # Try morph encoding for eligible unknown words
        if (rank is None
                and not is_rare_trail
                and lead == L_NONE
                and caps in (C_LOWER, C_TITLE)):
            base, morph_flag = lemmatizer.lemmatize(word)
            if (morph_flag != MORPH_BASE
                    and dictionary.has_word(base)):
                base_rank = dictionary.word_to_rank(base)
                if base_rank is not None:
                    morph_size = 1 + _varint_len(base_rank) + 1  # escape + rank + flag_caps
                    raw_size = 1 + len(original.encode('utf-8'))  # length + bytes
                    if morph_size < raw_size:
                        is_title = 1 if caps == C_TITLE else 0
                        flag_caps = (morph_flag & 0x7F) | (is_title << 7)
                        extra_buf.append(0x00)  # morph escape
                        _encode_varint_into(extra_buf, base_rank)
                        extra_buf.append(flag_caps)
                        n_morph_used += 1
                        continue

        # Raw extra section encoding (identical to v4)
        lead_char = _LEAD_CHAR.get(lead, '')
        extra_word = lead_char + original + rare_trail_str
        wb = extra_word.encode('utf-8')
        if len(wb) > 254:  # reserve 0x00 for morph escape; cap at 254
            wb = wb[:254]
        extra_buf.append(len(wb))
        extra_buf.extend(wb)

    # Use v4 version byte if no morph escapes were written — avoids brotli
    # sensitivity to the version byte when the blobs are otherwise identical.
    version_byte = VERSION_V6 if n_morph_used > 0 else 0x04

    buf = bytearray()
    buf.append(version_byte)
    buf.extend(count.to_bytes(3, 'big'))
    buf.extend(main_buf)
    buf.extend(extra_buf)
    return bytes(buf)
