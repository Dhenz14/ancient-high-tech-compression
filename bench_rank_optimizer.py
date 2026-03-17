"""
Benchmark: Optimized rank assignment vs original frequency ranking.

Runs the full optimization pipeline (Brown re-rank + SA) and compares
compression ratios against the original dictionary and raw brotli.
"""

import os
import sys
sys.path.insert(0, '.')

import brotli

from src.sequential.rank_optimizer import RankOptimizer
from src.sequential.two_stage import TwoStageCompressor
from src.wordid.dictionary import Dictionary

DICT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionary_cache.json")
OPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "optimized_dictionary_cache.json")

ARTICLE = "The history of science is a story of human curiosity and determination. From the ancient Greeks who first asked questions about the nature of the world to the modern researchers who probe the depths of space and the structure of atoms, people have always been driven to understand the universe around them. In the beginning, science was not separate from philosophy. Thinkers like Aristotle and Plato tried to explain the world through reason alone, without the benefit of experiments or measurements. It was not until the Renaissance that the scientific method began to take shape. Francis Bacon argued that knowledge should be built on observation and experiment, not just logic and tradition. Galileo turned his telescope to the sky and discovered that the earth was not the center of the universe. Newton showed that the same force that makes an apple fall from a tree also keeps the moon in orbit around the earth. These discoveries changed the way people thought about the world and their place in it. The industrial revolution brought science into everyday life. Steam engines, railways, and factories transformed society. Medicine advanced as doctors began to understand the causes of disease. In the twentieth century, science gave us computers, space travel, and the ability to split the atom. Today, science continues to push the boundaries of what we know and what we can do. From artificial intelligence to gene therapy, the frontiers of knowledge are expanding faster than ever before."

BLOG = "I was walking down the street yesterday when I saw something that completely changed my perspective on life. There was an old man sitting on a bench, feeding pigeons, and he looked so peaceful and content. I stopped and talked to him for a while. He told me he had been coming to that same bench every day for thirty years, ever since his wife passed away. He said the pigeons were his friends now, and they never judged him or asked him to be anything other than what he was. I think about that conversation often. In our busy lives, we forget that happiness does not come from having more things or being more successful. It comes from simple moments of connection and peace. The old man on the bench had figured out something that most of us spend our whole lives searching for."

texts = {
    "Article x1": " ".join(ARTICLE.split()),
    "Article x2": " ".join((" ".join([ARTICLE]*2)).split()),
    "Article x5": " ".join((" ".join([ARTICLE]*5)).split()),
    "Article x10": " ".join((" ".join([ARTICLE]*10)).split()),
    "Blog post": " ".join(BLOG.split()),
    "Mixed": " ".join((ARTICLE + " " + BLOG).split()),
}

SA_TEXTS = [
    " ".join(ARTICLE.split()),
    " ".join(BLOG.split()),
    " ".join((ARTICLE + " " + BLOG).split()),
]


def main():
    # === Step 1: Run optimizer ===
    print("=" * 100)
    print("RANK OPTIMIZER: Brown Re-rank + Simulated Annealing")
    print("=" * 100)
    print()

    opt = RankOptimizer(DICT_PATH)
    optimized_ranks = opt.optimize(
        benchmark_texts=SA_TEXTS,
        n_iterations=5000,
        seed=42,
        verbose=True,
    )
    opt.save(optimized_ranks, OPT_PATH)
    print()

    # === Step 2: Load both dictionaries ===
    d_orig = Dictionary(cache_path=DICT_PATH)
    d_opt = Dictionary(cache_path=OPT_PATH)

    # === Step 3: Verify round-trips ===
    print("Round-trip verification:")
    ts_orig = TwoStageCompressor(dictionary=d_orig, method="brotli")
    ts_opt = TwoStageCompressor(dictionary=d_opt, method="brotli")
    all_ok = True
    for name, text in texts.items():
        for label, ts in [("orig", ts_orig), ("opt", ts_opt)]:
            compressed = ts.compress(text)
            result = ts.decompress(compressed)
            ok = result == text
            if not ok:
                all_ok = False
                print(f"  FAIL {name} ({label})")
            else:
                print(f"  {name} ({label}): PASS")

    if not all_ok:
        print("\nFIX ROUND-TRIP ERRORS BEFORE BENCHMARKING")
        sys.exit(1)

    # === Step 4: Benchmark ===
    print()
    print("=" * 100)
    print("COMPRESSION COMPARISON")
    print("=" * 100)
    print()

    header = "%-14s %5s | %6s | %6s %6s | %7s %7s | %s" % (
        "Text", "Raw",
        "brotli",
        "Orig", "Opt",
        "vs Orig", "vs Brot",
        "VERDICT"
    )
    print(header)
    print("-" * 100)

    total_orig = 0
    total_opt = 0
    total_brotli = 0

    for name, text in texts.items():
        raw_bytes = text.encode("utf-8")
        raw = len(raw_bytes)

        br_raw = len(brotli.compress(raw_bytes, quality=11))

        orig_blob = ts_orig.compress(text)
        orig_size = len(orig_blob)

        opt_blob = ts_opt.compress(text)
        opt_size = len(opt_blob)

        total_orig += orig_size
        total_opt += opt_size
        total_brotli += br_raw

        delta_orig = orig_size - opt_size
        pct_orig = (delta_orig / orig_size * 100) if orig_size > 0 else 0

        delta_brotli = br_raw - opt_size
        pct_brotli = (delta_brotli / br_raw * 100) if br_raw > 0 else 0

        if opt_size < br_raw:
            verdict = ">>> BEATS BROTLI (%.1f:1 vs %.1f:1) <<<" % (raw/opt_size, raw/br_raw)
        elif opt_size < br_raw * 1.05:
            verdict = "CLOSE to brotli"
        else:
            verdict = "behind brotli"

        print("%-14s %5d | %6d | %6d %6d | %+5d %s | %+5d %s | %s" % (
            name, raw,
            br_raw,
            orig_size, opt_size,
            -delta_orig, ("(%.1f%%)" % pct_orig),
            -delta_brotli, ("(%.1f%%)" % pct_brotli) if delta_brotli != 0 else "",
            verdict
        ))

    print("-" * 100)

    total_delta = total_orig - total_opt
    total_pct = (total_delta / total_orig * 100) if total_orig > 0 else 0
    print(f"\nTOTAL: orig={total_orig} opt={total_opt} "
          f"saved={total_delta} bytes ({total_pct:.1f}% improvement)")

    brotli_delta = total_brotli - total_opt
    brotli_pct = (brotli_delta / total_brotli * 100) if total_brotli > 0 else 0
    print(f"vs raw brotli: {total_brotli} -> {total_opt} "
          f"({'+' if brotli_delta > 0 else ''}{brotli_pct:.1f}%)")


if __name__ == "__main__":
    main()
