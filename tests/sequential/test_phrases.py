"""
Phase 3 Phrase Detection Tests.

Tests cover:
  - Dictionary phrases property
  - Encoder _merge_phrases: normal merge, title case, blocked by punct, blocked by caps
  - Round-trip: encode + decode with phrases
  - No false merges: unknown phrases, punct-separated, wrong caps
  - Two-stage pipeline with phrases
"""

import json
import os
import tempfile

import pytest

from src.sequential.encoder import SequentialEncoder, C_LOWER, C_TITLE, C_UPPER, T_NONE, T_COMMA
from src.sequential.decoder import SequentialDecoder
from src.sequential.two_stage import TwoStageCompressor
from src.wordid.dictionary import Dictionary


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_dict_with_phrases(extra_phrases: dict = None) -> Dictionary:
    """
    Build a minimal Dictionary that includes a few phrases for testing.
    Uses a temp JSON file so Dictionary.phrases is populated correctly.
    """
    # Core single words with ranks matching realistic Brown freq order
    entries = {
        "the": 1, "and": 2, "of": 3, "to": 4, "a": 5,
        "in": 6, "that": 7, "he": 8, "it": 9, "for": 10,
        "was": 11, "his": 12, "is": 13, "with": 14, "be": 15,
        "not": 16, "as": 17, "you": 18, "at": 19, "world": 20,
        "have": 21, "from": 22, "or": 23, "had": 24, "but": 25,
        "been": 26, "they": 27, "its": 28, "who": 29, "will": 30,
        "said": 31, "each": 32, "she": 33, "do": 34, "how": 35,
        "her": 36, "if": 37, "up": 38, "time": 39, "go": 40,
    }
    # Add test phrases
    entries["in a"] = 100
    entries["to be"] = 101
    entries["it was"] = 102
    entries["had been"] = 103
    if extra_phrases:
        entries.update(extra_phrases)

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False, encoding='utf-8'
    ) as f:
        json.dump(entries, f)
        path = f.name

    d = Dictionary(cache_path=path)
    os.unlink(path)
    return d


def make_encoder_with_phrases(extra_phrases: dict = None) -> SequentialEncoder:
    d = make_dict_with_phrases(extra_phrases)
    return SequentialEncoder(dictionary=d)


def make_decoder_with_phrases(extra_phrases: dict = None) -> SequentialDecoder:
    d = make_dict_with_phrases(extra_phrases)
    return SequentialDecoder(dictionary=d)


# ── Dictionary.phrases property ───────────────────────────────────────────────

class TestDictionaryPhrasesProperty:

    def test_phrases_returns_frozenset(self):
        d = make_dict_with_phrases()
        assert isinstance(d.phrases, frozenset)

    def test_phrases_contains_space_entries(self):
        d = make_dict_with_phrases()
        assert "in a" in d.phrases
        assert "to be" in d.phrases
        assert "it was" in d.phrases

    def test_phrases_excludes_single_words(self):
        d = make_dict_with_phrases()
        assert "the" not in d.phrases
        assert "world" not in d.phrases

    def test_empty_dict_no_phrases(self):
        d = Dictionary.__new__(Dictionary)
        d._word_to_rank = {"hello": 1, "world": 2}
        d._rank_to_word = {1: "hello", 2: "world"}
        assert d.phrases == frozenset()

    def test_phrases_extra(self):
        d = make_dict_with_phrases({"had been": 200, "as well": 201})
        assert "had been" in d.phrases
        assert "as well" in d.phrases


# ── Encoder _merge_phrases ─────────────────────────────────────────────────

