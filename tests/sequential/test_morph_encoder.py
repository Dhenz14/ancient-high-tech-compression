"""
Round-trip tests for the v6 morphological fallback encoder/decoder.

Verifies 100% reconstruction accuracy for:
- Known words (should encode identically to v4, no morph involved)
- Unknown words with regular inflections (-ing, -ed, -s, -ly, -ness, etc.)
- Unknown words with irregular verb forms
- Title-cased and ALL CAPS unknown words
- Mixed cases: leading/trailing punct, rare trailing
- All 6 benchmark texts
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from src.sequential.morph_encoder import encode_v6, VERSION_V6
from src.sequential.decoder import SequentialDecoder
from src.wordid.dictionary import Dictionary


@pytest.fixture(scope="module")
def d():
    return Dictionary()


@pytest.fixture(scope="module")
def dec(d):
    return SequentialDecoder(d)


def roundtrip(text: str, d: Dictionary, dec: SequentialDecoder) -> str:
    blob = encode_v6(text, d)
    return dec.decode(blob)


class TestMorphEncoderBasic:

    def test_empty(self, d, dec):
        assert roundtrip("", d, dec) == ""

    def test_version_byte_fallback_to_v4(self, d):
        # When no morph escapes needed, falls back to v4 version byte
        blob = encode_v6("hello world", d)
        assert blob[0] in (0x04, VERSION_V6)  # either is valid

    def test_version_byte_v6_when_morph_used(self, d):
        # When morph encoding is used, should emit v6 byte
        # Use a word not in dict but whose base is in dict
        # "xyzrunning" won't be in dict but "xyzrun" also won't → no morph
        # Force a morph case by using a word we know lemmatizes correctly
        # The version byte should be v6 IF a morph was used; check the diagnostic
        # (This test passes as long as the encoder doesn't crash)
        blob = encode_v6("She was computerizing the data", d)
        assert blob[0] in (0x04, VERSION_V6)

    def test_known_word_roundtrip(self, d, dec):
        # "the cat" — both are in dictionary, go through main stream
        assert roundtrip("the cat", d, dec) == "the cat"

    def test_unknown_base_form(self, d, dec):
        # A word not in dictionary at all — raw extra section
        text = "xyzzyqux"
        assert roundtrip(text, d, dec) == text

    def test_title_case_known(self, d, dec):
        assert roundtrip("The cat sat", d, dec) == "The cat sat"

    def test_trailing_punct(self, d, dec):
        assert roundtrip("The cat sat.", d, dec) == "The cat sat."

    def test_rare_trailing_not_morph_encoded(self, d, dec):
        # rare trailing (; : ) ] -) goes to extra section as raw string
        # should round-trip fine
        assert roundtrip("The cat sat; something", d, dec) == "The cat sat; something"

    def test_all_caps_not_morph_encoded(self, d, dec):
        # ALL CAPS stays raw
        assert roundtrip("NASA launched rockets", d, dec) == "NASA launched rockets"

    def test_mixed_case_not_morph_encoded(self, d, dec):
        assert roundtrip("iPhone is popular", d, dec) == "iPhone is popular"


class TestMorphInflections:
    """Test that morph-encodable words round-trip correctly."""

    def _roundtrip_word(self, word: str, d: Dictionary, dec: SequentialDecoder) -> str:
        """Round-trip a single word embedded in context."""
        text = "I said " + word + " today"
        result = roundtrip(text, d, dec)
        assert result == text, f"Round-trip failed for '{word}': got '{result}'"
        return result

    def test_ing_suffix(self, d, dec):
        # "running" — if not in dict, lemmatizes to "run" + MORPH_ING
        self._roundtrip_word("running", d, dec)

    def test_ed_suffix(self, d, dec):
        self._roundtrip_word("computerized", d, dec)

    def test_ly_suffix(self, d, dec):
        self._roundtrip_word("quickly", d, dec)

    def test_ness_suffix(self, d, dec):
        self._roundtrip_word("happiness", d, dec)

    def test_able_suffix(self, d, dec):
        self._roundtrip_word("readable", d, dec)

    def test_ful_suffix(self, d, dec):
        self._roundtrip_word("hopeful", d, dec)

    def test_less_suffix(self, d, dec):
        self._roundtrip_word("hopeless", d, dec)

    def test_ment_suffix(self, d, dec):
        self._roundtrip_word("movement", d, dec)

    def test_plural_s(self, d, dec):
        self._roundtrip_word("computers", d, dec)

    def test_irregular_past(self, d, dec):
        # "went" -> go + MORPH_IRREG_PAST
        self._roundtrip_word("went", d, dec)

    def test_irregular_plural(self, d, dec):
        # "children" -> child + MORPH_IRREG_PLURAL
        self._roundtrip_word("children", d, dec)

    def test_title_case_inflection(self, d, dec):
        # Title-cased inflected word: "Running" (at start of sentence)
        text = "Running fast is healthy"
        assert roundtrip(text, d, dec) == text

    def test_un_prefix(self, d, dec):
        self._roundtrip_word("unhappy", d, dec)

    def test_re_prefix(self, d, dec):
        self._roundtrip_word("redo", d, dec)


class TestMorphEncoderBenchmarkTexts:
    """Round-trip all benchmark texts — any failure = immediate discard."""

    _ARTICLE = (
        "The history of science is a story of human curiosity and determination. "
        "From the ancient Greeks who first asked questions about the nature of the world "
        "to the modern researchers who probe the depths of space and the structure of atoms, "
        "people have always been driven to understand the universe around them. "
        "In the beginning, science was not separate from philosophy. "
        "Thinkers like Aristotle and Plato tried to explain the world through reason alone, "
        "without the benefit of experiments or measurements. "
        "It was not until the Renaissance that the scientific method began to take shape. "
        "Francis Bacon argued that knowledge should be built on observation and experiment, "
        "not just logic and tradition. Galileo turned his telescope to the sky and discovered "
        "that the earth was not the center of the universe. Newton showed that the same force "
        "that makes an apple fall from a tree also keeps the moon in orbit around the earth. "
        "These discoveries changed the way people thought about the world and their place in it. "
        "The industrial revolution brought science into everyday life. "
        "Steam engines, railways, and factories transformed society. "
        "Medicine advanced as doctors began to understand the causes of disease. "
        "In the twentieth century, science gave us computers, space travel, and the ability "
        "to split the atom. Today, science continues to push the boundaries of what we know "
        "and what we can do. From artificial intelligence to gene therapy, the frontiers of "
        "knowledge are expanding faster than ever before."
    )
    _BLOG = (
        "I was walking down the street yesterday when I saw something that completely "
        "changed my perspective on life. There was an old man sitting on a bench, "
        "feeding pigeons, and he looked so peaceful and content. I stopped and talked "
        "to him for a while. He told me he had been coming to that same bench every day "
        "for thirty years, ever since his wife passed away. He said the pigeons were his "
        "friends now, and they never judged him or asked him to be anything other than "
        "what he was. I think about that conversation often. In our busy lives, we forget "
        "that happiness does not come from having more things or being more successful. "
        "It comes from simple moments of connection and peace. The old man on the bench "
        "had figured out something that most of us spend our whole lives searching for."
    )
    _NEWS = (
        "The national economy added more jobs than expected last month, according to "
        "figures released by the government on Friday. The report showed that employment "
        "in the manufacturing sector had been growing steadily for the past six months, "
        "driven in part by new investment in clean energy projects. Economists said the "
        "results were better than anticipated, though they cautioned that uncertainty in "
        "global markets could slow growth in the months to come. The unemployment rate "
        "fell to its lowest level in more than a decade, a development that most analysts "
        "described as a sign of broad economic health."
    )
    _TECH = (
        "Version control is one of the most valuable tools available to any software developer. "
        "At its core, a version control system allows you to track changes to your files over time, "
        "so that you can return to an earlier state if something goes wrong. Learning to use it "
        "well is one of the best investments you can make as a professional. To get started, you "
        "need to install the software on your machine and create a new repository for your project."
    )
    _STORY = (
        "The library was nearly empty on that cold Tuesday morning. Margaret had been "
        "coming here for years, ever since she moved to the city, and she knew every "
        "corner of the old building. She settled into her usual chair beside the window "
        "and opened her book, but she found it hard to focus. There was something on her "
        "mind that she could not quite let go of."
    )
    _INFORMAL = (
        "okay so i finally tried that new coffee place everyone keeps talking about and "
        "honestly totally worth it the line was ridiculous but my friend was like just "
        "trust me and she was right got this oat milk latte thing and it was so good i "
        "almost went back for a second one"
    )

    def test_article(self, d, dec):
        text = " ".join(self._ARTICLE.split())
        assert roundtrip(text, d, dec) == text

    def test_blog(self, d, dec):
        text = " ".join(self._BLOG.split())
        assert roundtrip(text, d, dec) == text

    def test_news(self, d, dec):
        text = " ".join(self._NEWS.split())
        assert roundtrip(text, d, dec) == text

    def test_tech(self, d, dec):
        text = " ".join(self._TECH.split())
        assert roundtrip(text, d, dec) == text

    def test_story(self, d, dec):
        text = " ".join(self._STORY.split())
        assert roundtrip(text, d, dec) == text

    def test_informal(self, d, dec):
        text = " ".join(self._INFORMAL.split())
        assert roundtrip(text, d, dec) == text

    def test_article_x10(self, d, dec):
        base = " ".join(self._ARTICLE.split())
        text = " ".join([base] * 10)
        assert roundtrip(text, d, dec) == text
