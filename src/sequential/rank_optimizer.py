"""
AI-Optimized Rank Assignment for Sequential Rank Stream v3.

Two-phase optimization:
  Phase 1 — Brown-only re-ranking: removes Gutenberg contamination,
            promotes modern words to the 2-byte tier (ranks 4-511).
  Phase 2 — Simulated annealing: swaps tier-2 ranks to maximize
            brotli compressibility of the varint byte stream.

Usage:
    from src.sequential.rank_optimizer import RankOptimizer

    opt = RankOptimizer("dictionary_cache.json")
    ranks = opt.optimize(benchmark_texts=["The history of...", ...])
    opt.save(ranks, "optimized_dictionary_cache.json")
"""

import json
import math
import os
import random
from collections import Counter
from typing import Dict, List, Optional, Tuple

import brotli

# Import encoder constants and tokenizer
from .encoder import (
    C_LOWER, C_TITLE, C_UPPER, C_MIXED,
    L_NONE,
    VARIANT_MULT, VERSION,
    _V4_RARE_TRAIL, _TRAIL_STRING,
    SequentialEncoder,
    _LEAD_CHAR,
)

# Tier boundaries (unified = rank * VARIANT_MULT + variant)
# v4 (VARIANT_MULT=16):
#   1-byte: unified < 128 → ranks 1-7   (rank*16 < 128)
#   2-byte: 128 <= unified < 16384 → ranks 8-1023
#   3-byte: unified >= 16384 → ranks 1024+
TIER1_MAX_RANK = 7       # last 1-byte rank
TIER2_MIN_RANK = 8       # first 2-byte rank
TIER2_MAX_RANK = 1023    # last 2-byte rank


def _encode_varint_into(buf: bytearray, value: int):
    """Append LEB128 varint to buffer (in-place, avoids allocation)."""
    while value >= 0x80:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    buf.append(value & 0x7F)


def _fast_encode(tokens: List[Tuple[str, str, int, int, int]],
                 rank_map: Dict[str, int]) -> bytes:
    """
    Fast-path encoder for SA evaluation.

    Takes pre-tokenized text and a rank map, returns the v3 blob.
    Replicates encoder.py logic without constructing Dictionary/Encoder objects.
    """
    main_buf = bytearray()
    extra_buf = bytearray()

    for original, word, caps, lead, trail in tokens:
        rank = rank_map.get(word)

        # v4: rare trailing codes go to extra section
        is_rare_trail = trail in _V4_RARE_TRAIL
        rare_trail_str = ''
        if is_rare_trail:
            rare_trail_str = _TRAIL_STRING[trail]
            trail = 0  # T_NONE

        go_extra = (rank is None) or (caps in (C_UPPER, C_MIXED)) or (lead != L_NONE) or is_rare_trail

        if not go_extra:
            is_cap = 1 if caps == C_TITLE else 0
            variant = (is_cap << 3) | (trail & 0x07)  # v4: 4-bit variant
            unified = rank * VARIANT_MULT + variant
            _encode_varint_into(main_buf, unified)
        else:
            variant = trail & 0x07  # v4: 3-bit trailing
            _encode_varint_into(main_buf, variant)

            lead_char = _LEAD_CHAR.get(lead, '')
            extra_word = lead_char + original + rare_trail_str
            wb = extra_word.encode('utf-8')
            if len(wb) > 255:
                wb = wb[:255]
            extra_buf.append(len(wb))
            extra_buf.extend(wb)

    count = len(tokens)
    buf = bytearray()
    buf.append(VERSION)
    buf.extend(count.to_bytes(3, 'big'))
    buf.extend(main_buf)
    buf.extend(extra_buf)
    return bytes(buf)


def _score(token_lists: List[List[Tuple]], rank_map: Dict[str, int]) -> int:
    """Total brotli-compressed size across all benchmark texts."""
    total = 0
    for tokens in token_lists:
        blob = _fast_encode(tokens, rank_map)
        compressed = brotli.compress(blob, quality=11)
        total += len(compressed)
    return total


