"""
Inverted Index Reader: {word: [positions]} -> ordered token stream.

Reconstructs the sequential token order from the inverted index by
placing words on the grid and reading left-to-right, top-to-bottom.
This is the "battleship" decompression: coordinates -> document.
"""

from typing import List, Dict, Tuple

from ..tokenizer.tokenizer import Token


class IndexReader:

    def reconstruct_token_stream(
        self,
        entries: Dict[str, List[Tuple[int, int]]],
        word_order: List[str],
    ) -> List[Token]:
        """
        Rebuild ordered token list from inverted index.

        Places each word at its grid coordinates, then reads the grid
        left-to-right, top-to-bottom to produce the document order.

        Args:
            entries: word -> [(line_number, word_index), ...]
            word_order: unique words in encoding order (for deterministic iteration)

        Returns:
            List of Token objects in document order (caps/punct not restored yet).
        """
        # Collect all placements: (line, col, word)
        placements: List[Tuple[int, int, str]] = []

        for word in word_order:
            positions = entries.get(word, [])
            for line_num, word_idx in positions:
                placements.append((line_num, word_idx, word))

        # Sort by (line_number, word_index) to get document order
        placements.sort(key=lambda p: (p[0], p[1]))

        # Convert to Token objects (minimal - caps/punct added later from metadata)
        tokens = []
        for line_num, word_idx, word in placements:
            tokens.append(Token(
                word=word,
                original=word,  # will be overwritten by caps restoration
                leading_punct="",
                trailing_punct="",
                is_capitalized=False,
                line_number=line_num,
                word_index=word_idx,
            ))

        return tokens
