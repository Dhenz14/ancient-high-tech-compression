"""
Honest comparison: us vs the world's best compressors.
What do we need to beat them?
"""
import gzip
import zlib
import sys
sys.path.insert(0, '.')

from src.pipeline.compressor import Compressor
from src.pipeline.decompressor import Decompressor
from src.wordid.dictionary import Dictionary
from src.tokenizer.tokenizer import Tokenizer
from src.inverted_index.index_builder import IndexBuilder

d = Dictionary()

ARTICLE = "The history of science is a story of human curiosity and determination. From the ancient Greeks who first asked questions about the nature of the world to the modern researchers who probe the depths of space and the structure of atoms, people have always been driven to understand the universe around them. In the beginning, science was not separate from philosophy. Thinkers like Aristotle and Plato tried to explain the world through reason alone, without the benefit of experiments or measurements. It was not until the Renaissance that the scientific method began to take shape. Francis Bacon argued that knowledge should be built on observation and experiment, not just logic and tradition. Galileo turned his telescope to the sky and discovered that the earth was not the center of the universe. Newton showed that the same force that makes an apple fall from a tree also keeps the moon in orbit around the earth. These discoveries changed the way people thought about the world and their place in it. The industrial revolution brought science into everyday life. Steam engines, railways, and factories transformed society. Medicine advanced as doctors began to understand the causes of disease. In the twentieth century, science gave us computers, space travel, and the ability to split the atom. Today, science continues to push the boundaries of what we know and what we can do. From artificial intelligence to gene therapy, the frontiers of knowledge are expanding faster than ever before."

print("=" * 75)
print("HONEST COMPARISON: Us vs World's Best Compressors")
print("=" * 75)

for mult in [1, 2, 5, 10]:
    text = " ".join((" ".join([ARTICLE] * mult)).split())
    raw = len(text.encode("utf-8"))

    c = Compressor(dictionary=d)
    ours = len(c.compress(text))

    gz = len(gzip.compress(text.encode("utf-8"), 9))
    zl = len(zlib.compress(text.encode("utf-8"), 9))

    try:
        import brotli
        br = len(brotli.compress(text.encode("utf-8"), quality=11))
    except ImportError:
        br = None

    try:
        import zstandard
        zstd = len(zstandard.ZstdCompressor(level=22).compress(text.encode("utf-8")))
    except ImportError:
        zstd = None

    name = "Article x%d" % mult
    print("\n%s (raw: %d bytes)" % (name, raw))
    print("  %-12s %6d bytes  %5.1f:1  %5.1f%%" % ("Ours", ours, raw/ours, ours/raw*100))
    print("  %-12s %6d bytes  %5.1f:1  %5.1f%%" % ("gzip-9", gz, raw/gz, gz/raw*100))
    print("  %-12s %6d bytes  %5.1f:1  %5.1f%%" % ("zlib-9", zl, raw/zl, zl/raw*100))
    if br:
        print("  %-12s %6d bytes  %5.1f:1  %5.1f%%" % ("brotli-11", br, raw/br, br/raw*100))
    if zstd:
        print("  %-12s %6d bytes  %5.1f:1  %5.1f%%" % ("zstd-22", zstd, raw/zstd, zstd/raw*100))

print("\n" + "=" * 75)
print("WHY THEY WIN (for now)")
print("=" * 75)
print("""
gzip/brotli/zstd use BYTE-LEVEL pattern matching (LZ77/LZ78):
  - They find repeated BYTE SEQUENCES and replace with back-references
  - Article x10 = same bytes repeated 10 times = massive back-references
  - They encode: "repeat previous 1500 bytes" in ~3 bytes
  - EXTREMELY efficient for repetitive content

Our system uses WORD-LEVEL encoding:
  - We store each unique WORD once + its positions
  - Positions for high-frequency words are expensive (many occurrences)
  - We DON'T exploit byte-level repetition at all
  - Our blank system helps but only removes ~10-15 words
""")

# Analyze where our bytes go
print("=" * 75)
print("WHERE OUR BYTES GO (Article x10)")
print("=" * 75)

text = " ".join((" ".join([ARTICLE] * 10)).split())
tok = Tokenizer()
doc = tok.tokenize(text)
idx = IndexBuilder().build(doc.tokens)

print("\nDocument stats:")
print("  Total tokens: %d" % len(doc.tokens))
print("  Unique words: %d" % len(idx.word_order))
print("  Lines: %d" % doc.line_count)

# Count words by occurrence
from collections import Counter
occ = Counter()
for word in idx.word_order:
    count = len(idx.entries[word])
    if count >= 10:
        occ["10+ occurrences"] += 1
    elif count >= 5:
        occ["5-9 occurrences"] += 1
    elif count >= 3:
        occ["3-4 occurrences"] += 1
    elif count == 2:
        occ["2 occurrences"] += 1
    else:
        occ["1 occurrence"] += 1

print("\nWord frequency distribution:")
for bucket in ["1 occurrence", "2 occurrences", "3-4 occurrences", "5-9 occurrences", "10+ occurrences"]:
    print("  %s: %d words" % (bucket, occ.get(bucket, 0)))

