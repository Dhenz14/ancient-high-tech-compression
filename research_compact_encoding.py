"""
How to encode both vertical + horizontal in the SMALLEST possible space.
Constraint: must NOT be larger than current encoding.
"""
from math import log2, ceil

print("=" * 70)
print("COMPACT COMBINED ENCODING: Both dimensions, minimum bytes")
print("=" * 70)

# Current cost per word:
# word_id (1-2) + vert_pos_len (2) + vert_data (1-2) + horiz_pos_len (2) + horiz_data (1-2)
# = 8-10 bytes per word for 1 occurrence
# = 10-14 bytes for 2 occurrences
# = 12-18 bytes for 3 occurrences

print("\nCURRENT COST PER WORD (with position length headers):")
for k in range(1, 6):
    low = 1 + 2 + max(1,k) + 2 + max(1,k)   # word_id + vert_len + vert + horiz_len + horiz
    high = 2 + 2 + max(2,k*2) + 2 + max(2,k*2)
    print(f"  {k} occurrences: {low}-{high} bytes")

print()
print("=" * 70)
print("OPTION A: Single combined position integer (no separate lengths)")
print("=" * 70)

# One position = (row 0-99, slot 0-15) = 100*16 = 1600 values
# Fits in 11 bits. Two fit in 22 bits = 3 bytes.
# But we want 2 bytes.

# What if we shrink the grid?
# 80 char line / avg 5 chars per word = ~16 word slots
# But many lines have fewer. What if max slot = 13?
# Or: what if we encode the WORD INDEX (0-N) instead of char position?

# Actually: at 100 rows and 16 slots, one position = 1600 values.
# log2(1600) = 10.64 bits. Does NOT fit in 1 byte (8 bits = 256 values).
# DOES fit in 1.5 bytes (12 bits = 4096 values).

# What if we pack differently?
# Row: 0-99 → 7 bits
# Slot: 0-15 → 4 bits
# Combined: 11 bits per position

# For 1 occurrence: 11 bits → 2 bytes (with 5 spare bits)
# For 2 occurrences: 22 bits → 3 bytes (with 2 spare bits)
# For 3 occurrences: 33 bits → 5 bytes (with 7 spare bits)
# For 4 occurrences: 44 bits → 6 bytes (with 4 spare bits)

print("\nBit-packed positions (11 bits each):")
for k in range(1, 8):
    bits = 11 * k
    bytes_needed = ceil(bits / 8)
    print(f"  {k} positions: {bits} bits = {bytes_needed} bytes")

# Compare to current (separate vert + horiz with length headers):
print("\n  COMPARISON (word_id + positions only, no length headers):")
print(f"  {'Occ':>3s}  {'Current':>8s}  {'Packed':>8s}  {'Saved':>6s}")
for k in range(1, 6):
    current = 1 + 2 + max(1,k) + 2 + max(1,k)  # conservative estimate
    packed = 1 + ceil(11 * k / 8)  # word_id + packed positions
    saved = current - packed
    print(f"  {k:3d}  {current:7d}B  {packed:7d}B  {saved:+5d}B")

print()
print("=" * 70)
print("OPTION B: Eliminate position length headers entirely")
print("=" * 70)
print("""
Current format per word entry:
  [word_id: 1-3] [vert_len: 2] [vert_data: var] [horiz_len: 2] [horiz_data: var]

The 2-byte length headers cost 4 BYTES per word. For 200 words = 800 bytes wasted!

New format:
  [word_id: 1-2] [occurrence_count: 1] [packed_positions: 11 bits each]

  occurrence_count tells you how many 11-bit positions follow.
  No length headers needed. 1 byte instead of 4.
""")

print("SAVINGS FROM REMOVING LENGTH HEADERS:")
for k in range(1, 6):
    old = 1 + 2 + max(1,k) + 2 + max(1,k)
    new = 1 + 1 + ceil(11 * k / 8)  # word_id + count + packed positions
    saved = old - new
    print(f"  {k} occurrences: {old}B → {new}B  (save {saved} bytes)")

print()
print("=" * 70)
print("OPTION C: Template reference for COMMON patterns + inline for rare")
print("=" * 70)

# The user's vision: if the template has every possibility, just reference it.
# For 1 occurrence: 1,600 patterns → 11 bits → 2 byte template ID
# But word_id is ALSO needed → word_id(1) + template(2) = 3 bytes
# Current for 1 occ: word_id(1) + 4 headers + 2 pos = 7 bytes
# Savings: 4 bytes per single-occurrence word!

# For 2 occurrences: 1,600^2 = 2.56M patterns → 21 bits → 3 bytes
# word_id(1) + template(3) = 4 bytes
# Current: word_id(1) + 4 headers + 4 pos = 9 bytes
# Savings: 5 bytes per 2-occurrence word!

# But 2.56M templates on Hive... is that ok?
# Each template entry: just the 2 position IDs = 4 bytes
# Total: 2.56M * 4 = 10 MB. Feasible!

print("Template approach vs current:")
print(f"  {'Occ':>3s}  {'Current':>8s}  {'Template':>10s}  {'Saved':>6s}  {'Templates':>12s}  {'Hive':>8s}")
for k in range(1, 5):
    current = 1 + 4 + 2*k  # word_id + 4 header bytes + position data
    templates = 1600 ** k
    template_bits = ceil(log2(templates)) if templates > 1 else 1
    template_bytes = ceil(template_bits / 8)
    new = 1 + template_bytes  # word_id + template_id
    saved = current - new
    hive = templates * k * 2 / (1024*1024)
    feasible = "ok" if hive < 100 else "big" if hive < 5000 else "NO"
    print(f"  {k:3d}  {current:7d}B  {new:9d}B  {saved:+5d}B  {templates:>11,}  {hive:6.1f}MB {feasible}")

print()
print("=" * 70)
print("THE WINNING APPROACH: HYBRID")
print("=" * 70)
print("""
  1 occurrence (120 words): COMBINED TEMPLATE
    word_id(1) + combined_template_id(2) = 3 bytes
    Save 4 bytes each = 480 bytes saved
    Templates on Hive: 1,600 (3 KB)

  2 occurrences (80 words): COMBINED TEMPLATE
    word_id(1-2) + combined_template_id(3) = 4-5 bytes
    Save 4-5 bytes each = 320-400 bytes saved
    Templates on Hive: 1,280,800 (5 MB)

    OR: bit-packed inline positions
    word_id(1-2) + count(1) + 22 bits packed = 4-5 bytes
    Same size, no template lookup needed!

  3-4 occurrences (30 words): BIT-PACKED INLINE
    word_id(1-2) + count(1) + 33-44 bits packed = 6-8 bytes
    Save 4-8 bytes each = 120-240 bytes saved

  5+ occurrences (14 words): BLANKED
    0 bytes. Checksum recovery.

  TOTAL SAVINGS vs current:
    Single-occurrence: 480 bytes
    Double-occurrence: 360 bytes
    Triple+: 180 bytes
    Position headers eliminated: saves 4 bytes x 230 words = 920 bytes

    GRAND TOTAL SAVINGS: ~1,940 bytes
    Current Article x10: 7,020 bytes
    New estimate: ~5,080 bytes

    WITH blank system improvements: ~4,500 bytes
    RATIO: 3.3:1
""")
