"""
CAN WE BLANK EVERY WORD AND RECOVER THEM ALL?

If yes: ~500 bytes for 15KB of text = 30:1 compression.
Let's figure out exactly what the decoder needs to reconstruct.
"""

import sys
sys.path.insert(0, '.')

from src.tokenizer.tokenizer import Tokenizer
from src.inverted_index.index_builder import IndexBuilder
from src.wordid.dictionary import Dictionary
from collections import Counter, defaultdict

d = Dictionary()
tok = Tokenizer()

ARTICLE = "The history of science is a story of human curiosity and determination. From the ancient Greeks who first asked questions about the nature of the world to the modern researchers who probe the depths of space and the structure of atoms, people have always been driven to understand the universe around them. In the beginning, science was not separate from philosophy. Thinkers like Aristotle and Plato tried to explain the world through reason alone, without the benefit of experiments or measurements. It was not until the Renaissance that the scientific method began to take shape. Francis Bacon argued that knowledge should be built on observation and experiment, not just logic and tradition. Galileo turned his telescope to the sky and discovered that the earth was not the center of the universe. Newton showed that the same force that makes an apple fall from a tree also keeps the moon in orbit around the earth. These discoveries changed the way people thought about the world and their place in it. The industrial revolution brought science into everyday life. Steam engines, railways, and factories transformed society. Medicine advanced as doctors began to understand the causes of disease. In the twentieth century, science gave us computers, space travel, and the ability to split the atom. Today, science continues to push the boundaries of what we know and what we can do. From artificial intelligence to gene therapy, the frontiers of knowledge are expanding faster than ever before."

text = " ".join((" ".join([ARTICLE] * 10)).split())
doc = tok.tokenize(text)
idx = IndexBuilder().build(doc.tokens)

print("=" * 75)
print("BLANK EVERYTHING: What does the decoder need?")
print("=" * 75)

print("\nDocument: Article x10")
print("  Raw: %d bytes" % len(text.encode("utf-8")))
print("  Tokens: %d" % len(doc.tokens))
print("  Unique words: %d" % len(idx.word_order))
print("  Lines: %d" % doc.line_count)

# If we blank EVERY word, the decoder needs to know:
# 1. WHICH words exist in the document (the vocabulary)
# 2. HOW MANY times each word appears
# 3. WHERE each occurrence goes (the grid position)
# 4. Capitalization per token
# 5. Punctuation per token

print("\n" + "=" * 75)
print("WHAT THE DECODER NEEDS TO RECONSTRUCT")
print("=" * 75)

# 1. VOCABULARY: which words are in the document
print("\n1. VOCABULARY (which unique words)")
# Just a list of word_ids
vocab_bytes = 0
for word in idx.word_order:
    rank = d.word_to_rank(word)
    if rank and rank <= 127:
        vocab_bytes += 1
    elif rank and rank <= 16511:
        vocab_bytes += 2
    elif rank:
        vocab_bytes += 3
    else:
        vocab_bytes += 2 + len(word)
print("   %d unique words = %d bytes of word_ids" % (len(idx.word_order), vocab_bytes))

# 2. OCCURRENCE COUNT per word
print("\n2. OCCURRENCE COUNTS")
# If we store count per word: 1 byte each
count_bytes = len(idx.word_order)  # 1 byte per word
print("   %d words x 1 byte = %d bytes" % (len(idx.word_order), count_bytes))

# OR: derive from document structure (total tokens - sum of other counts = last word's count)
# Still need most counts. Best: 1 byte each.

# 3. POSITIONS: where each occurrence goes
print("\n3. POSITIONS (the expensive part)")
# This is the key question. If EVERYTHING is blanked, ALL positions are gaps.
# There are NO stored words to create the grid. The decoder has NO reference points.
#
# The decoder knows:
#   - total_tokens (from header)
#   - line_word_counts (from metadata)
#   - vocabulary + counts (from above)
#
# But it does NOT know which word goes WHERE.
# It just knows "the document has 29 'the's, 10 'of's, 10 'and's, etc."
#
# To place them correctly, it needs position info for each word.

