"""
Sequential Rank Stream Encoder v3 — Merged Varint Format.

Each token encodes word + caps + trailing punct as a SINGLE merged integer:
  unified = rank * 32 + variant
  variant = (is_title_case << 4) | trailing_punct_code

This keeps the top 3 most common words ("the", "of", "and") as single bytes,
which is optimal for brotli's stage-2 compression.

Special cases stored in the extra section (rank=0 in main stream):
  - Unknown words (not in dictionary)
  - ALL CAPS words (e.g., "NASA", "THE") — original casing preserved
  - Mixed-case words (e.g., "iPhone") — original casing preserved
  - Words with leading punctuation (e.g., '"hello') — lead char prepended

All extra words are stored WITH ORIGINAL CASING (no transformation needed on decode).
Trailing punct is still encoded in the variant bits even for extra-section tokens.

Fixes over v2:
  - Contractions safe: 'don't', 'can't', etc. — apostrophe not stripped mid-word
  - Multi-char trailing: '."' and ',"' encoded as single codes
  - ALL CAPS: "NASA", "THE" correctly recovered (was title-cased in v2)
  - Mixed case: "iPhone", "McDonald's" correctly recovered
  - Leading punct: '"hello', '(hello' correctly encoded
"""

from typing import List, Tuple, Optional
from ..wordid.dictionary import Dictionary


# === Trailing punct codes (4 bits = 16 values) ===
T_NONE       = 0
T_PERIOD     = 1
T_COMMA      = 2
T_EXCLAIM    = 3
T_QUESTION   = 4
T_SEMICOLON  = 5
T_COLON      = 6
T_DQUOTE     = 7   # trailing "
T_SQUOTE     = 8   # trailing ' (possessive)
T_PAREN      = 9   # )
T_BRACKET    = 10  # ]
T_HYPHEN     = 11  # -
T_ELLIPSIS   = 12  # ...
T_PERIOD_DQ  = 13  # ."
T_COMMA_DQ   = 14  # ,"
T_QDQUOTE    = 15  # ?" or !"

# === Leading punct codes (for extra-section words) ===
# These are only used internally to decide whether to store in extra section.
L_NONE    = 0
L_DQUOTE  = 1   # "
L_PAREN   = 2   # (
L_BRACKET = 3   # [

# === Caps mode constants ===
C_LOWER = 0   # all lowercase: "hello"
C_TITLE = 1   # first letter cap: "Hello"
C_UPPER = 2   # ALL CAPS: "NASA"
C_MIXED = 3   # mixed case: "iPhone"

# === Format constants ===
VARIANT_MULT = 32   # 5-bit variant: [caps:1][trailing:4]
VERSION = 0x03

# === Lookup tables ===
_TRAIL_SINGLE = {
    '.': T_PERIOD, ',': T_COMMA, '!': T_EXCLAIM, '?': T_QUESTION,
    ';': T_SEMICOLON, ':': T_COLON, '"': T_DQUOTE, "'": T_SQUOTE,
    ')': T_PAREN, ']': T_BRACKET, '-': T_HYPHEN,
}
_TRAIL_MULTI = {
    '."': T_PERIOD_DQ, ',"': T_COMMA_DQ,
    '!"': T_QDQUOTE, '?"': T_QDQUOTE,
}
_LEAD_MAP = {'"': L_DQUOTE, '(': L_PAREN, '[': L_BRACKET}
_LEAD_CHAR = {L_DQUOTE: '"', L_PAREN: '(', L_BRACKET: '[', L_NONE: ''}

# Characters that can appear as trailing punct
_TRAILING_CHARS = frozenset('.,!?;:\'")-]')
# Characters that can appear as leading punct (NOT single quote)
_LEADING_CHARS = frozenset('"([')


def _encode_varint(value: int) -> bytes:
    """LEB128 variable-length integer encoding."""
    buf = bytearray()
    while value >= 0x80:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    buf.append(value & 0x7F)
    return bytes(buf)


