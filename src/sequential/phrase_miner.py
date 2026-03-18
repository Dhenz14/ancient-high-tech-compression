"""
Phase 3 Phrase Miner — discover and score common bigrams for dictionary inclusion.

Two-stage scoring:
  Stage 1: theoretical pre-filter (component byte costs) + quick brotli screen
            (quality=5, first text only) — evaluates ~1000 candidates in ~10s
  Stage 2: precise scoring (quality=11, all texts) — evaluates top 200 in ~30s

Returns phrases ranked by net brotli savings. Only phrases that actually reduce
compressed size after accounting for their rank slot cost are returned.

Key insight: phrases where both component words are already 1-byte ranks (1-3)
save zero bytes — "of the" (rank 3 + rank 1 = 2 bytes) would cost 2 bytes as
a phrase too. Only 2-byte+2-byte and 2-byte+1-byte combos give real savings.
"""

import bisect
import json
from collections import Counter
from typing import Dict, List, Tuple

import brotli
import nltk

from .encoder import (
    SequentialEncoder,
    C_LOWER, C_TITLE,
    L_NONE, T_NONE,
    VARIANT_MULT,
)
from .rank_optimizer import _fast_encode, _encode_varint_into  # noqa: F401


def _bytes_for_rank(rank: int) -> int:
    """Number of LEB128 varint bytes for a given rank (variant=0 = worst case)."""
    unified = rank * VARIANT_MULT
    if unified < 0x80:
        return 1
    elif unified < 0x4000:
        return 2
    elif unified < 0x200000:
        return 3
    return 4


def _merge_tokens_for_phrase(
    token_lists: List[List[Tuple]],
    w1: str,
    w2: str,
) -> List[List[Tuple]]:
    """
    Merge adjacent token pairs (w1, w2) into single phrase tokens.

    Merge conditions (all must hold):
      - first token has no trailing punct (T_NONE)
      - second token has no leading punct (L_NONE)
      - caps: first is C_LOWER or C_TITLE, second is C_LOWER
        (catches lowercase "in a" and sentence-start "In a")
    """
    phrase = w1 + ' ' + w2
    result = []
    for tokens in token_lists:
        merged = []
        i = 0
        while i < len(tokens):
            if i + 1 < len(tokens):
                orig_i, word_i, caps_i, lead_i, trail_i = tokens[i]
                orig_j, word_j, caps_j, lead_j, trail_j = tokens[i + 1]
                if (word_i == w1 and word_j == w2
                        and trail_i == T_NONE and lead_j == L_NONE
                        and caps_i in (C_LOWER, C_TITLE) and caps_j == C_LOWER):
                    merged.append((
                        orig_i + ' ' + orig_j,
                        phrase,
                        caps_i,       # C_LOWER or C_TITLE preserved
                        lead_i,       # leading punct from first token
                        trail_j,      # trailing punct from second token
                    ))
                    i += 2
                    continue
            merged.append(tokens[i])
            i += 1
        result.append(merged)
    return result


def _score_quick(token_lists: List[List[Tuple]], rank_map: Dict[str, int]) -> int:
    """Fast scoring: brotli quality=5 on first text only."""
    blob = _fast_encode(token_lists[0], rank_map)
    return len(brotli.compress(blob, quality=5))


def _score_full(token_lists: List[List[Tuple]], rank_map: Dict[str, int]) -> int:
    """Full scoring: brotli quality=11 on all texts."""
    total = 0
    for tokens in token_lists:
        blob = _fast_encode(tokens, rank_map)
        total += len(brotli.compress(blob, quality=11))
    return total