# OPTION A: Store positions as bit-packed (current approach)
total_pos_bytes = 0
for word in idx.word_order:
    count = len(idx.entries[word])
    total_pos_bytes += (count * 12 + 7) // 8  # 12 bits per position

print("   Option A (bit-packed positions): %d bytes" % total_pos_bytes)
print("   This is still expensive. No savings over current approach.")

# OPTION B: Store the document as a sequential word_id stream
# Each token position = one word_id in sequence
# The word_id at position N tells you which word goes at position N
# This IS the inverted index in reverse

seq_bytes = 0
for token in doc.tokens:
    rank = d.word_to_rank(token.word)
    if rank and rank <= 127:
        seq_bytes += 1
    elif rank and rank <= 16511:
        seq_bytes += 2
    elif rank:
        seq_bytes += 3
    else:
        seq_bytes += 2 + len(token.word)

print("   Option B (sequential word_ids): %d bytes" % seq_bytes)

# OPTION C: Checksum-only recovery (NO position data)
# Can checksums alone tell you where each word goes?
# Answer: NO. Checksums tell you WHICH words are missing, not WHERE they go.
# You need SOME position information.

# OPTION D: The BLANK system with gap detection
# Blank a subset of words. The remaining words create the grid skeleton.
# Gaps = where blanked words go. Assignment by checksum + constraints.
#
# But if we blank ALL words, there is no skeleton. No gaps to detect.
# The whole grid is gaps.

print("\n   Option C (checksum only, no positions): IMPOSSIBLE")
print("   Checksums tell you WHICH words, not WHERE. Need position data.")

print("\n   Option D (partial blank): works but requires some words stored")

# OPTION E: Store positions as a SEQUENCE OF WORD_IDS (not inverted index)
# This is actually Option B but optimized.
# The document IS a sequence of word_ids. Sequential order = position.
# No separate position encoding needed!
#
# BUT: sequential repeats word_ids for every occurrence.
# "the" appearing 29 times = 29 x 1 byte = 29 bytes
# Inverted index: 1 x 1 byte word_id + 29 positions = 1 + 44 = 45 bytes
# Sequential is CHEAPER for single-byte word_ids!

print("\n   Option E (SEQUENTIAL): word_id per token, position is implicit")
print("   Sequential: %d bytes (word_id per token)" % seq_bytes)

# What if we blank common words from the sequence?
# "the" = 1 byte. Appearing 29 times = 29 bytes.
# If blanked: checksum recovers identity, gaps recover position.
# Blank cost: 1 byte constraint marker.
# Savings: 29 - 1 = 28 bytes.
# But we need remaining words to form the skeleton for gap detection.

# OPTIMAL STRATEGY: Sequential stream + blank the most common words
# The sequence provides implicit positions for non-blanked words.
# Blanked positions are gaps in the sequence (0x00 marker or inferred).

print("\n" + "=" * 75)
print("THE WINNING STRATEGY: SEQUENTIAL + AGGRESSIVE BLANKING")
print("=" * 75)

# Calculate optimal blank cutoff
print("\nSequential word_id stream with blanking:")
print("  Each token = 1 word_id (1-3 bytes). Position = stream index. FREE.")
print("  Blank frequent words: replace their slots with a blank marker.")
print("  The blank marker = 0 or 1 bytes (just a gap in the stream).")
print()

# Sort words by frequency x word_id_cost
word_costs = []
for word in idx.word_order:
    count = len(idx.entries[word])
    rank = d.word_to_rank(word)
    if rank and rank <= 127:
        cost_per = 1
    elif rank and rank <= 16511:
        cost_per = 2
    elif rank:
        cost_per = 3
    else:
        cost_per = 2 + len(word)
    total_cost = count * cost_per
    word_costs.append((word, count, cost_per, total_cost, rank))

word_costs.sort(key=lambda x: -x[3])

# Progressive blanking analysis
print("Progressive blanking (sequential stream):")
print("%-20s %5s %5s %7s %7s %7s" % ("Strategy", "Kept", "Blank", "SeqSize", "BlkMeta", "Total"))
print("-" * 70)

base_seq_size = seq_bytes
header = 16
caps = (len(doc.tokens) + 7) // 8
punct = 150