class TestMergePhrases:

    def test_basic_merge_lowercase(self):
        enc = make_encoder_with_phrases()
        tokens = enc._tokenize("it was a good time")
        lowered = [t[1] for t in tokens]
        # "it was" should be merged into one token
        assert "it was" in lowered
        assert "it" not in lowered
        assert "was" not in lowered

    def test_title_case_first_word_merges(self):
        enc = make_encoder_with_phrases()
        tokens = enc._tokenize("In a world of wonder")
        lowered = [t[1] for t in tokens]
        caps   = [t[2] for t in tokens]
        assert "in a" in lowered
        idx = lowered.index("in a")
        assert caps[idx] == C_TITLE  # original caps preserved

    def test_no_merge_trailing_punct_between(self):
        # "in, a" — comma between → no merge
        enc = make_encoder_with_phrases()
        tokens = enc._tokenize("in, a world")
        lowered = [t[1] for t in tokens]
        assert "in a" not in lowered
        assert "in" in lowered
        assert "a" in lowered

    def test_no_merge_both_title_case(self):
        # "In A world" — second word title case → skip
        enc = make_encoder_with_phrases()
        tokens = enc._tokenize("In A world")
        lowered = [t[1] for t in tokens]
        assert "in a" not in lowered

    def test_no_merge_all_caps_first_word(self):
        enc = make_encoder_with_phrases()
        tokens = enc._tokenize("IN a world")  # ALL CAPS first word
        lowered = [t[1] for t in tokens]
        assert "in a" not in lowered

    def test_no_merge_unknown_phrase(self):
        # "world time" is not a known phrase
        enc = make_encoder_with_phrases()
        tokens = enc._tokenize("world time is precious")
        lowered = [t[1] for t in tokens]
        assert "world time" not in lowered
        assert "world" in lowered
        assert "time" in lowered

    def test_no_merge_leading_punct_second_word(self):
        # "(a world" — leading paren on second word → no merge
        enc = make_encoder_with_phrases()
        tokens = enc._tokenize("in (a world)")
        lowered = [t[1] for t in tokens]
        assert "in a" not in lowered

    def test_trailing_punct_from_second_token(self):
        # "to be," — comma should end up on the merged phrase token
        enc = make_encoder_with_phrases()
        tokens = enc._tokenize("it wants to be, real")
        for orig, word, caps, lead, trail in tokens:
            if word == "to be":
                assert trail == T_COMMA
                break
        else:
            pytest.fail("phrase 'to be' not found in tokens")

    def test_no_merge_no_phrases_dict(self):
        # Encoder with no phrases in dict → all single words
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump({"the": 1, "in": 2, "a": 3, "world": 4}, f)
            path = f.name
        d = Dictionary(cache_path=path)
        os.unlink(path)
        enc = SequentialEncoder(dictionary=d)
        assert enc._phrases == frozenset()
        tokens = enc._tokenize("in a world")
        lowered = [t[1] for t in tokens]
        assert "in a" not in lowered
        assert "in" in lowered

    def test_multiple_phrases_in_text(self):
        enc = make_encoder_with_phrases()
        tokens = enc._tokenize("it was in a world where to be alive had been enough")
        lowered = [t[1] for t in tokens]
        assert "it was" in lowered
        assert "in a" in lowered
        assert "to be" in lowered
        assert "had been" in lowered


# ── Round-trip: encode → decode ────────────────────────────────────────────

class TestPhraseRoundtrip:

    def _roundtrip(self, text: str) -> str:
        d = make_dict_with_phrases()
        enc = SequentialEncoder(dictionary=d)
        dec = SequentialDecoder(dictionary=d)
        blob = enc.encode(text)
        return dec.decode(blob)

    def test_basic_phrase_roundtrip(self):
        text = "it was a great time to be alive"
        assert self._roundtrip(text) == text

    def test_title_case_phrase_roundtrip(self):
        text = "In a world of wonder to be or not to be"
        assert self._roundtrip(text) == text

    def test_phrase_with_trailing_punct_roundtrip(self):
        text = "it wants to be, or not to be"
        assert self._roundtrip(text) == text

    def test_no_phrase_text_unaffected(self):
        text = "the world is a beautiful place"
        assert self._roundtrip(text) == text

    def test_phrase_at_end_of_text(self):
        text = "the answer is to be"
        assert self._roundtrip(text) == text

    def test_phrase_at_start_of_text(self):
        text = "in a world of wonder"
        assert self._roundtrip(text) == text

    def test_decoder_handles_phrase_rank_transparently(self):
        # Decoder must return the full phrase string when rank_to_word returns "in a"
        d = make_dict_with_phrases()
        assert d.rank_to_word(100) == "in a"
        assert d.rank_to_word(101) == "to be"

    def test_two_stage_phrase_roundtrip(self):
        d = make_dict_with_phrases()
        ts = TwoStageCompressor(dictionary=d)
        texts = [
            "it was in a world where to be alive had been enough",
            "In a time of great change to be or not to be",
            "the answer is to be found in a careful study",
        ]
        for text in texts:
            result = ts.decompress(ts.compress(text))
            assert result == text, f"Failed for: {text!r}"
