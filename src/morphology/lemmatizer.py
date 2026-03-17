"""
Lemmatizer: word -> (base_form, morph_flag)

Reduces inflected words to their base form + a morphology flag byte.
This merges word variants into a single inverted index entry,
improving coordinate template hits and reducing unique word count.

Example: "running" -> ("run", MORPH_ING)
         "dogs"    -> ("dog", MORPH_S)
         "went"    -> ("go", MORPH_IRREG_PAST)
"""

from typing import Tuple, Optional


# Morphology flag constants
MORPH_BASE = 0x00       # base form, no transformation
MORPH_S = 0x01          # -s (plural / 3rd person singular)
MORPH_ED = 0x02         # -ed (past tense, regular)
MORPH_ING = 0x03        # -ing (progressive)
MORPH_ER = 0x04         # -er (comparative)
MORPH_EST = 0x05        # -est (superlative)
MORPH_LY = 0x06         # -ly (adverb from adjective)
MORPH_NESS = 0x07       # -ness (noun from adjective)
MORPH_TION = 0x08       # -tion/-sion (nominalization)
MORPH_ABLE = 0x09       # -able/-ible
MORPH_MENT = 0x0A       # -ment
MORPH_FUL = 0x0B        # -ful
MORPH_LESS = 0x0C       # -less
MORPH_OUS = 0x0D        # -ous/-ious
MORPH_UN = 0x0E         # un- prefix
MORPH_RE = 0x0F         # re- prefix

# Irregular forms: 0x10-0x3F (each ambiguous form gets its own flag)
MORPH_IRREG_PAST = 0x10        # irregular past tense (went, came, saw...)
MORPH_IRREG_PAST_PART = 0x11   # irregular past participle (gone, seen, taken...)
MORPH_IRREG_PLURAL = 0x13      # irregular plural (children, men, women...)
# Specific irregular present forms of "be" (each needs unique flag)
MORPH_IRREG_IS = 0x14          # is -> be
MORPH_IRREG_AM = 0x15          # am -> be
MORPH_IRREG_ARE = 0x16         # are -> be
# Specific irregular past forms of "be"
MORPH_IRREG_WAS = 0x17         # was -> be
MORPH_IRREG_WERE = 0x18        # were -> be