class RankOptimizer:
    """Optimize dictionary rank assignment for brotli compression."""

    def __init__(self, dictionary_cache_path: str):
        with open(dictionary_cache_path, 'r', encoding='utf-8') as f:
            self._original_ranks: Dict[str, int] = {
                w.lower().strip(): int(r) for w, r in json.load(f).items()
            }
        self._all_words = set(self._original_ranks.keys())

    def build_brown_frequencies(self) -> Dict[str, int]:
        """Build word frequency map from Brown corpus only (no Gutenberg).

        Also counts bigram frequencies for known phrases (entries with a space),
        so phrases retain tier-2 placement after re-ranking.
        """
        import nltk
        nltk.download('brown', quiet=True)
        from nltk.corpus import brown

        freq: Counter = Counter()
        words_lower = []
        for word in brown.words():
            w = word.lower().strip()
            if w.isalpha() and len(w) >= 1:
                freq[w] += 1
                words_lower.append(w)

        # Count bigram and trigram frequencies for dictionary phrases
        known_phrases = {w for w in self._all_words if ' ' in w}
        if known_phrases:
            known_bigrams = {w for w in known_phrases if w.count(' ') == 1}
            known_trigrams = {w for w in known_phrases if w.count(' ') == 2}
            for i in range(len(words_lower) - 1):
                bigram = words_lower[i] + ' ' + words_lower[i + 1]
                if bigram in known_bigrams:
                    freq[bigram] += 1
                if i + 2 < len(words_lower):
                    trigram = words_lower[i] + ' ' + words_lower[i + 1] + ' ' + words_lower[i + 2]
                    if trigram in known_trigrams:
                        freq[trigram] += 1

        return dict(freq)

    def rerank_by_frequency(self, freq: Optional[Dict[str, int]] = None) -> Dict[str, int]:
        """
        Phase 1: Re-rank all words by Brown corpus frequency.

        Words with frequency data ranked first (descending), then remaining
        words alphabetically. Returns new {word: rank} mapping.
        """
        if freq is None:
            freq = self.build_brown_frequencies()

        freq_words = [(w, freq.get(w, 0)) for w in self._all_words if freq.get(w, 0) > 0]
        no_freq_words = [w for w in self._all_words if freq.get(w, 0) == 0]

        freq_words.sort(key=lambda x: (-x[1], x[0]))
        no_freq_words.sort()

        new_ranks: Dict[str, int] = {}
        rank = 1
        for word, _ in freq_words:
            new_ranks[word] = rank
            rank += 1
        for word in no_freq_words:
            new_ranks[word] = rank
            rank += 1

        return new_ranks

    def optimize_tier2_sa(
        self,
        initial_ranks: Dict[str, int],
        benchmark_texts: List[str],
        n_iterations: int = 5000,
        seed: int = 42,
        verbose: bool = True,
        start_temp: float = 3.0,
        cooling_rate: float = 0.997,
    ) -> Dict[str, int]:
        """
        Phase 2: Simulated annealing refinement of tier-2 ranks (4-511).

        Pre-tokenizes benchmark texts once, then iteratively swaps pairs
        of tier-2 words and evaluates brotli compressed size.
        """
        rng = random.Random(seed)

        # Pre-tokenize all benchmark texts
        encoder = SequentialEncoder()  # default dict, only used for tokenizer
        token_lists = [encoder._tokenize(text) for text in benchmark_texts]

        # Build mutable rank map
        ranks = dict(initial_ranks)

        # Identify tier-2 words (ranks 4-511)
        tier2_words = [w for w, r in ranks.items() if TIER2_MIN_RANK <= r <= TIER2_MAX_RANK]
        if len(tier2_words) < 2:
            return ranks

        # Initial score
        best_score = _score(token_lists, ranks)
        current_score = best_score
        best_ranks = dict(ranks)

        # SA parameters
        temp = start_temp
        cooling = cooling_rate
        min_temp = 0.001
        improvements = 0

        if verbose:
            print(f"SA start: {best_score} bytes ({len(tier2_words)} tier-2 words)")

        for i in range(n_iterations):
            # Pick two random tier-2 words and swap their ranks
            w1, w2 = rng.sample(tier2_words, 2)
            r1, r2 = ranks[w1], ranks[w2]

            # Swap
            ranks[w1], ranks[w2] = r2, r1

            new_score = _score(token_lists, ranks)
            delta = new_score - current_score

            # Accept or reject
            accept = delta < 0 or (
                temp > min_temp and delta / temp < 50
                and rng.random() < math.exp(-delta / temp)
            )
            if accept:
                current_score = new_score
                if new_score < best_score:
                    best_score = new_score
                    best_ranks = dict(ranks)
                    improvements += 1
            else:
                # Revert swap
                ranks[w1], ranks[w2] = r1, r2

            temp = max(temp * cooling, min_temp)

            if verbose and (i + 1) % 1000 == 0:
                print(f"  iter {i+1}/{n_iterations}: best={best_score} "
                      f"current={current_score} temp={temp:.4f} "
                      f"improvements={improvements}")

        if verbose:
            print(f"SA done: {best_score} bytes ({improvements} improvements)")

        return best_ranks

    def optimize(
        self,
        benchmark_texts: Optional[List[str]] = None,
        n_iterations: int = 5000,
        seed: int = 42,
        verbose: bool = True,
        start_temp: float = 3.0,
        cooling_rate: float = 0.997,
    ) -> Dict[str, int]:
        """
        Full pipeline: Phase 1 (Brown re-rank) + Phase 2 (SA refinement).

        Args:
            benchmark_texts: Texts for SA evaluation. If None, skip SA.
            n_iterations: SA iterations (default 5000).
            seed: Random seed for reproducibility.
            verbose: Print progress.
            start_temp: SA initial temperature (default 3.0).
            cooling_rate: SA cooling multiplier per iteration (default 0.997).

        Returns:
            Optimized {word: rank} mapping.
        """
        if verbose:
            print("Phase 1: Brown-only frequency re-ranking...")
        freq = self.build_brown_frequencies()
        ranks = self.rerank_by_frequency(freq)

        if verbose:
            # Report tier changes
            old_t2 = {w for w, r in self._original_ranks.items()
                      if TIER2_MIN_RANK <= r <= TIER2_MAX_RANK}
            new_t2 = {w for w, r in ranks.items()
                      if TIER2_MIN_RANK <= r <= TIER2_MAX_RANK}
            promoted = new_t2 - old_t2
            demoted = old_t2 - new_t2
            print(f"  Promoted to tier 2: {len(promoted)} words")
            print(f"  Demoted from tier 2: {len(demoted)} words")
            if promoted:
                examples = sorted(promoted, key=lambda w: ranks[w])[:10]
                print(f"  Promoted examples: {examples}")
            if demoted:
                examples = sorted(demoted, key=lambda w: self._original_ranks[w])[:10]
                print(f"  Demoted examples: {examples}")

        if benchmark_texts:
            if verbose:
                print("\nPhase 2: Simulated annealing refinement...")
            ranks = self.optimize_tier2_sa(
                ranks, benchmark_texts,
                n_iterations=n_iterations, seed=seed, verbose=verbose,
                start_temp=start_temp, cooling_rate=cooling_rate,
            )

        return ranks

    @staticmethod
    def save(ranks: Dict[str, int], output_path: str):
        """Save optimized dictionary to JSON (same format as dictionary_cache.json)."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ranks, f, ensure_ascii=False)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"Saved {len(ranks)} words to {output_path} ({size_mb:.1f} MB)")
