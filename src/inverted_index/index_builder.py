"""
Inverted Index Builder: token stream -> {word: [positions]}.

Builds the inverted index that maps each unique word to all grid positions
where it appears. This is the core of the "battleship" compression approach:
instead of storing words sequentially, store each word once with its coordinates.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import OrderedDict

from ..tokenizer.tokenizer import Token


@dataclass
class InvertedIndex:
    """
    Inverted index mapping words to their grid positions.

    entries: word -> list of (line_number, word_index) tuples
    word_order: unique words in first-appearance order
    total_tokens: total number of word tokens in document
    """
    entries: Dict[str, List[Tuple[int, int]]]  # word -> [(line, col), ...]
    word_order: List[str]                       # unique words, first-appearance order
    total_tokens: int


class IndexBuilder:

    def build(self, tokens: List[Token]) -> InvertedIndex:
        """
        Build inverted index from token stream.

        Each token's (line_number, word_index) becomes a grid coordinate.
        Words are tracked in first-appearance order for deterministic encoding.
        """
        entries: Dict[str, List[Tuple[int, int]]] = OrderedDict()

        for token in tokens:
            word = token.word
            pos = (token.line_number, token.word_index)

            if word not in entries:
                entries[word] = []
            entries[word].append(pos)

        word_order = list(entries.keys())

        return InvertedIndex(
            entries=dict(entries),
            word_order=word_order,
            total_tokens=len(tokens),
        )

    def get_vertical_positions(self, index: InvertedIndex, word: str) -> List[int]:
        """Extract vertical (line number) positions for a word."""
        if word not in index.entries:
            return []
        return [pos[0] for pos in index.entries[word]]

    def get_horizontal_positions(self, index: InvertedIndex, word: str) -> List[int]:
        """Extract horizontal (word index within line) positions for a word."""
        if word not in index.entries:
            return []
        return [pos[1] for pos in index.entries[word]]
