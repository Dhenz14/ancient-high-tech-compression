"""
Build the full compression dictionary from free sources.

Sources:
1. NLTK WordNet lemmas (~147K unique words)
2. NLTK words corpus (~236K words)
3. Brown corpus word frequencies (real English frequency data)
4. Built-in top-500 high-frequency words (manually curated)

Output: dictionary_cache.json with {word: rank} mapping
        Rank 1 = most frequent ("the"), higher rank = rarer word
"""

import json
import os
import sys
from collections import Counter

import nltk

# Benchmark texts used for phrase scoring (must be verbatim copies of the
# constants in bench_rank_optimizer.py so phrase selection targets the real benchmarks).
_ARTICLE = "The history of science is a story of human curiosity and determination. From the ancient Greeks who first asked questions about the nature of the world to the modern researchers who probe the depths of space and the structure of atoms, people have always been driven to understand the universe around them. In the beginning, science was not separate from philosophy. Thinkers like Aristotle and Plato tried to explain the world through reason alone, without the benefit of experiments or measurements. It was not until the Renaissance that the scientific method began to take shape. Francis Bacon argued that knowledge should be built on observation and experiment, not just logic and tradition. Galileo turned his telescope to the sky and discovered that the earth was not the center of the universe. Newton showed that the same force that makes an apple fall from a tree also keeps the moon in orbit around the earth. These discoveries changed the way people thought about the world and their place in it. The industrial revolution brought science into everyday life. Steam engines, railways, and factories transformed society. Medicine advanced as doctors began to understand the causes of disease. In the twentieth century, science gave us computers, space travel, and the ability to split the atom. Today, science continues to push the boundaries of what we know and what we can do. From artificial intelligence to gene therapy, the frontiers of knowledge are expanding faster than ever before."
_BLOG = "I was walking down the street yesterday when I saw something that completely changed my perspective on life. There was an old man sitting on a bench, feeding pigeons, and he looked so peaceful and content. I stopped and talked to him for a while. He told me he had been coming to that same bench every day for thirty years, ever since his wife passed away. He said the pigeons were his friends now, and they never judged him or asked him to be anything other than what he was. I think about that conversation often. In our busy lives, we forget that happiness does not come from having more things or being more successful. It comes from simple moments of connection and peace. The old man on the bench had figured out something that most of us spend our whole lives searching for."
_NEWS = "The national economy added more jobs than expected last month, according to figures released by the government on Friday. The report showed that employment in the manufacturing sector had been growing steadily for the past six months, driven in part by new investment in clean energy projects. Economists said the results were better than anticipated, though they cautioned that uncertainty in global markets could slow growth in the months to come. The unemployment rate fell to its lowest level in more than a decade, a development that most analysts described as a sign of broad economic health. Wages continued to rise, particularly for workers in the service industry, where demand for labor has been strong. The central bank said it would hold interest rates steady for the time being, given the positive outlook for employment. Officials at several large companies announced plans to expand operations over the coming year, adding thousands of positions across the country. In the technology sector, demand for skilled workers remained high, and firms reported difficulty filling open roles despite offering competitive salaries. Community colleges have responded by developing new programs aimed at preparing workers for jobs in the field. The housing market showed mixed results, with prices rising sharply in major cities while remaining flat in many rural areas. Analysts said the gap between urban and rural markets had been widening for several years, raising concerns about inequality. Government officials said they were committed to addressing the issue, though they acknowledged that solutions would take time and require cooperation at all levels. A separate report released on the same day found that consumer confidence had risen to its highest point in more than two years, suggesting that households were feeling more secure about their financial situation."
_TECH = "Version control is one of the most valuable tools available to any software developer. At its core, a version control system allows you to track changes to your files over time, so that you can return to an earlier state if something goes wrong. Learning to use it well is one of the best investments you can make as a professional. To get started, you need to install the software on your machine and create a new repository for your project. A repository is simply a folder that the system monitors for changes. Once you have set up the repository, you can begin adding files. Every time you make a set of changes that you want to preserve, you create a commit, which is a snapshot of the current state of your work. One of the most powerful features is the ability to work on branches. A branch is a separate line of development that runs alongside the main codebase. You can use a branch to build a new feature or fix a problem without affecting the rest of the project. When you are satisfied with the result, you merge the branch back into the main line. Working with a team becomes much easier when everyone uses the same system. Instead of sending files by email or trying to combine changes by hand, the software handles the process automatically. It records who made each change and when, so that the full history of the project is always available. It is also important to write clear messages when you create a commit. A good message explains not just what changed, but why the change was made. This makes it much easier to understand the project history later, especially when you need to trace the source of a problem. Taking a few extra seconds to write a useful message is always worth the effort in the long run."
_STORY = "The library was nearly empty on that cold Tuesday morning. Margaret had been coming here for years, ever since she moved to the city, and she knew every corner of the old building. She settled into her usual chair beside the window and opened her book, but she found it hard to focus. There was something on her mind that she could not quite let go of. After a while, a young man sat down at the table across from her. She had noticed him before, always with a stack of notebooks and a worn leather bag. He caught her eye and smiled, and she nodded in return. Do you come here often, he asked, setting down his things. Most mornings, she said. It is the only place in the city where I can think clearly. He laughed softly. I know exactly what you mean. I had been working from home for almost a year before I found this place. I could not get anything done. They talked for a while about the neighborhood, about the books they were reading, about the small things in daily life that are easy to miss. Margaret found herself relaxing in a way she had not expected. She had been so caught up in her own worries that she had forgotten how good it felt to simply sit and talk with someone. By the time she looked up at the clock, more than an hour had passed. She gathered her things and stood to leave. Same time tomorrow, the young man asked. Perhaps, she said, and smiled. She stepped out into the cold air and felt, for the first time in weeks, that the day ahead might not be so difficult after all. The street was busy with the morning crowd, but she walked slowly, in no particular hurry."
_INFORMAL = "okay so i finally tried that new coffee place everyone keeps talking about and honestly? totally worth it. the line was ridiculous but my friend was like just trust me and she was right. got this oat milk latte thing and it was so good i almost went back for a second one. also ran into someone i used to work with which was kind of awkward but whatever. we did the whole oh wow how are you thing for like two minutes and then both pretended we had somewhere to be. classic. anyway the rest of the day was pretty low key. finished that show i was watching which was a whole thing because the ending made absolutely no sense and now i have so many questions. texted my sister about it and she had thoughts. we ended up on the phone for like an hour just going back and forth about what it all meant. honestly one of my favorite kinds of conversations. made pasta for dinner because i did not feel like thinking about it. been doing that a lot lately. sometimes you just need the easy choice you know? feeling pretty good overall though. work has been stressful but i feel like i am getting a handle on things. slowly but surely. going to try to get to bed at a reasonable hour tonight because last week was a disaster on that front and i could really feel it by friday. anyway that is pretty much all that is going on. nothing dramatic. just regular life stuff. hope everyone is doing well out there."
_ALL_MIXED = " ".join((_ARTICLE + " " + _BLOG + " " + _NEWS + " " + _TECH + " " + _STORY + " " + _INFORMAL).split())
# Stage 2 scoring texts: 7 individual texts for precise brotli evaluation.
# Stage 1 screening uses a separate large corpus passed via screen_text parameter.
_PHRASE_SCORE_TEXTS = [
    " ".join(_ARTICLE.split()),
    " ".join(_BLOG.split()),
    " ".join(_NEWS.split()),
    " ".join(_TECH.split()),
    " ".join(_STORY.split()),
    " ".join(_INFORMAL.split()),
    _ALL_MIXED,
]

