"""
Blank Resolver: recover blanked words during decompression.

The battleship game in reverse:
  1. Rebuild the grid from non-blanked word entries
  2. Detect gaps (positions not claimed by any word)
  3. For each blanked word, use constraint signals to identify it
  4. Assign the blanked word to gap positions

Position recovery works because:
  - We know how many words are on each line (stored as line_word_counts)
  - We know all positions claimed by non-blanked words
  - Unclaimed positions = where blanked words go
  - Each blanked word's constraint signals tell us WHICH word it is
  - The word's positions in the original grid are the gap positions
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

from ..wordid.dictionary import Dictionary
from .constraint_checker import ConstraintChecker


class BlankResolver:
    """Recover blanked words and their positions from grid gaps."""

    def __init__(self, dictionary: Dictionary):
        self.dictionary = dictionary
        self.checker = ConstraintChecker(dictionary)

    def find_gap_positions(
        self,
        known_entries: Dict[str, List[Tuple[int, int]]],
        line_word_counts: List[int],
    ) -> List[Tuple[int, int]]:
        """
        Find grid positions not claimed by any known word.

        Args:
            known_entries: {word: [(line, col), ...]} for non-blanked words
            line_word_counts: number of words on each line [line1_count, line2_count, ...]

        Returns:
            List of (line_number, word_index) positions that are gaps.
        """
        # Build set of all claimed positions
        claimed: Set[Tuple[int, int]] = set()
        for positions in known_entries.values():
            for pos in positions:
                claimed.add(pos)

        # Enumerate all expected positions from line_word_counts
        gaps = []
        for line_idx, count in enumerate(line_word_counts):
            line_number = line_idx + 1  # 1-based
            for word_idx in range(count):
                pos = (line_number, word_idx)
                if pos not in claimed:
                    gaps.append(pos)

        return sorted(gaps)

    def assign_blanks_to_gaps(
        self,
        blank_constraints: List[dict],
        gap_positions: List[Tuple[int, int]],
        gap_assignment: List[int] = None,
    ) -> Dict[str, List[Tuple[int, int]]]:
        """
        Assign blanked words to gap positions using gap_assignment map.

        Args:
            blank_constraints: list of decoded constraint dicts (one per blanked word)
            gap_positions: list of (line, col) gap positions
            gap_assignment: list of blank_index per gap (maps each gap to a blank)

        Returns:
            {word: [(line, col), ...]} for recovered blanked words
        """
        if not blank_constraints or not gap_positions:
            return {}

        # Resolve each blank's word identity from constraints
        blank_words = []
        for constraints in blank_constraints:
            word = self.checker.resolve_word(constraints)
            blank_words.append(word or "[UNKNOWN_BLANK]")

        recovered_entries: Dict[str, List[Tuple[int, int]]] = {}

        if gap_assignment and len(gap_assignment) == len(gap_positions):
            # Multi-blank: use gap_assignment to map each gap to the correct word
            for gap_pos, blank_idx in zip(gap_positions, gap_assignment):
                if blank_idx < len(blank_words):
                    word = blank_words[blank_idx]
                    if word not in recovered_entries:
                        recovered_entries[word] = []
                    recovered_entries[word].append(gap_pos)
        elif len(blank_constraints) == 1:
            # Single blank: all gaps belong to this word
            recovered_entries[blank_words[0]] = list(gap_positions)
        else:
            # Fallback: assign by occurrence count
            offset = 0
            for i, constraints in enumerate(blank_constraints):
                count = constraints.get('occurrence_count', 0)
                word = blank_words[i]
                if count > 0 and offset + count <= len(gap_positions):
                    recovered_entries[word] = list(gap_positions[offset:offset + count])
                    offset += count

        return recovered_entries
