"""Tests for the AI-optimized rank assignment optimizer."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.sequential.rank_optimizer import (
    RankOptimizer,
    _fast_encode,
    _score,
    TIER1_MAX_RANK,
    TIER2_MIN_RANK,
    TIER2_MAX_RANK,
)
from src.sequential.encoder import SequentialEncoder
from src.sequential.decoder import SequentialDecoder
from src.sequential.two_stage import TwoStageCompressor
from src.wordid.dictionary import Dictionary

DICT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'dictionary_cache.json')

ARTICLE = "The history of science is a story of human curiosity and determination. From the ancient Greeks who first asked questions about the nature of the world to the modern researchers who probe the depths of space and the structure of atoms, people have always been driven to understand the universe around them."

BLOG = "I was walking down the street yesterday when I saw something that completely changed my perspective on life. There was an old man sitting on a bench, feeding pigeons, and he looked so peaceful and content."

SKIP_REASON = "dictionary_cache.json not found"


@pytest.fixture
def optimizer():
    if not os.path.exists(DICT_PATH):
        pytest.skip(SKIP_REASON)
    return RankOptimizer(DICT_PATH)


# === Phase 1: Frequency Re-ranking ===

class TestFrequencyReranking:

    def test_rerank_preserves_word_set(self, optimizer):
        ranks = optimizer.rerank_by_frequency()
        assert set(ranks.keys()) == optimizer._all_words

    def test_rerank_preserves_rank_uniqueness(self, optimizer):
        ranks = optimizer.rerank_by_frequency()
        values = list(ranks.values())
        assert len(values) == len(set(values)), "Duplicate ranks found"

    def test_rerank_rank_range(self, optimizer):
        ranks = optimizer.rerank_by_frequency()
        assert min(ranks.values()) == 1
        assert max(ranks.values()) == len(ranks)

    def test_top3_are_common_words(self, optimizer):
        ranks = optimizer.rerank_by_frequency()
        top3 = {w for w, r in ranks.items() if r <= TIER1_MAX_RANK}
        common = {"the", "of", "and", "to", "a", "in"}
        assert len(top3 & common) >= 2, f"Top 3 should be common words, got {top3}"

    def test_common_modern_words_in_tier2(self, optimizer):
        ranks = optimizer.rerank_by_frequency()
        modern_words = ["government", "system", "program", "world", "people"]
        for w in modern_words:
            if w in ranks:
                assert ranks[w] <= TIER2_MAX_RANK, (
                    f"'{w}' should be in tier 2, got rank {ranks[w]}"
                )

    def test_rerank_deterministic(self, optimizer):
        r1 = optimizer.rerank_by_frequency()
        r2 = optimizer.rerank_by_frequency()
        assert r1 == r2


# === Phase 2: SA Refinement ===

class TestSARefinement:

    def test_sa_improves_or_ties(self, optimizer):
        initial = optimizer.rerank_by_frequency()
        texts = [ARTICLE, BLOG]

        encoder = SequentialEncoder()
        token_lists = [encoder._tokenize(t) for t in texts]
        initial_score = _score(token_lists, initial)

        refined = optimizer.optimize_tier2_sa(
            initial, texts, n_iterations=200, seed=42, verbose=False,
        )
        refined_score = _score(token_lists, refined)
        assert refined_score <= initial_score, (
            f"SA should not worsen: {refined_score} > {initial_score}"
        )

    def test_sa_preserves_word_set(self, optimizer):
        initial = optimizer.rerank_by_frequency()
        refined = optimizer.optimize_tier2_sa(
            initial, [ARTICLE], n_iterations=100, seed=42, verbose=False,
        )
        assert set(refined.keys()) == set(initial.keys())
        assert len(set(refined.values())) == len(refined), "Duplicate ranks"

    def test_sa_deterministic_with_seed(self, optimizer):
        initial = optimizer.rerank_by_frequency()
        r1 = optimizer.optimize_tier2_sa(
            initial, [ARTICLE], n_iterations=100, seed=42, verbose=False,
        )
        r2 = optimizer.optimize_tier2_sa(
            initial, [ARTICLE], n_iterations=100, seed=42, verbose=False,
        )
        assert r1 == r2


# === Round-trip ===

class TestRoundTrip:

    def test_roundtrip_with_optimized_ranks(self, optimizer):
        ranks = optimizer.rerank_by_frequency()

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump(ranks, f)
            tmp_path = f.name

        try:
            d = Dictionary(cache_path=tmp_path)
            enc = SequentialEncoder(dictionary=d)
            dec = SequentialDecoder(dictionary=d)

            for text in [ARTICLE, BLOG, "The quick brown fox jumps over the lazy dog."]:
                blob = enc.encode(text)
                result = dec.decode(blob)
                assert result == text, f"Round-trip failed: {text[:50]}..."
        finally:
            os.unlink(tmp_path)

    def test_two_stage_roundtrip_with_optimized_ranks(self, optimizer):
        ranks = optimizer.rerank_by_frequency()

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump(ranks, f)
            tmp_path = f.name

        try:
            d = Dictionary(cache_path=tmp_path)
            ts = TwoStageCompressor(dictionary=d, method="brotli")

            for text in [ARTICLE, BLOG]:
                compressed = ts.compress(text)
                result = ts.decompress(compressed)
                assert result == text, f"Two-stage round-trip failed"
        finally:
            os.unlink(tmp_path)

    def test_save_and_load(self, optimizer):
        ranks = optimizer.rerank_by_frequency()

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            tmp_path = f.name

        try:
            RankOptimizer.save(ranks, tmp_path)
            d = Dictionary(cache_path=tmp_path)
            assert d.size == len(ranks)
            assert d.word_to_rank("the") is not None
            assert d.rank_to_word(1) is not None
        finally:
            os.unlink(tmp_path)


# === Fast encode path ===

class TestFastEncode:

    def test_fast_encode_matches_encoder(self, optimizer):
        ranks = optimizer.rerank_by_frequency()

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump(ranks, f)
            tmp_path = f.name

        try:
            d = Dictionary(cache_path=tmp_path)
            enc = SequentialEncoder(dictionary=d)

            for text in [ARTICLE, BLOG]:
                expected = enc.encode(text)
                tokens = enc._tokenize(text)
                actual = _fast_encode(tokens, ranks)
                assert actual == expected, (
                    f"Fast encode mismatch for: {text[:40]}..."
                )
        finally:
            os.unlink(tmp_path)