def mine_phrases(
    dictionary_cache_path: str,
    benchmark_texts: List[str],
    min_freq: int = 30,
    max_phrases: int = 500,
    verbose: bool = True,
) -> List[Tuple[str, int, int]]:
    """
    Mine and score bigram phrases for dictionary inclusion.

    Args:
        dictionary_cache_path: Path to current optimized dictionary JSON.
        benchmark_texts: Texts used for brotli scoring (typically Article, Blog, Mixed).
        min_freq: Minimum Brown corpus bigram frequency to consider.
        max_phrases: Maximum number of phrases to return.
        verbose: Print progress and results.

    Returns:
        List of (phrase, net_brotli_savings, bigram_count) sorted by savings descending.
        Only phrases with positive net savings are included.
        bigram_count is the raw Brown corpus frequency — use for dictionary ranking.
    """
    nltk.download('brown', quiet=True)
    from nltk.corpus import brown

    # Load current rank map
    with open(dictionary_cache_path, 'r', encoding='utf-8') as f:
        rank_map: Dict[str, int] = {
            w.lower().strip(): int(r) for w, r in json.load(f).items()
        }

    if verbose:
        print(f"Dictionary: {len(rank_map):,} words loaded")

    # Build Brown single-word and bigram frequencies in one pass
    if verbose:
        print("Mining Brown corpus bigrams...")

    words_lower = [w.lower() for w in brown.words() if w.isalpha()]
    word_freq: Counter = Counter(words_lower)
    bigram_freq: Counter = Counter()
    for i in range(len(words_lower) - 1):
        w1, w2 = words_lower[i], words_lower[i + 1]
        if w1 in rank_map and w2 in rank_map:
            bigram_freq[(w1, w2)] += 1

    if verbose:
        print(f"  {len(bigram_freq):,} bigram types with both words in dictionary")

    # Estimate provisional phrase rank based on bigram frequency.
    # A phrase with bigram_count X slots below all single words with freq > X.
    # Cap to 2-byte tier (4-511) since that's where meaningful savings occur.
    sorted_freqs_desc = sorted(word_freq.values(), reverse=True)

    def estimate_rank(phrase_freq: int) -> int:
        pos = bisect.bisect_left([-f for f in sorted_freqs_desc], -phrase_freq)
        return max(4, min(511, pos + 1))

    # Pre-filter: only candidates where cost(w1) + cost(w2) > cost(phrase)
    # This eliminates "of the" (1+1=2 → phrase costs 2 → zero savings)
    candidates = []
    for (w1, w2), cnt in bigram_freq.items():
        if cnt < min_freq:
            continue
        r1 = rank_map[w1]
        r2 = rank_map[w2]
        cost_sep = _bytes_for_rank(r1) + _bytes_for_rank(r2)
        phrase_rank = estimate_rank(cnt)
        cost_phrase = _bytes_for_rank(phrase_rank)
        if cost_sep > cost_phrase:
            savings_per_occ = cost_sep - cost_phrase
            candidates.append((w1, w2, cnt, savings_per_occ))

    # Sort by expected total savings (frequency × savings_per_occurrence)
    candidates.sort(key=lambda x: -(x[2] * x[3]))

    if verbose:
        print(f"  {len(candidates):,} candidates pass theoretical filter")
        print(f"\n  Top 15 by expected savings:")
        for w1, w2, cnt, spo in candidates[:15]:
            r1, r2 = rank_map[w1], rank_map[w2]
            pr = estimate_rank(cnt)
            print(f"    '{w1} {w2}': freq={cnt:,}  "
                  f"sep={_bytes_for_rank(r1)}+{_bytes_for_rank(r2)}B → "
                  f"phrase@rank{pr}={_bytes_for_rank(pr)}B  "
                  f"saves {spo}B/occ  expected={cnt * spo:,}B total")

    # Pre-tokenize benchmark texts once
    encoder = SequentialEncoder()
    token_lists = [encoder._tokenize(text) for text in benchmark_texts]

    # ── Stage 1: Quick screen ──────────────────────────────────────────────
    n_screen = min(len(candidates), 1000)
    if verbose:
        print(f"\nStage 1: quick screen {n_screen} candidates (brotli q=5, text[0])...")

    base_quick = _score_quick(token_lists, rank_map)
    quick_scored = []

    for w1, w2, cnt, _ in candidates[:n_screen]:
        phrase = w1 + ' ' + w2
        phrase_rank = estimate_rank(cnt)
        rank_map[phrase] = phrase_rank
        merged = _merge_tokens_for_phrase(token_lists, w1, w2)
        score = _score_quick(merged, rank_map)
        del rank_map[phrase]
        quick_scored.append((w1, w2, cnt, base_quick - score))

    quick_scored.sort(key=lambda x: -x[3])
    top200 = [(w1, w2, cnt) for w1, w2, cnt, s in quick_scored if s > 0][:200]

    if verbose:
        print(f"  {len(top200)} candidates passed quick screen (positive q=5 savings)")

    if not top200:
        if verbose:
            print("  No candidates passed quick screen — no phrases to add.")
        return []

    # ── Stage 2: Precise scoring ───────────────────────────────────────────
    if verbose:
        print(f"Stage 2: precise scoring {len(top200)} candidates (brotli q=11, all texts)...")

    base_full = _score_full(token_lists, rank_map)
    full_scored = []

    for w1, w2, cnt in top200:
        phrase = w1 + ' ' + w2
        phrase_rank = estimate_rank(cnt)
        rank_map[phrase] = phrase_rank
        merged = _merge_tokens_for_phrase(token_lists, w1, w2)
        score = _score_full(merged, rank_map)
        del rank_map[phrase]
        full_scored.append((phrase, base_full - score, cnt))

    full_scored.sort(key=lambda x: -x[1])

    if verbose:
        positives = [(p, s, c) for p, s, c in full_scored if s > 0]
        print(f"\n  Results (brotli q=11, all {len(benchmark_texts)} texts):")
        print(f"  Base compressed: {base_full} bytes")
        print(f"  Phrases with positive savings: {len(positives)}")
        print(f"\n  Top 25 by actual brotli savings:")
        for phrase, savings, cnt in full_scored[:25]:
            marker = "✓" if savings > 0 else "✗"
            print(f"  {marker} '{phrase}': saves {savings:+d} bytes (freq={cnt:,})")

    result = [(phrase, savings, cnt)
              for phrase, savings, cnt in full_scored
              if savings > 0]
    return result[:max_phrases]
