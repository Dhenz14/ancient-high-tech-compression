"""
Detokenizer: Token list -> text.

Reconstructs the original text from tokens by reattaching punctuation
and restoring capitalization.
"""

from typing import List
from .tokenizer import Token, TokenizedDocument


class Detokenizer:

    def detokenize(self, doc: TokenizedDocument) -> str:
        """Reconstruct original text from tokenized document."""
        return self.detokenize_tokens(doc.tokens)

    def detokenize_tokens(self, tokens: List[Token]) -> str:
        """Reconstruct text from a list of tokens."""
        parts = []
        for token in tokens:
            # Restore capitalization
            word = token.original
            if token.is_capitalized and word and word[0].islower():
                word = word[0].upper() + word[1:]
            elif not token.is_capitalized and word and word[0].isupper():
                word = word[0].lower() + word[1:]

            # Reattach punctuation
            parts.append(token.leading_punct + word + token.trailing_punct)

        return " ".join(parts)

    def reconstruct_from_grid(self, word_placements: list, cap_bitmap: bytes,
                              punct_table: list) -> str:
        """
        Reconstruct text from grid placements + structural metadata.

        Args:
            word_placements: list of (word, line_number, word_index) sorted by position
            cap_bitmap: capitalization bitmap (1 bit per token)
            punct_table: list of (token_index, leading_punct, trailing_punct)

        Returns:
            Reconstructed text string.
        """
        # Build punct lookup
        punct_lookup = {}
        for entry in punct_table:
            punct_lookup[entry[0]] = (entry[1], entry[2])

        parts = []
        for i, (word, _line, _col) in enumerate(word_placements):
            # Restore capitalization from bitmap
            byte_idx = i // 8
            bit_idx = 7 - (i % 8)
            is_cap = False
            if byte_idx < len(cap_bitmap):
                is_cap = bool(cap_bitmap[byte_idx] & (1 << bit_idx))

            if is_cap and word and word[0].islower():
                word = word[0].upper() + word[1:]

            # Reattach punctuation
            leading = ""
            trailing = ""
            if i in punct_lookup:
                leading, trailing = punct_lookup[i]

            parts.append(leading + word + trailing)

        return " ".join(parts)