# Common irregular verb mappings: inflected -> (base, flag)
_IRREGULAR_VERBS = {
    "went": ("go", MORPH_IRREG_PAST),
    "gone": ("go", MORPH_IRREG_PAST_PART),
    "goes": ("go", MORPH_S),
    "going": ("go", MORPH_ING),
    "came": ("come", MORPH_IRREG_PAST),
    "coming": ("come", MORPH_ING),
    "saw": ("see", MORPH_IRREG_PAST),
    "seen": ("see", MORPH_IRREG_PAST_PART),
    "seeing": ("see", MORPH_ING),
    "took": ("take", MORPH_IRREG_PAST),
    "taken": ("take", MORPH_IRREG_PAST_PART),
    "taking": ("take", MORPH_ING),
    "gave": ("give", MORPH_IRREG_PAST),
    "given": ("give", MORPH_IRREG_PAST_PART),
    "giving": ("give", MORPH_ING),
    "got": ("get", MORPH_IRREG_PAST),
    "gotten": ("get", MORPH_IRREG_PAST_PART),
    "getting": ("get", MORPH_ING),
    "made": ("make", MORPH_IRREG_PAST),
    "making": ("make", MORPH_ING),
    "said": ("say", MORPH_IRREG_PAST),
    "saying": ("say", MORPH_ING),
    "did": ("do", MORPH_IRREG_PAST),
    "done": ("do", MORPH_IRREG_PAST_PART),
    "doing": ("do", MORPH_ING),
    "was": ("be", MORPH_IRREG_WAS),
    "were": ("be", MORPH_IRREG_WERE),
    "am": ("be", MORPH_IRREG_AM),
    "is": ("be", MORPH_IRREG_IS),
    "are": ("be", MORPH_IRREG_ARE),
    "been": ("be", MORPH_IRREG_PAST_PART),
    "being": ("be", MORPH_ING),
    "had": ("have", MORPH_IRREG_PAST),
    "has": ("have", MORPH_S),
    "having": ("have", MORPH_ING),
    "ran": ("run", MORPH_IRREG_PAST),
    "running": ("run", MORPH_ING),
    "ate": ("eat", MORPH_IRREG_PAST),
    "eaten": ("eat", MORPH_IRREG_PAST_PART),
    "eating": ("eat", MORPH_ING),
    "wrote": ("write", MORPH_IRREG_PAST),
    "written": ("write", MORPH_IRREG_PAST_PART),
    "writing": ("write", MORPH_ING),
    "spoke": ("speak", MORPH_IRREG_PAST),
    "spoken": ("speak", MORPH_IRREG_PAST_PART),
    "speaking": ("speak", MORPH_ING),
    "broke": ("break", MORPH_IRREG_PAST),
    "broken": ("break", MORPH_IRREG_PAST_PART),
    "breaking": ("break", MORPH_ING),
    "drove": ("drive", MORPH_IRREG_PAST),
    "driven": ("drive", MORPH_IRREG_PAST_PART),
    "driving": ("drive", MORPH_ING),
    "flew": ("fly", MORPH_IRREG_PAST),
    "flown": ("fly", MORPH_IRREG_PAST_PART),
    "knew": ("know", MORPH_IRREG_PAST),
    "known": ("know", MORPH_IRREG_PAST_PART),
    "thought": ("think", MORPH_IRREG_PAST),
    "thinking": ("think", MORPH_ING),
    "brought": ("bring", MORPH_IRREG_PAST),
    "bringing": ("bring", MORPH_ING),
    "bought": ("buy", MORPH_IRREG_PAST),
    "buying": ("buy", MORPH_ING),
    "caught": ("catch", MORPH_IRREG_PAST),
    "taught": ("teach", MORPH_IRREG_PAST),
    "teaching": ("teach", MORPH_ING),
    "told": ("tell", MORPH_IRREG_PAST),
    "telling": ("tell", MORPH_ING),
    "found": ("find", MORPH_IRREG_PAST),
    "finding": ("find", MORPH_ING),
    "felt": ("feel", MORPH_IRREG_PAST),
    "feeling": ("feel", MORPH_ING),
    "left": ("leave", MORPH_IRREG_PAST),
    "leaving": ("leave", MORPH_ING),
    "kept": ("keep", MORPH_IRREG_PAST),
    "keeping": ("keep", MORPH_ING),
    "meant": ("mean", MORPH_IRREG_PAST),
    "met": ("meet", MORPH_IRREG_PAST),
    "meeting": ("meet", MORPH_ING),
    "sat": ("sit", MORPH_IRREG_PAST),
    "sitting": ("sit", MORPH_ING),
    "stood": ("stand", MORPH_IRREG_PAST),
    "standing": ("stand", MORPH_ING),
    "lost": ("lose", MORPH_IRREG_PAST),
    "losing": ("lose", MORPH_ING),
    "paid": ("pay", MORPH_IRREG_PAST),
    "paying": ("pay", MORPH_ING),
    "sent": ("send", MORPH_IRREG_PAST),
    "sending": ("send", MORPH_ING),
    "built": ("build", MORPH_IRREG_PAST),
    "building": ("build", MORPH_ING),
    "spent": ("spend", MORPH_IRREG_PAST),
    "spending": ("spend", MORPH_ING),
    "heard": ("hear", MORPH_IRREG_PAST),
    "hearing": ("hear", MORPH_ING),
    "read": ("read", MORPH_IRREG_PAST),  # same spelling
    "reading": ("read", MORPH_ING),
    "held": ("hold", MORPH_IRREG_PAST),
    "holding": ("hold", MORPH_ING),
    "began": ("begin", MORPH_IRREG_PAST),
    "begun": ("begin", MORPH_IRREG_PAST_PART),
    "won": ("win", MORPH_IRREG_PAST),
    "winning": ("win", MORPH_ING),
    # Irregular plurals
    "children": ("child", MORPH_IRREG_PLURAL),
    "men": ("man", MORPH_IRREG_PLURAL),
    "women": ("woman", MORPH_IRREG_PLURAL),
    "people": ("person", MORPH_IRREG_PLURAL),
    "mice": ("mouse", MORPH_IRREG_PLURAL),
    "feet": ("foot", MORPH_IRREG_PLURAL),
    "teeth": ("tooth", MORPH_IRREG_PLURAL),
}


