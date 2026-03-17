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


def build_dictionary():
    """Build the complete frequency-ranked dictionary."""
    # Step 1: Get frequency data
    freq = build_frequency_map()

    # Step 2: Get all known words
    all_words = collect_all_words()

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