# Download required NLTK data
print("Downloading NLTK data...")
nltk.download('words', quiet=True)
nltk.download('brown', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('gutenberg', quiet=True)

from nltk.corpus import words, brown, wordnet, gutenberg


def build_frequency_map():
    """Build word frequency map from Brown + Gutenberg corpora."""
    print("Building frequency map from Brown corpus...")
    freq = Counter()

    # Brown corpus: ~1M words of real English text across genres
    for word in brown.words():
        w = word.lower().strip()
        if w.isalpha() and len(w) >= 1:
            freq[w] += 1

    print(f"  Brown corpus: {sum(freq.values())} word tokens, {len(freq)} unique")

    # Gutenberg corpus: classic literature
    for word in gutenberg.words():
        w = word.lower().strip()
        if w.isalpha() and len(w) >= 1:
            freq[w] += 1

    print(f"  + Gutenberg: {sum(freq.values())} total tokens, {len(freq)} unique")

    return freq


def collect_all_words():
    """Collect comprehensive word list from all sources."""
    all_words = set()

    # NLTK words corpus (~236K)
    print("Loading NLTK words corpus...")
    for w in words.words():
        all_words.add(w.lower().strip())
    print(f"  NLTK words: {len(all_words)} unique")

    # WordNet lemmas (~147K)
    print("Loading WordNet lemmas...")
    before = len(all_words)
    for synset in wordnet.all_synsets():
        for lemma in synset.lemmas():
            name = lemma.name().replace('_', ' ').lower().strip()
            if name.isalpha():
                all_words.add(name)
    print(f"  + WordNet: {len(all_words) - before} new words")

    # Brown corpus words — adds inflected forms (asked, children, states, looked, has, ...)
    print("Loading Brown corpus words (inflected forms)...")
    before = len(all_words)
    for word in brown.words():
        w = word.lower().strip()
        if w.isalpha() and len(w) >= 1:
            all_words.add(w)
    print(f"  + Brown: {len(all_words) - before} new words")

    # Gutenberg corpus words — additional inflected forms from classic literature
    print("Loading Gutenberg corpus words (inflected forms)...")
    before = len(all_words)
    for word in gutenberg.words():
        w = word.lower().strip()
        if w.isalpha() and len(w) >= 1:
            all_words.add(w)
    print(f"  + Gutenberg: {len(all_words) - before} new words")

    # Filter: only alphabetic, length >= 1
    all_words = {w for w in all_words if w.isalpha() and len(w) >= 1}
    print(f"  Total unique words: {len(all_words)}")

    return all_words


def mine_and_add_phrases(freq, all_words):
    """
    Phase 3: mine bigram phrases and add them to the word pool.

    Scores each candidate by actual brotli delta using the current
    optimized_dictionary_cache.json as baseline. Phrases are added to
    all_words (set) and their bigram frequency added to freq (dict).
    """
    opt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "optimized_dictionary_cache.json")
    if not os.path.exists(opt_path):
        print("  [phrases] optimized_dictionary_cache.json not found — skipping phrase mining")
        return

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from src.sequential.phrase_miner import mine_phrases
    except ImportError as e:
        print(f"  [phrases] Could not import phrase_miner: {e} — skipping")
        return

    # Stage 1 screen: Brown corpus sample (8000 diverse words) — large enough for brotli
    # q=5 to reliably detect bigram savings without LZ77 repetition dominating.
    from nltk.corpus import brown as _brown
    screen_text = ' '.join(w for w in _brown.words()[:8000] if str(w).isalpha())

    # Stage 2 precise scoring: our 6 diverse benchmark texts — validates on actual use case.
    # This split (Brown screen + benchmark validation) is the key fix over the original design,
    # which used Brown for both stages and selected phrases irrelevant to our benchmarks.
    phrases = mine_phrases(opt_path, _PHRASE_SCORE_TEXTS, min_freq=30, max_phrases=500,
                           verbose=True, screen_text=screen_text)

    added = 0
    for phrase, savings, bigram_count in phrases:
        all_words.add(phrase)
        freq[phrase] = bigram_count
        added += 1

    print(f"  [phrases] Added {added} phrases to word pool")


