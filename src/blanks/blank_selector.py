"""
Blank Selector: choose which words to remove from the grid for maximum savings.

Strategy:
  1. Calculate the byte cost of each word's inverted index entry
  2. Calculate the cost of a blank marker (constraint hints)
  3. Select words where blank_cost << entry_cost (net savings)
  4. Prioritize high-frequency words (they have the most position data)
  5. Respect partition limits (1 blank per checksum partition for simple mode)

The blank selector considers the FULL cost: removing a word's entire entry
(word_id + vertical positions + horizontal positions) and replacing it with
a small constraint marker. The positions of the blanked word are recoverable
from grid gaps (positions not claimed by any remaining word).
"""

from typing import List, Dict, Set, Optional
from dataclasses import dataclass

from ..wordid.dictionary import Dictionary
from ..wordid.word_id_codec import WordIdCodec
from ..serializer.encoder import WordEntry
from .constraint_checker import ConstraintChecker


@dataclass
class BlankDecision:
    """A decision to blank a word from the grid."""
    word: str
    rank: int
    entry_cost: int           # bytes saved by removing entry
    blank_cost: int           # bytes spent on constraint marker
    net_savings: int          # entry_cost - blank_cost
    occurrence_count: int     # how many times this word appears
    constraint_bytes: bytes   # pre-encoded constraint signals
    positions: list = None    # original grid positions for gap assignment


class BlankSelector:
    """Select words to blank for maximum compression."""

    # Minimum net savings to bother blanking a word
    MIN_SAVINGS = 3

    def __init__(self, dictionary: Dictionary):
        self.dictionary = dictionary
        self.codec = WordIdCodec()
        self.checker = ConstraintChecker(dictionary)

    def select_blanks(
        self,
        word_entries: List[WordEntry],
        total_tokens: int,
    ) -> List[BlankDecision]:
        """
        Select words to blank for maximum byte savings.

        Returns list of BlankDecision objects, sorted by savings descending.
        """
        candidates = []

        for entry in word_entries:
            if entry.rank is None:
                continue  # can't blank unknown words (no rank for recovery)

            # Calculate byte cost of this word's entry in the word table
            word_id_bytes = len(self.codec.encode_rank(entry.rank))
            vert_bytes = len(entry.vert_encoded) if entry.vert_encoded else len(entry.vert_positions) * 2
            horiz_bytes = len(entry.horiz_encoded) if entry.horiz_encoded else len(entry.horiz_positions) * 2
            # Total: word_id + vert_len(2) + vert_data + horiz_len(2) + horiz_data
            entry_cost = word_id_bytes + 2 + vert_bytes + 2 + horiz_bytes

            # Calculate cost of blank marker
            constraint_bytes = self.checker.encode_constraints(entry.word)
            blank_cost = len(constraint_bytes)

            net_savings = entry_cost - blank_cost

            if net_savings >= self.MIN_SAVINGS:
                occurrence_count = len(entry.vert_positions)
                positions = list(zip(entry.vert_positions, entry.horiz_positions))
                candidates.append(BlankDecision(
                    word=entry.word,
                    rank=entry.rank,
                    entry_cost=entry_cost,
                    blank_cost=blank_cost,
                    net_savings=net_savings,
                    occurrence_count=occurrence_count,
                    constraint_bytes=constraint_bytes,
                    positions=positions,
                ))

        # Sort by net savings descending (blank the most expensive words first)
        candidates.sort(key=lambda c: -c.net_savings)

        # Select all blanks with positive savings.
        # Multi-blank gap assignment uses occurrence_count to slice gaps.
        return candidates
