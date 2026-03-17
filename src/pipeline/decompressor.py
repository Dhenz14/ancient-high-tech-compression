"""
Decompressor: compressed byte blob -> text.

Full pipeline: deserialize blob -> decode word IDs -> coordinate-decode positions
-> reconstruct inverted index -> read grid -> detokenize.
"""

from typing import Optional, List, Tuple
import io
import sys

from ..serializer.decoder import BlobDecoder, DecodedBlob
from ..serializer.encoder import PunctEntry
from ..wordid.dictionary import Dictionary
from ..inverted_index.index_reader import IndexReader
from ..tokenizer.detokenizer import Detokenizer
from ..tokenizer.tokenizer import Token
from ..morphology.inflector import Inflector
from ..blanks.blank_resolver import BlankResolver

# Import coordinate decoding system (existing, tested)
from ..coordinate_encoding.coordinate_decoder import CoordinateDecoder


def _suppress_prints(func, *args, **kwargs):
    """Call a function while suppressing its print output."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout


class Decompressor:

    def __init__(self, dictionary: Optional[Dictionary] = None):
        self.dictionary = dictionary or Dictionary()
        self.blob_decoder = BlobDecoder()
        self.index_reader = IndexReader()
        self.detokenizer = Detokenizer()
        self.coord_decoder = _suppress_prints(CoordinateDecoder)
        self.inflector = Inflector()
        self.blank_resolver = BlankResolver(self.dictionary)

    def decompress(self, blob: bytes) -> str:
        """
        Decompress a binary blob back to text.

        Pipeline:
        1. Deserialize blob into structured data
        2. Resolve word IDs to actual words via dictionary
        3. Rebuild inverted index entries
        4. Reconstruct token stream from grid positions
        5. Apply capitalization and punctuation from metadata
        6. Detokenize to text

        Returns:
            Reconstructed text string.
        """
        # Step 1: Deserialize
        decoded = self.blob_decoder.decode(blob)

        if decoded.total_tokens == 0:
            return ""

        # Step 2: Resolve word IDs to words and rebuild entries
        entries = {}
        word_order = []

        for entry in decoded.word_entries:
            if entry.rank is not None:
                word = self.dictionary.rank_to_word(entry.rank)
                if word is None:
                    word = f"[RANK:{entry.rank}]"
            else:
                word = entry.word  # unknown word was stored inline

            # Get positions: prefer combined, fall back to separate vert/horiz
            if entry.combined_positions:
                positions = list(entry.combined_positions)
            elif entry.vert_encoded is not None and len(entry.vert_encoded) > 0:
                vert = self.coord_decoder.decode(entry.vert_encoded)
                horiz = self.coord_decoder.decode(entry.horiz_encoded) if entry.horiz_encoded else entry.horiz_positions
                positions = list(zip(vert, horiz))
            else:
                positions = list(zip(entry.vert_positions, entry.horiz_positions))
            entries[word] = positions
            word_order.append(word)

        # Step 2.5: Restore blanked words (Phase 4)
        if decoded.blank_data and decoded.blank_data.get('blanks'):
            self._restore_blanked_words(
                entries, word_order, decoded.blank_data, decoded
            )

        # Step 3: Reconstruct token stream from grid
        tokens = self.index_reader.reconstruct_token_stream(entries, word_order)

        # Step 4: Apply morphological inflection (Phase 3)
        if decoded.morph_flags:
            self._apply_morphology(tokens, decoded.morph_flags)

        # Step 5: Apply capitalization from bitmap
        self._apply_capitalization(tokens, decoded.cap_bitmap)

        # Step 6: Apply punctuation from table
        self._apply_punctuation(tokens, decoded.punct_entries)

        # Step 6: Detokenize
        return self.detokenizer.detokenize_tokens(tokens)

    def _apply_capitalization(self, tokens: List[Token], cap_bitmap: bytes):
        """Apply capitalization bitmap to tokens."""
        for i, token in enumerate(tokens):
            byte_idx = i // 8
            bit_idx = 7 - (i % 8)
            if byte_idx < len(cap_bitmap):
                is_cap = bool(cap_bitmap[byte_idx] & (1 << bit_idx))
                token.is_capitalized = is_cap
                if is_cap and token.word:
                    token.original = token.word[0].upper() + token.word[1:]
                else:
                    token.original = token.word

    def _restore_blanked_words(self, entries: dict, word_order: list,
                                blank_data: dict, decoded) -> None:
        """
        Restore blanked words using gap detection + constraint resolution.

        The battleship game:
        1. We know how many words are on each line (line_word_counts)
        2. We know which positions are claimed by non-blanked words (entries)
        3. Unclaimed positions = gaps = where blanked words go
        4. Constraint signals tell us WHICH word fills the gaps
        5. Occurrence count tells us HOW MANY gaps belong to each blank
        """
        from ..blanks.blank_resolver import BlankResolver
        from ..blanks.constraint_checker import ConstraintChecker

        resolver = BlankResolver(self.dictionary)
        checker = ConstraintChecker(self.dictionary)

        line_word_counts = blank_data.get('line_word_counts', [])
        blanks = blank_data.get('blanks', [])

        if not line_word_counts or not blanks:
            return

        # Step 1: Find gap positions (the battleship detection)
        gaps = resolver.find_gap_positions(entries, line_word_counts)

        # Step 2: Decode constraint signals for each blank
        decoded_constraints = []
        for blank in blanks:
            cb = blank['constraint_bytes']
            constraints, _ = checker.decode_constraints(cb, 0)
            constraints['occurrence_count'] = blank.get('occurrence_count', 0)
            decoded_constraints.append(constraints)

        # Step 3: Assign blanked words to gaps using gap assignment map
        gap_assignment = blank_data.get('gap_assignment', None)
        recovered = resolver.assign_blanks_to_gaps(
            decoded_constraints, gaps, gap_assignment
        )

        # Step 4: Merge recovered entries into the main entries dict
        for word, positions in recovered.items():
            if word in entries:
                entries[word].extend(positions)
            else:
                entries[word] = positions
                word_order.append(word)

    def _apply_morphology(self, tokens: List[Token], morph_flags: dict):
        """Apply morphological inflection to tokens."""
        for idx, flag in morph_flags.items():
            if idx < len(tokens) and flag != 0:
                inflected = self.inflector.inflect(tokens[idx].word, flag)
                tokens[idx].word = inflected
                tokens[idx].original = inflected

    def _apply_punctuation(self, tokens: List[Token], punct_entries: List[PunctEntry]):
        """Apply punctuation table to tokens."""
        # Build lookup by token index
        punct_map = {p.token_index: p for p in punct_entries}

        for i, token in enumerate(tokens):
            if i in punct_map:
                token.leading_punct = punct_map[i].leading_punct
                token.trailing_punct = punct_map[i].trailing_punct