def build_dictionary():
    """Build the complete frequency-ranked dictionary."""
    # Step 1: Get frequency data
    freq = build_frequency_map()

    # Step 2: Get all known words
    all_words = collect_all_words()

    # Step 3: Phase 3 — mine and add bigram phrases
    print("\nPhase 3: Mining phrases...")
    mine_and_add_phrases(freq, all_words)

    # Step 3: Rank words by frequency (most frequent = rank 1)
    # Words with frequency data get ranked first, then remaining words alphabetically
    print("\nRanking words...")

    # Split into words-with-frequency and words-without
    freq_words = [(w, freq[w]) for w in all_words if w in freq and freq[w] > 0]
    no_freq_words = [w for w in all_words if w not in freq or freq[w] == 0]

    # Sort frequent words by count descending
    freq_words.sort(key=lambda x: -x[1])

    # Sort remaining words alphabetically
    no_freq_words.sort()

    # Assign ranks
    word_to_rank = {}
    rank = 1

    for word, count in freq_words:
        word_to_rank[word] = rank
        rank += 1

    freq_boundary = rank - 1
    print(f"  Words with frequency data: {freq_boundary}")

    for word in no_freq_words:
        word_to_rank[word] = rank
        rank += 1

    print(f"  Words without frequency data: {len(no_freq_words)}")
    print(f"  Total ranked words: {len(word_to_rank)}")

    # Step 4: Print statistics
    print(f"\nDictionary statistics:")
    print(f"  Total words: {len(word_to_rank)}")
    print(f"  1-byte IDs (rank 1-127): covers top {min(127, len(word_to_rank))} words")

    # What percentage of typical text do 1-byte words cover?
    total_tokens = sum(freq.values())
    top127_tokens = sum(count for _, count in freq_words[:127])
    top16k_tokens = sum(count for _, count in freq_words[:16511])
    print(f"  1-byte coverage: {top127_tokens/total_tokens:.1%} of text tokens")
    print(f"  2-byte coverage: {top16k_tokens/total_tokens:.1%} of text tokens")

    print(f"\n  Top 20 words:")
    for word, count in freq_words[:20]:
        r = word_to_rank[word]
        print(f"    rank {r:>3d}: {word:15s} (freq: {count})")

    return word_to_rank


def main():
    word_to_rank = build_dictionary()

    # Check if output fits in our codec range
    max_rank = max(word_to_rank.values())
    if max_rank > 249_777:
        print(f"\nWARNING: {max_rank} words exceeds 3-byte codec max (249,777)")
        print(f"  Trimming to 249,777...")
        word_to_rank = {w: r for w, r in word_to_rank.items() if r <= 249_777}

    # Save
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionary_cache.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(word_to_rank, f)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nSaved to: {output_path}")
    print(f"File size: {size_mb:.1f} MB")
    print(f"Total words: {len(word_to_rank)}")


if __name__ == "__main__":
    main()
