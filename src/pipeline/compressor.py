"""
Compressor: text -> compressed byte blob.

Full pipeline: tokenize -> build inverted index -> coordinate-encode positions
-> encode word IDs -> serialize to binary blob.
"""

from typing import Optional, List
import io
import sys

from ..tokenizer.tokenizer import Tokenizer, Token
from ..wordid.dictionary import Dictionary
from ..wordid.word_id_codec import WordIdCodec
from ..inverted_index.index_builder import IndexBuilder
from ..serializer.encoder import BlobEncoder, WordEntry, PunctEntry, build_cap_bitmap
from ..morphology.lemmatizer import Lemmatizer, MORPH_BASE
from ..blanks.blank_selector import BlankSelector
from ..blanks.constraint_checker import ConstraintChecker
from .config import FLAG_HAS_UNKNOWN_WORDS, FLAG_HAS_MORPHOLOGY

# Import coordinate encoding system (existing, tested)
from ..coordinate_encoding.coordinate_encoder import CoordinateEncoder


def _suppress_prints(func, *args, **kwargs):
    """Call a function while suppressing its print output."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout


class Compressor:

    def __init__(self, dictionary: Optional[Dictionary] = None,
                 use_coordinate_encoding: bool = True,
                 use_morphology: bool = True,
                 use_blanks: bool = True):
        self.dictionary = dictionary or Dictionary()
        self.tokenizer = Tokenizer()
        self.index_builder = IndexBuilder()
        self.blob_encoder = BlobEncoder()
        self.use_coordinate_encoding = use_coordinate_encoding
        self.use_morphology = use_morphology
        self.use_blanks = use_blanks
        if use_coordinate_encoding:
            self.coord_encoder = _suppress_prints(CoordinateEncoder)
        if use_morphology:
            self.lemmatizer = Lemmatizer(dictionary=self.dictionary)
        if use_blanks:
            self.blank_selector = BlankSelector(self.dictionary)
            self.constraint_checker = ConstraintChecker(self.dictionary)

    def compress(self, text: str) -> bytes:
        """
        Compress text to a binary blob.

        Pipeline:
        1. Tokenize text (split, extract punct/caps, wrap to 80-char bins)
        2. Build inverted index (word -> grid positions)
        3. Encode each word's ID and positions
        4. Build structural metadata (capitalization bitmap, punctuation table)
        5. Serialize everything to binary blob

        Returns:
            Compressed byte blob.
        """
        # Step 1: Tokenize
        doc = self.tokenizer.tokenize(text)

        if not doc.tokens:
            return self._encode_empty()

        # Step 1.5: Morphological lemmatization (Phase 3)
        morph_flags = []
        if self.use_morphology:
            for token in doc.tokens:
                base, flag = self.lemmatizer.lemmatize(token.word)
                morph_flags.append(flag)
                if flag != MORPH_BASE:
                    token.word = base  # replace with base form for index
        else:
            morph_flags = [MORPH_BASE] * len(doc.tokens)

        # Step 2: Build inverted index (uses base forms if morphology active)
        index = self.index_builder.build(doc.tokens)

        # Step 3: Build word entries with IDs and coordinate-encoded positions
        word_entries = []
        has_unknowns = False

        for word in index.word_order:
            positions = index.entries[word]
            vert = [p[0] for p in positions]
            horiz = [p[1] for p in positions]

            rank = self.dictionary.word_to_rank(word)
            if rank is None:
                has_unknowns = True

            # Combined (row, slot) positions for bitpacked encoding
            combined = [(v, h) for v, h in zip(vert, horiz)]

            word_entries.append(WordEntry(
                rank=rank,
                word=word,
                vert_positions=vert,
                horiz_positions=horiz,
                combined_positions=combined,
            ))

        # Step 4: Build structural metadata
        cap_flags = [t.is_capitalized for t in doc.tokens]
        cap_bitmap = build_cap_bitmap(cap_flags)

        punct_entries = []
        for i, token in enumerate(doc.tokens):
            if token.leading_punct or token.trailing_punct:
                punct_entries.append(PunctEntry(
                    token_index=i,
                    leading_punct=token.leading_punct,
                    trailing_punct=token.trailing_punct,
                ))

        # Step 5: Calculate checksum (on base forms after lemmatization)
        all_words = [t.word for t in doc.tokens]
        checksum = self.dictionary.checksum(all_words)

        # Step 5.5: Blank system (Phase 4) - remove words recoverable from constraints
        blank_data = None
        if self.use_blanks and len(doc.tokens) > 5:
            blanks = self.blank_selector.select_blanks(word_entries, len(doc.tokens))
            if blanks:
                # Compute line_word_counts for gap detection
                line_word_counts = self.constraint_checker.compute_line_word_counts(doc.tokens)

                # Build gap assignment map: for each gap position, which blank index?
                # Gaps are sorted by (line, col). We need to map each gap to a blank.
                # Build a position → blank_index lookup from the blanked words' positions.
                gap_assignment = []
                pos_to_blank_idx = {}
                for blank_idx, blank in enumerate(blanks):
                    if blank.positions:
                        for pos in blank.positions:
                            pos_to_blank_idx[pos] = blank_idx

                # Enumerate all positions, find gaps, record assignment
                for line_idx, count in enumerate(line_word_counts):
                    line_number = line_idx + 1
                    for word_idx in range(count):
                        pos = (line_number, word_idx)
                        if pos in pos_to_blank_idx:
                            gap_assignment.append(pos_to_blank_idx[pos])

                # Remove blanked word entries from the word table
                blanked_words = {b.word for b in blanks}
                word_entries = [e for e in word_entries if e.word not in blanked_words]

                blank_data = {
                    'line_word_counts': line_word_counts,
                    'gap_assignment': gap_assignment,
                    'blanks': [
                        {
                            'constraint_bytes': b.constraint_bytes,
                            'occurrence_count': b.occurrence_count,
                        }
                        for b in blanks
                    ],
                }

        # Step 6: Serialize
        blob = self.blob_encoder.encode(
            word_entries=word_entries,
            total_tokens=len(doc.tokens),
            line_count=doc.line_count,
            checksum=checksum,
            cap_bitmap=cap_bitmap,
            punct_entries=punct_entries,
            morph_flags=morph_flags if self.use_morphology else None,
            blank_data=blank_data,
        )

        return blob

    def _encode_empty(self) -> bytes:
        """Encode an empty document."""
        return self.blob_encoder.encode(
            word_entries=[],
            total_tokens=0,
            line_count=0,
            checksum=0,
            cap_bitmap=b'',
            punct_entries=[],
        )
