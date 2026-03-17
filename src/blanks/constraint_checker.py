"""
Constraint Checker: multi-signal word identification.

The Venn diagram approach: each constraint signal is a "circle" that
narrows the candidate set. The intersection of all signals = exactly 1 word.

Signals available:
  1. Checksum deficit (rank) - uniquely identifies within a partition
  2. POS category (noun/verb/adj/adv/etc) - eliminates ~90% of words
  3. Word length - eliminates ~80-95% of remaining
  4. First letter - eliminates ~96% of candidates
  5. Morphological form - eliminates inflected vs base

For single-blank-per-partition, the checksum deficit alone is sufficient
(ranks are unique). Multiple blanks per partition require additional signals.
"""

from typing import Dict, List, Tuple, Optional, Set
from ..wordid.dictionary import Dictionary


# Simple POS tagger based on word characteristics and dictionary position
# In Phase 5 this would use NLTK's POS tagger, but for now we use heuristics
_FUNCTION_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'nor', 'for', 'yet', 'so',
    'in', 'on', 'at', 'to', 'by', 'of', 'with', 'from', 'into', 'onto',
    'upon', 'out', 'up', 'down', 'off', 'over', 'under', 'through', 'between',
    'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being',
    'has', 'have', 'had', 'having',
    'do', 'does', 'did', 'doing',
    'will', 'would', 'shall', 'should', 'may', 'might', 'can', 'could', 'must',
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
    'my', 'your', 'his', 'its', 'our', 'their',
    'this', 'that', 'these', 'those',
    'who', 'whom', 'which', 'what', 'whose',
    'not', 'no', 'nor', 'neither', 'never',
    'if', 'then', 'else', 'when', 'while', 'until', 'since', 'because', 'although',
    'very', 'too', 'also', 'just', 'only', 'even', 'still', 'already',
    'all', 'each', 'every', 'both', 'few', 'many', 'much', 'some', 'any',
    'here', 'there', 'where', 'how', 'why', 'about', 'than', 'as',
}

# POS categories (4 bits = 16 categories)
POS_FUNCTION = 0     # function words (the, a, is, and, etc.)
POS_NOUN = 1         # nouns
POS_VERB = 2         # verbs
POS_ADJ = 3          # adjectives
POS_ADV = 4          # adverbs
POS_PROPER = 5       # proper nouns (capitalized, not in dict)
POS_UNKNOWN = 15     # unknown


class ConstraintChecker:
    """Multi-signal constraint system for word identification."""

    def __init__(self, dictionary: Dictionary):
        self.dictionary = dictionary

    def get_word_constraints(self, word: str) -> Dict[str, int]:
        """
        Extract all constraint signals for a word.

        Returns dict with:
            rank: frequency rank (1-249777)
            pos: POS category (0-15)
            length: character count
            first_char: ord of first character (0-25 for a-z)
        """
        w = word.lower().strip()
        rank = self.dictionary.word_to_rank(w) or 0
        return {
            'rank': rank,
            'pos': self._get_pos(w),
            'length': len(w),
            'first_char': ord(w[0]) - ord('a') if w and w[0].isalpha() else 0,
        }

    def encode_constraints(self, word: str) -> bytes:
        """
        Encode word constraints into minimal bytes for storage.

        Format (5 bytes):
          [rank: 1-3 bytes variable] [pos_and_length: 1 byte] [first_char: 1 byte]

        pos_and_length packs: high 4 bits = POS, low 4 bits = min(length, 15)
        """
        from ..wordid.word_id_codec import WordIdCodec
        codec = WordIdCodec()

        c = self.get_word_constraints(word)
        buf = bytearray()

        # Rank (variable 1-3 bytes) - this alone is sufficient for single-blank
        if c['rank'] > 0:
            buf.extend(codec.encode_rank(c['rank']))
        else:
            buf.extend(codec.encode_unknown(word))  # inline unknown word

        # POS (4 bits) + length (4 bits) packed into 1 byte
        pos_len = ((c['pos'] & 0x0F) << 4) | (min(c['length'], 15) & 0x0F)
        buf.append(pos_len)

        # First character (1 byte)
        buf.append(c['first_char'] & 0x1F)

        return bytes(buf)

    def decode_constraints(self, data: bytes, offset: int = 0) -> Tuple[dict, int]:
        """
        Decode constraint bytes back to constraint dict.

        Returns (constraints_dict, bytes_consumed).
        """
        from ..wordid.word_id_codec import WordIdCodec
        codec = WordIdCodec()

        start = offset

        # Rank
        if codec.is_unknown_marker(data, offset):
            from ..wordid.unknown_handler import UnknownHandler
            word, consumed = UnknownHandler.decode(data, offset)
            offset += consumed
            rank = 0
            inline_word = word
        else:
            rank, consumed = codec.decode_rank(data, offset)
            offset += consumed
            inline_word = None

        # POS + length
        pos_len = data[offset]
        offset += 1
        pos = (pos_len >> 4) & 0x0F
        length = pos_len & 0x0F

        # First char
        first_char = data[offset] & 0x1F
        offset += 1

        result = {
            'rank': rank,
            'pos': pos,
            'length': length,
            'first_char': first_char,
        }
        if inline_word:
            result['inline_word'] = inline_word

        return result, offset - start

    def resolve_word(self, constraints: dict) -> Optional[str]:
        """
        Resolve a word from its constraint signals.

        For single-blank-per-partition, rank alone is sufficient.
        Additional signals provide redundancy and enable multi-blank.
        """
        # If we have an inline unknown word, return it directly
        if 'inline_word' in constraints:
            return constraints['inline_word']

        # Rank uniquely identifies the word
        rank = constraints.get('rank', 0)
        if rank > 0:
            word = self.dictionary.rank_to_word(rank)
            if word:
                return word

        return None

    def compute_line_word_counts(self, tokens) -> List[int]:
        """
        Compute how many words are on each line.

        This is stored in the compressed blob so the decoder can
        reconstruct the full grid and detect gaps.
        """
        from collections import Counter
        line_counts = Counter()
        for token in tokens:
            line_counts[token.line_number] += 1

        if not line_counts:
            return []

        max_line = max(line_counts.keys())
        return [line_counts.get(ln, 0) for ln in range(1, max_line + 1)]

    def _get_pos(self, word: str) -> int:
        """Simple POS categorization heuristic."""
        if word in _FUNCTION_WORDS:
            return POS_FUNCTION
        # Heuristic suffixes
        if word.endswith(('tion', 'sion', 'ment', 'ness', 'ity', 'ence', 'ance')):
            return POS_NOUN
        if word.endswith(('ing', 'ed', 'ize', 'ify', 'ate')):
            return POS_VERB
        if word.endswith(('ful', 'less', 'ous', 'ive', 'able', 'ible', 'al', 'ic')):
            return POS_ADJ
        if word.endswith('ly'):
            return POS_ADV
        return POS_NOUN  # default: noun
