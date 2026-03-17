"""
Can we pre-compute a STATIC template of ALL possible coordinate patterns?

The grid: 100 rows x 16 word slots = 1,600 possible positions.
A word can appear at ANY SUBSET of these 1,600 positions.
The number of possible subsets = 2^1600 = impossibly large.

BUT: we don't need ALL subsets. We need SMART encoding.

The approach: DON'T template the full position combination.
Instead, template EACH INDIVIDUAL POSITION as a separate mark.

Each occurrence of a word needs one coordinate: (row, slot).
There are exactly 1,600 possible coordinates.
1,600 values fits in 11 bits = can be indexed with 2 bytes.

So the static template has exactly 1,600 entries:
  mark 0    = position (row 0, slot 0)
  mark 1    = position (row 0, slot 1)
  ...
  mark 15   = position (row 0, slot 15)
  mark 16   = position (row 1, slot 0)
  ...
  mark 1599 = position (row 99, slot 15)

For a word appearing N times, you store N coordinate marks.
Each mark = 2 bytes (or less with smart encoding).

"the" appears 100 times → 100 coordinate marks × 2 bytes = 200 bytes.
That is WORSE than bit-packing (138 bytes).

WAIT. The user doesn't want to store per-occurrence marks.
They want ONE mark that encodes ALL occurrences.
The template maps that ONE mark to all the positions.

So we need: one PATTERN ID that maps to a SET of positions.
How many unique sets exist?
"""
from math import comb, log2, ceil

print("=" * 70)
print("STATIC TEMPLATE: How to encode position SETS compactly")
print("=" * 70)

# The REAL approach: don't enumerate all possible subsets (2^1600).
# Instead, encode the set DESCRIPTION compactly.

# A set of positions is fully described by:
#   - How many positions (count: 1 byte, 0-255)
#   - Which positions (the actual coordinates)

# The most compact description of a set of K positions from 1600:
# Sorted list of K values from 0-1599.
# Each value: 11 bits.
# K values: 11*K bits.
# With delta encoding: first value 11 bits, each delta 7-11 bits.

# But the user wants a SINGLE mark/symbol that encodes the ENTIRE set.
# That mark is an INDEX into a template table.
# The template table maps index → position set.

# How big is the index? Depends on how many unique sets we expect.
# In practice, across all documents ever compressed, the number of
# unique position sets for any given word is bounded by the number
# of documents (each doc creates one set per word).

# If we compress 1 million documents, each with ~244 unique words,
# that is 244 million unique sets MAXIMUM (if every doc is different).
# In practice, MUCH fewer because patterns repeat.

# A 3-byte index addresses 16.7 million unique sets.
# A 4-byte index addresses 4.3 billion.

# But the user wants this STATIC (pre-computed, not growing).
# That means we need to enumerate all USEFUL position sets in advance.

print("""
APPROACH 1: Decompose into per-line horizontal patterns

Instead of templating the FULL position set, decompose it:

  For each LINE the word appears on:
    - Which horizontal SLOT does it occupy? (0-15)

  The word's full position = list of (line, slot) pairs.

  We can split this into:
    WHICH LINES:  encoded as existing vertical coordinate template (1-2 bytes)
    WHICH SLOTS:  one slot value per line (4 bits each)

  "the" at (line 1 slot 3), (line 5 slot 0), (line 12 slot 7):
    Vertical: lines [1, 5, 12] → vertical template code (2 bytes)
    Horizontal: slots [3, 0, 7] → pack 3 × 4 bits = 12 bits = 2 bytes
    Total: 2 + 2 = 4 bytes for 3 occurrences!

  "the" at 100 positions:
    Vertical: 100 line numbers → delta encoded (~50-100 bytes)
    Horizontal: 100 slot values × 4 bits = 50 bytes
    Total: ~100-150 bytes

  Still too much for 100 occurrences. BLANK is better for high counts.
""")

print("APPROACH 2: The slot is ALWAYS known from the grid\n")

# WAIT. Critical insight:
# In the inverted index, we store the word ONCE and its positions.
# But what if instead, we store the word AT EACH POSITION in sequence?
# Then the position is IMPLIED by where the word appears in the stream.

# The 80-char bin creates a grid. Reading left to right, top to bottom:
# Position 0 = (line 1, slot 0)
# Position 1 = (line 1, slot 1)
# ...
# Position 15 = (line 1, slot 15)
# Position 16 = (line 2, slot 0)
# etc.

# If we store the document as a SEQUENTIAL stream of word marks:
# [mark_for_pos_0] [mark_for_pos_1] [mark_for_pos_2] ...

# Then EVERY position is free! The position is just the index in the stream.
# "the" at position 0 = the stream starts with the mark for "the".
# "the" at position 37 = position 37 in the stream is "the"'s mark.

# Cost per token: just the word_id. No position data at all!
# "the" appearing 100 times = 100 × word_id(1 byte) = 100 bytes.
# "cat" appearing 1 time = 1 × word_id(2 bytes) = 2 bytes.