class Lemmatizer:
    """Reduce inflected words to base form + morphology flag."""

    def __init__(self, dictionary=None):
        """
        Args:
            dictionary: Optional Dictionary instance. If provided, only lemmatize
                       when the base form exists in the dictionary (prevents
                       false lemmatizations).
        """
        self.dictionary = dictionary

    def lemmatize(self, word: str) -> Tuple[str, int]:
        """
        Attempt to reduce word to base form + morph flag.

        Returns:
            (base_form, morph_flag) if lemmatization found,
            (word, MORPH_BASE) if word is already a base form.
        """
        w = word.lower().strip()

        # Check irregular forms first
        if w in _IRREGULAR_VERBS:
            base, flag = _IRREGULAR_VERBS[w]
            if self._base_valid(base):
                return (base, flag)

        # Try regular suffix rules (longest match first)
        result = self._try_regular_suffixes(w)
        if result is not None:
            return result

        # Try prefix rules
        result = self._try_prefixes(w)
        if result is not None:
            return result

        return (w, MORPH_BASE)

    def _try_regular_suffixes(self, word: str) -> Optional[Tuple[str, int]]:
        """Try regular suffix stripping rules."""
        # Order matters: try longer/more specific suffixes first

        # -fulness -> -ful (compound suffix, skip for now)
        # -lessly -> -less (compound suffix, skip for now)

        # -ness
        if word.endswith("ness") and len(word) > 5:
            base = word[:-4]
            if base.endswith("i"):
                base = base[:-1] + "y"  # happiness -> happy
            if self._base_valid(base):
                return (base, MORPH_NESS)

        # -ment
        if word.endswith("ment") and len(word) > 5:
            base = word[:-4]
            if self._base_valid(base):
                return (base, MORPH_MENT)

        # -tion / -sion
        if word.endswith("tion") and len(word) > 5:
            base = word[:-4] + "t"  # creation -> creat... not great
            # Skip: -tion lemmatization is unreliable without full dictionary
            pass
        if word.endswith("sion") and len(word) > 5:
            pass

        # -able / -ible
        if word.endswith("able") and len(word) > 5:
            base = word[:-4]
            if base.endswith("i"):
                base = base[:-1] + "y"
            if self._base_valid(base):
                return (base, MORPH_ABLE)

        # -ful
        if word.endswith("ful") and len(word) > 4:
            base = word[:-3]
            if self._base_valid(base):
                return (base, MORPH_FUL)

        # -less
        if word.endswith("less") and len(word) > 5:
            base = word[:-4]
            if self._base_valid(base):
                return (base, MORPH_LESS)

        # -ous / -ious
        if word.endswith("ous") and len(word) > 4:
            base = word[:-3]
            if self._base_valid(base):
                return (base, MORPH_OUS)

        # -ly (adverb from adjective)
        if word.endswith("ly") and len(word) > 3:
            base = word[:-2]
            if base.endswith("i"):
                base = base[:-1] + "y"  # easily -> easy
            if base.endswith("ical"):
                pass  # basically -> basic, skip complex
            if self._base_valid(base):
                return (base, MORPH_LY)

        # -ing
        if word.endswith("ing") and len(word) > 4:
            # running -> run (doubled consonant)
            base = word[:-3]
            if base and base[-1] == base[-2:] and len(base) > 2:
                base_short = base[:-1]
                if self._base_valid(base_short):
                    return (base_short, MORPH_ING)
            # making -> make (dropped e)
            if self._base_valid(base + "e"):
                return (base + "e", MORPH_ING)
            if self._base_valid(base):
                return (base, MORPH_ING)

        # -ed (past tense regular)
        if word.endswith("ed") and len(word) > 3:
            base = word[:-2]
            # stopped -> stop (doubled consonant)
            if base and len(base) > 2 and base[-1] == base[-2]:
                base_short = base[:-1]
                if self._base_valid(base_short):
                    return (base_short, MORPH_ED)
            # loved -> love (dropped e)
            if self._base_valid(base + "e"):
                return (base + "e", MORPH_ED)
            # carried -> carry
            if base.endswith("i"):
                base_y = base[:-1] + "y"
                if self._base_valid(base_y):
                    return (base_y, MORPH_ED)
            if self._base_valid(base):
                return (base, MORPH_ED)

        # -er (comparative)
        if word.endswith("er") and len(word) > 3:
            base = word[:-2]
            if base and len(base) > 2 and base[-1] == base[-2]:
                base_short = base[:-1]
                if self._base_valid(base_short):
                    return (base_short, MORPH_ER)
            if self._base_valid(base + "e"):
                return (base + "e", MORPH_ER)
            if self._base_valid(base):
                return (base, MORPH_ER)

        # -est (superlative)
        if word.endswith("est") and len(word) > 4:
            base = word[:-3]
            if self._base_valid(base + "e"):
                return (base + "e", MORPH_EST)
            if self._base_valid(base):
                return (base, MORPH_EST)

        # -s (plural / 3rd person)
        if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
            # -ies -> -y (carries -> carry)
            if word.endswith("ies"):
                base = word[:-3] + "y"
                if self._base_valid(base):
                    return (base, MORPH_S)
            # Try plain -s FIRST (makes -> make, dogs -> dog)
            base = word[:-1]
            if self._base_valid(base):
                return (base, MORPH_S)
            # Then try -es (boxes -> box, watches -> watch)
            if word.endswith("es") and len(word) > 3:
                base = word[:-2]
                if self._base_valid(base):
                    return (base, MORPH_S)

        return None

    def _try_prefixes(self, word: str) -> Optional[Tuple[str, int]]:
        """Try prefix stripping rules."""
        # un-
        if word.startswith("un") and len(word) > 3:
            base = word[2:]
            if self._base_valid(base):
                return (base, MORPH_UN)

        # re-
        if word.startswith("re") and len(word) > 3:
            base = word[2:]
            if self._base_valid(base):
                return (base, MORPH_RE)

        return None

    def _base_valid(self, base: str) -> bool:
        """Check if base form is valid (exists in dictionary if one is provided)."""
        if not base or len(base) < 2:
            return False
        if self.dictionary is not None:
            return self.dictionary.has_word(base)
        return True  # no dictionary = accept any base