for blank_threshold in [0, 5, 10, 20, 50, 100, 200, 2440]:
    blanked_words = set()
    blanked_tokens = 0
    kept_bytes = 0
    blank_count = 0

    for word, count, cost_per, total_cost, rank in word_costs:
        if count >= blank_threshold and rank is not None:
            blanked_words.add(word)
            blanked_tokens += count
            blank_count += 1
        else:
            kept_bytes += count * cost_per

    # Blank metadata: word_id per blanked word (for checksum recovery)
    blank_meta = sum(
        1 if (r and r <= 127) else 2 if (r and r <= 16511) else 3
        for w, c, cp, tc, r in word_costs
        if w in blanked_words and r is not None
    )
    # POS partition checksums (7 partitions x 4 bytes)
    blank_meta += 28
    # Occurrence count per blanked word
    blank_meta += blank_count

    # Kept tokens in sequential stream (non-blanked)
    # Blanked token slots: need a marker OR just skip
    # If we use 0x00 as blank marker: 1 byte per blanked token
    # OR: if blank words are predictable from POS + checksum, mark slots differently
    # Simplest: blank marker = 1 special byte (0x00)
    blank_slot_cost = blanked_tokens * 1  # 1 byte per blank slot in stream

    # OR: use gap encoding (no blank markers, infer from structure)
    # If we store line_word_counts, the decoder knows total tokens.
    # Non-blank tokens fill slots. Remaining slots = blank.
    # But which SPECIFIC slots? The non-blank tokens' positions are
    # their stream index, which shifts when blanks are removed.
    # This doesn't work without markers.

    # Better: store the stream WITHOUT blanked tokens,
    # plus a blank_positions bitmap (1 bit per token: 0=stored, 1=blank)
    blank_bitmap = (len(doc.tokens) + 7) // 8  # 1 bit per token

    total_with_bitmap = header + kept_bytes + blank_bitmap + blank_meta + caps + punct
    total_with_markers = header + kept_bytes + blank_slot_cost + blank_meta + caps + punct

    label = "blank>=%d" % blank_threshold if blank_threshold > 0 else "no blanks"
    if blank_threshold == 2440:
        label = "blank ALL"

    print("%-20s %5d %5d %7d %7d %7d" % (
        label,
        len(doc.tokens) - blanked_tokens,
        blanked_tokens,
        kept_bytes,
        blank_meta + blank_bitmap,
        total_with_bitmap
    ))

print()
print("=" * 75)
print("THE OPTIMAL APPROACH")
print("=" * 75)

# Find the optimal threshold
best_total = float('inf')
best_thresh = 0
for blank_threshold in range(1, 50):
    blanked_words = set()
    blanked_tokens = 0
    kept_bytes = 0
    blank_count = 0

    for word, count, cost_per, total_cost, rank in word_costs:
        if count >= blank_threshold and rank is not None:
            blanked_words.add(word)
            blanked_tokens += count
            blank_count += 1
        else:
            kept_bytes += count * cost_per

    blank_meta = blank_count * 3 + 28  # rough: 3 bytes per blank + checksums
    blank_bitmap = (len(doc.tokens) + 7) // 8
    total = header + kept_bytes + blank_bitmap + blank_meta + caps + punct

    if total < best_total:
        best_total = total
        best_thresh = blank_threshold

print("\n  Optimal blank threshold: blank words appearing >= %d times" % best_thresh)
print("  Minimum total: %d bytes" % best_total)
print("  Ratio: %.1f:1" % (len(text.encode("utf-8")) / best_total))

import gzip
gz = len(gzip.compress(text.encode("utf-8"), 9))
try:
    import brotli
    br = len(brotli.compress(text.encode("utf-8"), quality=11))
except:
    br = None

print("\n  vs gzip:   %d bytes (%.1f:1)" % (gz, len(text.encode("utf-8")) / gz))
if br:
    print("  vs brotli: %d bytes (%.1f:1)" % (br, len(text.encode("utf-8")) / br))

if best_total < gz:
    print("\n  >>> WE BEAT GZIP! <<<")
if br and best_total < br:
    print("  >>> WE BEAT BROTLI! <<<")