# TOTAL for document: one word_id per token, in sequence.
# Average word_id: ~1.3 bytes (55% are 1-byte top-127 words)
# 2500 tokens × 1.3 bytes = 3,250 bytes

# BUT the inverted index was: 244 unique words × ~5 bytes = 1,220 bytes
# SEQUENTIAL is worse when words repeat a lot.

# HOWEVER: we can COMBINE sequential with the blank system.
# Store the stream sequentially, but SKIP blanked positions.
# The blanked positions are recovered from checksum.

# Sequential stream with blanks:
# [mark][mark][BLANK][mark][mark][BLANK][BLANK][mark]...
# Each mark = 1-2 byte word_id
# Each BLANK = 0 bytes (inferred from gap)

# If we blank "the" (100 occurrences) + "a" (50) + "and" (40) + "of" (30):
# 220 blanked tokens → 220 positions that are just gaps
# 2280 remaining tokens × 1.3 bytes = 2,964 bytes
# + blank metadata: ~50 bytes
# = ~3,014 bytes

# Still worse than inverted index (~1,220).
# BECAUSE: sequential repeats word_ids for every occurrence.
# Inverted index stores each word_id ONCE.

print("SEQUENTIAL vs INVERTED INDEX:")
print("-" * 40)

# Let us compare properly
tokens = 2500
unique = 244
avg_word_id = 1.3
blanked_tokens = 220  # top 4 words
remaining_tokens = tokens - blanked_tokens

# Sequential
seq_cost = remaining_tokens * avg_word_id + 50  # + blank metadata
print(f"  Sequential: {remaining_tokens} tokens × {avg_word_id} = {seq_cost:.0f} bytes")

# Inverted index with bit-packed positions (new format)
inv_words = unique - 4  # minus blanked words
avg_word_entry = 4 + 1 + ceil(11 * 2 / 8)  # word_id + count + avg 2 positions packed
inv_cost = inv_words * avg_word_entry + 50  # + blank metadata
print(f"  Inverted (bit-packed): {inv_words} words × ~{avg_word_entry} bytes = {inv_cost:.0f} bytes")

# Inverted index with 2-byte coordinate template per word
inv_template = inv_words * (2 + 2 + 2) + 50  # word_id + vert_template + horiz_template
print(f"  Inverted (templates): {inv_words} words × ~6 bytes = {inv_template:.0f} bytes")

print()
print("=" * 70)
print("THE ANSWER: What is the absolute smallest possible encoding?")
print("=" * 70)

print("""
For EACH UNIQUE WORD in the document, the minimum data is:

  1. WHICH WORD:     word_id        (1-2 bytes, from dictionary)
  2. HOW MANY TIMES: occurrence count (can be derived from position data)
  3. WHERE:          position data   (the expensive part)

Position data minimum (information theory):
  Each position is one of 1,600 values (100 rows × 16 slots).
  log2(1600) = 10.64 bits per position.
  K positions = 10.64 × K bits minimum.
  This is a HARD FLOOR. No encoding can beat it.

  1 occurrence:   11 bits = 2 bytes
  2 occurrences:  22 bits = 3 bytes
  3 occurrences:  33 bits = 5 bytes
  10 occurrences: 107 bits = 14 bytes
  100 occurrences: 1064 bits = 133 bytes

  UNLESS you don't store positions at all (blank + checksum recovery).

THE THEORETICAL MINIMUM for a document:
  Sum over all unique words of: word_id + position_bits

  For words appearing 1-4 times: word_id(1-2) + positions(2-6) = 3-8 bytes
  For words appearing 5+ times: BLANKED = 0 bytes + ~10 bytes blank overhead

  244 unique words in Article x10:
    230 words × 5 bytes avg = 1,150 bytes
    14 blanked words × 0 + metadata 100 bytes = 100 bytes
    Header + caps + punct: ~300 bytes
    TOTAL: ~1,550 bytes = 9.7:1 ratio

  This is the FLOOR. No encoding scheme can beat this without
  losing information (which means imperfect reconstruction).

CAVEMAN MARK APPROACH:
  word_mark (1-2 bytes) + coordinate_mark (2-5 bytes) per word
  = same as above, just different labels

  The coordinate_mark IS the bit-packed position data.
  Whether you call it a "mark" or "packed bits" or "template reference",
  it is 11 bits per occurrence of information. That is the physics.

  For 100 occurrences, 133 bytes of position info exists.
  You MUST either store it (133 bytes) or blank it (~10 bytes).
  No visual encoding trick changes this. The information is the information.

THE STATIC TEMPLATE THAT WORKS:
  It is the existing coordinate template system.
  8,946 templates covering 1-3 position patterns.
  Each template = 1-2 byte code = 1-2 byte mark.
  Pre-computed, static, set in stone.

  For 4+ positions: bit-pack them (11 bits each).
  For 5+ occurrences: BLANK them.

  This IS the dictionary of marks. 8,946 coordinate marks +
  249,777 word marks = the complete static dictionary.
""")