# Calculate theoretical minimum
print("\n" + "=" * 75)
print("THEORETICAL MINIMUM (what we COULD achieve)")
print("=" * 75)

# For each unique word: word_id (1-2 bytes) + position data
total_word_ids = 0
total_positions = 0
total_tokens_stored = 0
blankable_positions = 0

for word in idx.word_order:
    count = len(idx.entries[word])
    rank = d.word_to_rank(word)
    if rank and rank <= 127:
        wid_cost = 1
    elif rank and rank <= 16511:
        wid_cost = 2
    elif rank:
        wid_cost = 3
    else:
        wid_cost = 2 + len(word)  # unknown word inline

    pos_cost_per = 1.5  # 12 bits per position = 1.5 bytes
    pos_cost = int(count * pos_cost_per)

    if count >= 5:
        # Blankable - just need constraint marker
        blankable_positions += count
        # Don't count this word at all (blanked)
    else:
        total_word_ids += wid_cost
        total_positions += pos_cost
        total_tokens_stored += count

# Metadata costs
header = 16
blank_metadata = 50  # rough estimate for blank markers + checksums
caps_bitmap = (len(doc.tokens) + 7) // 8
punct_table = 150  # rough estimate

total_min = header + total_word_ids + total_positions + blank_metadata + caps_bitmap + punct_table

raw = len(text.encode("utf-8"))
print("\n  Word IDs: %d bytes (%d non-blanked words)" % (total_word_ids, len(idx.word_order) - occ.get("10+ occurrences", 0) - occ.get("5-9 occurrences", 0)))
print("  Positions: %d bytes (%d tokens at 1.5 bytes each)" % (total_positions, total_tokens_stored))
print("  Blanked: %d tokens from %d words (saved)" % (blankable_positions, occ.get("10+ occurrences", 0) + occ.get("5-9 occurrences", 0)))
print("  Blank metadata: ~%d bytes" % blank_metadata)
print("  Caps bitmap: %d bytes" % caps_bitmap)
print("  Punct table: ~%d bytes" % punct_table)
print("  Header: %d bytes" % header)
print("  ─────────────────────────")
print("  THEORETICAL MIN: %d bytes" % total_min)
print("  RATIO: %.1f:1" % (raw / total_min))
print("  vs gzip: %.1f:1" % (raw / gz))

print("\n  GAP: We need %d bytes. gzip does %d bytes." % (total_min, gz))
print("  That is %.1fx gap." % (total_min / gz))

print("\n" + "=" * 75)
print("THE PATH TO BEATING THEM")
print("=" * 75)
print("""
THEIR ADVANTAGE: byte-level repetition detection (LZ77)
  Article x10 repeats the same paragraph 10 times.
  gzip says "copy previous 1499 bytes" x9 = ~30 bytes for 9 copies.
  We say "here is word 'the' at 29 positions" = much more expensive.

OUR ADVANTAGE: shared dictionary on Hive (zero per-document cost)
  gzip includes its Huffman table in EVERY compressed file.
  We store the dictionary ONCE on Hive.
  For 1 document: gzip wins (small Huffman table vs our overhead).
  For 1000 documents: we win IF our per-doc size is competitive.

THE KEY INSIGHT: We need LZ-STYLE encoding on the word_id stream.
  After converting text to word_ids, the id stream ITSELF is repetitive.
  Article x10 produces the same word_id sequence repeated 10 times.
  If we apply delta/back-reference encoding to the word_id stream,
  we get LZ-like compression on top of our word-level encoding.

  This is the missing piece: ENTROPY CODING on the final byte stream.

  Step 1: Text -> word_ids + positions (what we have now)
  Step 2: Blank high-frequency words (what we have now)
  Step 3: COMPRESS the remaining byte stream with zlib/deflate
          (this is the nuclear option that closes the gap)

  The result: word-level compression PLUS byte-level compression.
  gzip only does byte-level. We do BOTH.
""")

# Demonstrate: what if we just zlib-compress our output?
c = Compressor(dictionary=d)
our_blob = c.compress(text)
our_plus_zlib = zlib.compress(our_blob, 9)

print("DEMONSTRATION: Our compression + zlib on top")
print("  Raw text: %d bytes" % raw)
print("  Our blob: %d bytes (%.1f:1)" % (len(our_blob), raw/len(our_blob)))
print("  Our blob + zlib: %d bytes (%.1f:1)" % (len(our_plus_zlib), raw/len(our_plus_zlib)))
print("  gzip alone: %d bytes (%.1f:1)" % (gz, raw/gz))
print()

if len(our_plus_zlib) < gz:
    print("  >>> WE WIN! Our system + zlib beats gzip! <<<")
else:
    print("  Gap remaining: %d bytes (%.1fx)" % (len(our_plus_zlib) - gz, len(our_plus_zlib)/gz))
    print("  Our blob has structure that zlib can exploit.")
    print("  With better word-level pre-processing, this gap closes.")
