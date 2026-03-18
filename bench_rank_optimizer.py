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

NEWS = "The national economy added more jobs than expected last month, according to figures released by the government on Friday. The report showed that employment in the manufacturing sector had been growing steadily for the past six months, driven in part by new investment in clean energy projects. Economists said the results were better than anticipated, though they cautioned that uncertainty in global markets could slow growth in the months to come. The unemployment rate fell to its lowest level in more than a decade, a development that most analysts described as a sign of broad economic health. Wages continued to rise, particularly for workers in the service industry, where demand for labor has been strong. The central bank said it would hold interest rates steady for the time being, given the positive outlook for employment. Officials at several large companies announced plans to expand operations over the coming year, adding thousands of positions across the country. In the technology sector, demand for skilled workers remained high, and firms reported difficulty filling open roles despite offering competitive salaries. Community colleges have responded by developing new programs aimed at preparing workers for jobs in the field. The housing market showed mixed results, with prices rising sharply in major cities while remaining flat in many rural areas. Analysts said the gap between urban and rural markets had been widening for several years, raising concerns about inequality. Government officials said they were committed to addressing the issue, though they acknowledged that solutions would take time and require cooperation at all levels. A separate report released on the same day found that consumer confidence had risen to its highest point in more than two years, suggesting that households were feeling more secure about their financial situation."

TECH = "Version control is one of the most valuable tools available to any software developer. At its core, a version control system allows you to track changes to your files over time, so that you can return to an earlier state if something goes wrong. Learning to use it well is one of the best investments you can make as a professional. To get started, you need to install the software on your machine and create a new repository for your project. A repository is simply a folder that the system monitors for changes. Once you have set up the repository, you can begin adding files. Every time you make a set of changes that you want to preserve, you create a commit, which is a snapshot of the current state of your work. One of the most powerful features is the ability to work on branches. A branch is a separate line of development that runs alongside the main codebase. You can use a branch to build a new feature or fix a problem without affecting the rest of the project. When you are satisfied with the result, you merge the branch back into the main line. Working with a team becomes much easier when everyone uses the same system. Instead of sending files by email or trying to combine changes by hand, the software handles the process automatically. It records who made each change and when, so that the full history of the project is always available. It is also important to write clear messages when you create a commit. A good message explains not just what changed, but why the change was made. This makes it much easier to understand the project history later, especially when you need to trace the source of a problem. Taking a few extra seconds to write a useful message is always worth the effort in the long run."

STORY = "The library was nearly empty on that cold Tuesday morning. Margaret had been coming here for years, ever since she moved to the city, and she knew every corner of the old building. She settled into her usual chair beside the window and opened her book, but she found it hard to focus. There was something on her mind that she could not quite let go of. After a while, a young man sat down at the table across from her. She had noticed him before, always with a stack of notebooks and a worn leather bag. He caught her eye and smiled, and she nodded in return. Do you come here often, he asked, setting down his things. Most mornings, she said. It is the only place in the city where I can think clearly. He laughed softly. I know exactly what you mean. I had been working from home for almost a year before I found this place. I could not get anything done. They talked for a while about the neighborhood, about the books they were reading, about the small things in daily life that are easy to miss. Margaret found herself relaxing in a way she had not expected. She had been so caught up in her own worries that she had forgotten how good it felt to simply sit and talk with someone. By the time she looked up at the clock, more than an hour had passed. She gathered her things and stood to leave. Same time tomorrow, the young man asked. Perhaps, she said, and smiled. She stepped out into the cold air and felt, for the first time in weeks, that the day ahead might not be so difficult after all. The street was busy with the morning crowd, but she walked slowly, in no particular hurry."

INFORMAL = "okay so i finally tried that new coffee place everyone keeps talking about and honestly? totally worth it. the line was ridiculous but my friend was like just trust me and she was right. got this oat milk latte thing and it was so good i almost went back for a second one. also ran into someone i used to work with which was kind of awkward but whatever. we did the whole oh wow how are you thing for like two minutes and then both pretended we had somewhere to be. classic. anyway the rest of the day was pretty low key. finished that show i was watching which was a whole thing because the ending made absolutely no sense and now i have so many questions. texted my sister about it and she had thoughts. we ended up on the phone for like an hour just going back and forth about what it all meant. honestly one of my favorite kinds of conversations. made pasta for dinner because i did not feel like thinking about it. been doing that a lot lately. sometimes you just need the easy choice you know? feeling pretty good overall though. work has been stressful but i feel like i am getting a handle on things. slowly but surely. going to try to get to bed at a reasonable hour tonight because last week was a disaster on that front and i could really feel it by friday. anyway that is pretty much all that is going on. nothing dramatic. just regular life stuff. hope everyone is doing well out there."

_ALL = " ".join((ARTICLE + " " + BLOG + " " + NEWS + " " + TECH + " " + STORY + " " + INFORMAL).split())

texts = {
    "Article x1":  " ".join(ARTICLE.split()),
    "Article x2":  " ".join((" ".join([ARTICLE]*2)).split()),
    "Article x5":  " ".join((" ".join([ARTICLE]*5)).split()),
    "Article x10": " ".join((" ".join([ARTICLE]*10)).split()),
    "Blog post":   " ".join(BLOG.split()),
    "News":        " ".join(NEWS.split()),
    "Tech doc":    " ".join(TECH.split()),
    "Story":       " ".join(STORY.split()),
    "Informal":    " ".join(INFORMAL.split()),
    "Mixed (2)":   " ".join((ARTICLE + " " + BLOG).split()),
    "All mixed":   _ALL,
}

# Phase 2 SA training: 6 diverse formal texts (sweet spot — INFORMAL excluded here
# because it causes Phase 2 to trade formal-text gains for informal-text gains).
SA_TEXTS = [
    " ".join(NEWS.split()),
    " ".join(ARTICLE.split()),
    " ".join(BLOG.split()),
    " ".join(TECH.split()),
    " ".join(STORY.split()),
    _ALL,
]

# Phase 3 cross-tier SA training: all 7 texts including INFORMAL.
# Phase 3 extends the SA pool to include tier-3 words appearing in these texts,
# letting the optimizer restore colloquial words demoted by Phase 1 back to tier-2.
SA_TEXTS_7 = SA_TEXTS + [" ".join(INFORMAL.split())]


def main():
    # === Step 1: Run optimizer ===
    print("=" * 100)
    print("RANK OPTIMIZER: Brown Re-rank + Simulated Annealing")
    print("=" * 100)
    print()

    opt = RankOptimizer(DICT_PATH)

    # Phase 1 + 2: Brown re-rank then tier-2-only SA on 6 formal texts
    optimized_ranks = opt.optimize(
        benchmark_texts=SA_TEXTS,
        n_iterations=20000,
        seed=42,
        verbose=True,
        start_temp=3.0,
        cooling_rate=0.9993,
    )

    # Phase 3: Cross-tier SA — expands pool to tier-3 words appearing in training
    # texts, fixing genre regressions (e.g. colloquial words demoted by Phase 1).
    print("\nPhase 3: Cross-tier SA refinement (7 texts incl. Informal)...")
    optimized_ranks = opt.optimize_crosstier_sa(
        optimized_ranks,
        benchmark_texts=SA_TEXTS_7,
        n_iterations=5000,
        seed=42,
        verbose=True,
        start_temp=1.0,
        cooling_rate=0.999,
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