class SequentialEncoder:
    """
    Encode text as a merged-varint stream + extra section.

    Blob format:
      [version:1]      0x03
      [count:3]        uint24 big-endian, total token count
      [main_stream]    LEB128 varints, one per token: rank*32 + variant
                       rank=0 means "extra section" token
      [extra_section]  length-prefixed UTF-8 strings, in stream order
                       for rank=0 tokens: full original word (with casing + leading punct)
    """

    def __init__(self, dictionary: Optional[Dictionary] = None):
        self.dictionary = dictionary or Dictionary()

    def encode(self, text: str) -> bytes:
        if not text or not text.strip():
            return bytes([VERSION, 0, 0, 0])

        tokens = self._tokenize(text)

        main_buf = bytearray()
        extra_buf = bytearray()

        for original, word, caps, lead, trail in tokens:
            rank = self.dictionary.word_to_rank(word)

            # Determine if this token goes in the extra section:
            # Unknown words, ALL CAPS, mixed case, or has leading punct
            go_extra = (rank is None) or (caps in (C_UPPER, C_MIXED)) or (lead != L_NONE)

            if not go_extra:
                # Normal known word: merge into single varint
                is_cap = 1 if caps == C_TITLE else 0
                variant = (is_cap << 4) | (trail & 0x0F)
                unified = rank * VARIANT_MULT + variant
                main_buf.extend(_encode_varint(unified))
            else:
                # Extra section: rank=0 in main stream
                variant = trail & 0x0F  # caps bit=0, trailing only
                main_buf.extend(_encode_varint(variant))  # varint(0-15) → rank=0

                # Build extra word: leading punct char (if any) + original casing
                lead_char = _LEAD_CHAR.get(lead, '')
                extra_word = lead_char + original
                wb = extra_word.encode('utf-8')
                if len(wb) > 255:
                    wb = wb[:255]
                extra_buf.append(len(wb))
                extra_buf.extend(wb)

        count = len(tokens)
        buf = bytearray()
        buf.append(VERSION)
        buf.extend(count.to_bytes(3, 'big'))
        buf.extend(main_buf)
        buf.extend(extra_buf)
        return bytes(buf)

    def _tokenize(self, text: str) -> List[Tuple[str, str, int, int, int]]:
        """
        Split text into tokens.

        Returns list of (original, lowered, caps_mode, lead_code, trail_code).
          original:  chunk with original casing, AFTER leading/trailing punct stripped
          lowered:   lowercased version for dictionary lookup
          caps_mode: C_LOWER / C_TITLE / C_UPPER / C_MIXED
          lead_code: L_NONE / L_DQUOTE / L_PAREN / L_BRACKET
          trail_code: T_* constant
        """
        result = []

        for chunk in text.split():
            if not chunk:
                continue

            # --- Strip leading punct ---
            lead_code = L_NONE
            i = 0
            while i < len(chunk) and chunk[i] in _LEADING_CHARS:
                i += 1

            if i > 0:
                lead_chars = chunk[:i]
                chunk = chunk[i:]
                lead_code = _LEAD_MAP.get(lead_chars[0], L_NONE)

            if not chunk:
                # Pure leading punct: store as extra word
                result.append((lead_chars, lead_chars, C_LOWER, L_NONE, T_NONE))
                continue

            # --- Strip trailing punct ---
            trail_code = T_NONE

            if chunk.endswith('...'):
                trail_code = T_ELLIPSIS
                chunk = chunk[:-3]
            else:
                j = len(chunk)
                while j > 0 and chunk[j - 1] in _TRAILING_CHARS:
                    j -= 1

                if j < len(chunk):
                    trail = chunk[j:]
                    remaining = chunk[:j]

                    if remaining:
                        chunk = remaining
                        if trail in _TRAIL_MULTI:
                            trail_code = _TRAIL_MULTI[trail]
                        elif len(trail) >= 2 and trail[-2:] in _TRAIL_MULTI:
                            trail_code = _TRAIL_MULTI[trail[-2:]]
                        else:
                            trail_code = _TRAIL_SINGLE.get(trail[-1], T_NONE)
                    # else: entire chunk was trailing punct — keep as word

            if not chunk:
                continue

            # --- Determine caps mode ---
            original = chunk
            lowered = chunk.lower()

            if chunk == lowered:
                caps = C_LOWER
            elif len(chunk) == 1 and chunk.isupper():
                caps = C_TITLE  # single capital like "I" or "A"
            elif chunk[0].isupper() and chunk[1:] == chunk[1:].lower():
                caps = C_TITLE  # standard title case: "Hello"
            elif all(c.isupper() or not c.isalpha() for c in chunk) and any(c.isalpha() for c in chunk):
                caps = C_UPPER  # ALL CAPS: "NASA", "U.S."
            else:
                caps = C_MIXED  # mixed: "iPhone", "McDonald's"

            result.append((original, lowered, caps, lead_code, trail_code))

        return result
