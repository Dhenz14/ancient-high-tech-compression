"""
Inflector: (base_form, morph_flag) -> inflected word.

Reverse of Lemmatizer: reconstructs the original inflected form
from the base word and morphology flag.
"""

from .lemmatizer import (
    MORPH_BASE, MORPH_S, MORPH_ED, MORPH_ING, MORPH_ER, MORPH_EST,
    MORPH_LY, MORPH_NESS, MORPH_TION, MORPH_ABLE, MORPH_MENT,
    MORPH_FUL, MORPH_LESS, MORPH_OUS, MORPH_UN, MORPH_RE,
    MORPH_IRREG_PAST, MORPH_IRREG_PAST_PART,
    MORPH_IRREG_PLURAL,
    MORPH_IRREG_IS, MORPH_IRREG_AM, MORPH_IRREG_ARE,
    MORPH_IRREG_WAS, MORPH_IRREG_WERE,
    _IRREGULAR_VERBS,
)


# Build reverse lookup: (base, flag) -> inflected form
_REVERSE_IRREGULARS: dict = {}
for inflected, (base, flag) in _IRREGULAR_VERBS.items():
    key = (base, flag)
    # Keep first (most common) mapping if duplicates
    if key not in _REVERSE_IRREGULARS:
        _REVERSE_IRREGULARS[key] = inflected


def _ends_with_consonant_y(word: str) -> bool:
    """Check if word ends with consonant + y."""
    if not word or word[-1] != 'y':
        return False
    if len(word) < 2:
        return False
    return word[-2] not in 'aeiou'


def _needs_doubled_consonant(word: str) -> bool:
    """Check if final consonant should be doubled before -ing/-ed/-er/-est.
    Only applies to short words (typically 1-syllable CVC words like run, sit, big).
    Multi-syllable words (discover, happen, enter) do NOT double."""
    if len(word) < 3 or len(word) > 6:
        return False
    vowels = set('aeiou')
    # CVC pattern: consonant-vowel-consonant at end
    if word[-1] not in vowels and word[-2] in vowels and word[-3] not in vowels:
        # Don't double w, x, y
        if word[-1] not in 'wxy':
            return True
    return False


class Inflector:
    """Reconstruct inflected word from base form + morphology flag."""

    def inflect(self, base: str, morph_flag: int) -> str:
        """
        Apply morphological transformation to base form.

        Args:
            base: base word form
            morph_flag: morphology flag byte

        Returns:
            Inflected word form.
        """
        if morph_flag == MORPH_BASE:
            return base

        # Handle specific "be" forms directly (avoid ambiguity)
        if morph_flag == MORPH_IRREG_IS:
            return "is"
        if morph_flag == MORPH_IRREG_AM:
            return "am"
        if morph_flag == MORPH_IRREG_ARE:
            return "are"
        if morph_flag == MORPH_IRREG_WAS:
            return "was"
        if morph_flag == MORPH_IRREG_WERE:
            return "were"

        # Check irregular reverse lookup
        key = (base, morph_flag)
        if key in _REVERSE_IRREGULARS:
            return _REVERSE_IRREGULARS[key]

        # Regular transformations
        if morph_flag == MORPH_S:
            return self._add_s(base)
        elif morph_flag == MORPH_ED:
            return self._add_ed(base)
        elif morph_flag == MORPH_ING:
            return self._add_ing(base)
        elif morph_flag == MORPH_ER:
            return self._add_er(base)
        elif morph_flag == MORPH_EST:
            return self._add_est(base)
        elif morph_flag == MORPH_LY:
            return self._add_ly(base)
        elif morph_flag == MORPH_NESS:
            return self._add_ness(base)
        elif morph_flag == MORPH_ABLE:
            return base + "able"
        elif morph_flag == MORPH_MENT:
            return base + "ment"
        elif morph_flag == MORPH_FUL:
            return base + "ful"
        elif morph_flag == MORPH_LESS:
            return base + "less"
        elif morph_flag == MORPH_OUS:
            return base + "ous"
        elif morph_flag == MORPH_UN:
            return "un" + base
        elif morph_flag == MORPH_RE:
            return "re" + base
        elif morph_flag == MORPH_TION:
            return base + "tion"

        # Unknown flag - return base unchanged
        return base

    def _add_s(self, base: str) -> str:
        if base.endswith(('s', 'sh', 'ch', 'x', 'z')):
            return base + "es"
        if _ends_with_consonant_y(base):
            return base[:-1] + "ies"
        return base + "s"

    def _add_ed(self, base: str) -> str:
        if base.endswith('e'):
            return base + "d"
        if _ends_with_consonant_y(base):
            return base[:-1] + "ied"
        if _needs_doubled_consonant(base):
            return base + base[-1] + "ed"
        return base + "ed"

    def _add_ing(self, base: str) -> str:
        if base.endswith('e') and not base.endswith('ee'):
            return base[:-1] + "ing"
        if base.endswith('ie'):
            return base[:-2] + "ying"
        if _needs_doubled_consonant(base):
            return base + base[-1] + "ing"
        return base + "ing"

    def _add_er(self, base: str) -> str:
        if base.endswith('e'):
            return base + "r"
        if _ends_with_consonant_y(base):
            return base[:-1] + "ier"
        if _needs_doubled_consonant(base):
            return base + base[-1] + "er"
        return base + "er"

    def _add_est(self, base: str) -> str:
        if base.endswith('e'):
            return base + "st"
        if _ends_with_consonant_y(base):
            return base[:-1] + "iest"
        if _needs_doubled_consonant(base):
            return base + base[-1] + "est"
        return base + "est"

    def _add_ly(self, base: str) -> str:
        if base.endswith('y'):
            return base[:-1] + "ily"
        if base.endswith('le'):
            return base[:-1] + "y"
        if base.endswith('ic'):
            return base + "ally"
        return base + "ly"

    def _add_ness(self, base: str) -> str:
        if base.endswith('y'):
            return base[:-1] + "iness"
        return base + "ness"
