"""
Tokenizer: text -> Token list with 80-char bin structure.

Splits text into tokens preserving capitalization, punctuation,
and whitespace structure. Wraps into 80-char bins for the
battleship grid coordinate system.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from ..pipeline.config import MAX_LINE_WIDTH


@dataclass
class Token:
    word: str               # lowercased, stripped of punctuation
    original: str           # original form as it appeared in text
    leading_punct: str      # punctuation before the word (e.g. '"')
    trailing_punct: str     # punctuation after the word (e.g. ',')
    is_capitalized: bool    # first letter was uppercase
    line_number: int = 0    # which 80-char bin line (1-based)
    word_index: int = 0     # word position within line (0-based)


@dataclass
class TokenizedDocument:
    tokens: List[Token]
    line_bins: List[str]    # the 80-char wrapped lines
    line_count: int
    original_text: str = "" # stored for verification


# Punctuation that attaches to words
LEADING_PUNCT = set('"\'([{')
TRAILING_PUNCT = set('.,!?;:\'")}]')
# Extended: handle smart quotes, em-dash, ellipsis
LEADING_PUNCT_PATTERN = re.compile(r'^(["\'\(\[\{""''«]+)')
TRAILING_PUNCT_PATTERN = re.compile(r'([.,!?;:\'\"\)\]\}""''»\-]+)$')


class Tokenizer:

    def tokenize(self, text: str) -> TokenizedDocument:
        """Split text into tokens, wrap into 80-char bins, assign grid positions."""
        # Step 1: Split into raw word tokens
        raw_tokens = self._split_into_tokens(text)

        # Step 2: Wrap into 80-char bins and assign positions
        line_bins, tokens = self._assign_grid_positions(raw_tokens)

        return TokenizedDocument(
            tokens=tokens,
            line_bins=line_bins,
            line_count=len(line_bins),
            original_text=text,
        )

    def _split_into_tokens(self, text: str) -> List[Token]:
        """Split text into Token objects, extracting punctuation."""
        tokens = []
        # Split on whitespace, preserving the raw chunks
        chunks = text.split()

        for chunk in chunks:
            if not chunk:
                continue

            # Extract leading punctuation
            leading = ""
            m = LEADING_PUNCT_PATTERN.match(chunk)
            if m:
                leading = m.group(1)
                chunk = chunk[len(leading):]

            # Extract trailing punctuation
            trailing = ""
            if chunk:  # might be empty if chunk was all punct
                m = TRAILING_PUNCT_PATTERN.search(chunk)
                if m:
                    trailing = m.group(1)
                    chunk = chunk[:len(chunk) - len(trailing)]

            # Handle edge case: chunk was entirely punctuation
            if not chunk:
                # Treat the whole thing as a word (rare: standalone punctuation)
                chunk = leading + trailing
                leading = ""
                trailing = ""

            word = chunk.lower()
            is_cap = chunk[0].isupper() if chunk else False

            tokens.append(Token(
                word=word,
                original=chunk,
                leading_punct=leading,
                trailing_punct=trailing,
                is_capitalized=is_cap,
            ))

        return tokens

    def _assign_grid_positions(self, tokens: List[Token]) -> tuple:
        """Wrap tokens into 80-char bins and assign (line_number, word_index)."""
        lines: List[str] = []
        current_line_words: List[str] = []
        current_line_len = 0
        token_idx = 0  # index into tokens list

        # Track which tokens go on which line
        line_token_ranges: List[List[int]] = []  # list of token indices per line
        current_line_token_indices: List[int] = []

        for i, token in enumerate(tokens):
            # Reconstruct the display form for line-width calculation
            display = token.leading_punct + token.original + token.trailing_punct
            word_len = len(display)

            # Check if adding this word exceeds 80 chars
            needed = word_len if current_line_len == 0 else 1 + word_len  # +1 for space

            if current_line_len + needed > MAX_LINE_WIDTH and current_line_words:
                # Finalize current line
                lines.append(" ".join(current_line_words))
                line_token_ranges.append(current_line_token_indices)
                current_line_words = []
                current_line_len = 0
                current_line_token_indices = []

            current_line_words.append(display)
            current_line_token_indices.append(i)
            current_line_len += needed

        # Finalize last line
        if current_line_words:
            lines.append(" ".join(current_line_words))
            line_token_ranges.append(current_line_token_indices)

        # Assign grid positions to tokens
        for line_idx, token_indices in enumerate(line_token_ranges):
            for word_idx, token_i in enumerate(token_indices):
                tokens[token_i].line_number = line_idx + 1  # 1-based
                tokens[token_i].word_index = word_idx        # 0-based

        return lines, tokens
