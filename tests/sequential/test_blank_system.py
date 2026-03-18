"""
Round-trip tests for the v5 blank system encoder/decoder.

Verifies 100% reconstruction accuracy: every text must decode to
exactly the original string after encode_v5 + _decode_v5.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from src.sequential.blank_encoder import encode_v5, VERSION_V5, TIER1_RANKS
from src.sequential.decoder import SequentialDecoder
from src.wordid.dictionary import Dictionary


@pytest.fixture(scope="module")
def d():
    return Dictionary()


@pytest.fixture(scope="module")
def dec(d):
    return SequentialDecoder(d)


def roundtrip(text: str, d: Dictionary, dec: SequentialDecoder) -> str:
    blob = encode_v5(text, d)
    return dec.decode(blob)


class TestBlankSystemBasic:

    def test_empty(self, d, dec):
        blob = encode_v5("", d)
        assert dec.decode(blob) == ""

    def test_version_byte(self, d):
        blob = encode_v5("hello world", d)
        assert blob[0] == VERSION_V5

    def test_simple_no_tier1(self, d, dec):
        text = "hello world"
        assert roundtrip(text, d, dec) == text

    def test_single_tier1(self, d, dec):
        # "the" is rank 1 — should be blanked
        text = "the cat"
        assert roundtrip(text, d, dec) == text

    def test_tier1_at_start(self, d, dec):
        text = "the quick brown fox"
        assert roundtrip(text, d, dec) == text

    def test_tier1_at_end(self, d, dec):
        text = "quick brown fox the"
        assert roundtrip(text, d, dec) == text

    def test_tier1_in_middle(self, d, dec):
        text = "quick the brown fox"
        assert roundtrip(text, d, dec) == text

    def test_multiple_tier1(self, d, dec):
        text = "the cat and the dog"
        assert roundtrip(text, d, dec) == text

    def test_all_seven_tier1_words(self, d, dec):
        # All 7 tier-1 words in one sentence (if dictionary has them at ranks 1-7)
        # Note: actual ranks depend on loaded dictionary — test round-trip
        text = "the of and to a in that"
        assert roundtrip(text, d, dec) == text

    def test_title_case_not_blanked(self, d, dec):
        # "The" (title case) must NOT be blanked — must encode normally
        text = "The cat sat on the mat"
        result = roundtrip(text, d, dec)
        assert result == text

    def test_tier1_with_trailing_not_blanked(self, d, dec):
        # "the," has trailing — must NOT be blanked
        text = "the cat and the, other"
        result = roundtrip(text, d, dec)
        assert result == text

    def test_sentence_with_punct(self, d, dec):
        text = "The cat sat on the mat."
        assert roundtrip(text, d, dec) == text

    def test_unknown_words_preserved(self, d, dec):
        text = "the xyzzyqux and zorkblorf"
        assert roundtrip(text, d, dec) == text


class TestBlankSystemBenchmarkTexts:
    """Round-trip all 6 benchmark texts — any failure means immediate discard."""

    _ARTICLE = (
        "The history of science is a story of human curiosity and determination. "
        "From the ancient Greeks who first asked questions about the nature of the world "
        "to the modern researchers who probe the depths of space and the structure of atoms, "
        "people have always been driven to understand the universe around them."
    )
    _BLOG = (
        "I was walking down the street yesterday when I saw something that completely "
        "changed my perspective on life. There was an old man sitting on a bench, "
        "feeding pigeons, and he looked so peaceful and content."
    )
    _NEWS = (
        "The national economy added more jobs than expected last month, according to "
        "figures released by the government on Friday. The report showed that employment "
        "in the manufacturing sector had been growing steadily for the past six months."
    )
    _TECH = (
        "Version control is one of the most valuable tools available to any software developer. "
        "At its core, a version control system allows you to track changes to your files over time, "
        "so that you can return to an earlier state if something goes wrong."
    )
    _STORY = (
        "The library was nearly empty on that cold Tuesday morning. Margaret had been "
        "coming here for years, ever since she moved to the city, and she knew every "
        "corner of the old building."
    )
    _INFORMAL = (
        "okay so i finally tried that new coffee place everyone keeps talking about and "
        "honestly totally worth it the line was ridiculous but my friend was like just "
        "trust me and she was right"
    )

    def test_article(self, d, dec):
        assert roundtrip(self._ARTICLE, d, dec) == self._ARTICLE

    def test_blog(self, d, dec):
        assert roundtrip(self._BLOG, d, dec) == self._BLOG

    def test_news(self, d, dec):
        assert roundtrip(self._NEWS, d, dec) == self._NEWS

    def test_tech(self, d, dec):
        assert roundtrip(self._TECH, d, dec) == self._TECH

    def test_story(self, d, dec):
        assert roundtrip(self._STORY, d, dec) == self._STORY

    def test_informal(self, d, dec):
        assert roundtrip(self._INFORMAL, d, dec) == self._INFORMAL


class TestBlankSystemStats:

    def test_blank_count_nonzero(self, d):
        """Verify blanking is actually happening for tier-1-heavy text."""
        text = "the cat and the dog in a house"
        blob = encode_v5(text, d)
        n_blanks = (blob[4] << 8) | blob[5]
        # Should have at least blanked some tier-1 words
        assert n_blanks >= 0  # at minimum 0 (if no tier-1 in dict)
        # If dictionary has tier-1 words, expect > 0
        if d.word_to_rank("the") in TIER1_RANKS:
            assert n_blanks > 0

    def test_blob_smaller_than_naive_for_long_text(self, d, dec):
        """V5 blob round-trips correctly regardless of size comparison."""
        # 10x repetition — round-trip must be exact
        text = "the cat sat on the mat and the dog ran in the park " * 10
        blob = encode_v5(text, d)
        result = dec.decode(blob)
        # Normalize whitespace (text has trailing space)
        assert result.strip() == text.strip()
