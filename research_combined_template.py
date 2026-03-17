"""
Research: Baking vertical + horizontal into ONE template integer.

Grid: 100 rows × 16 word slots per row = 1,600 possible positions.
A single position = (row, slot) = one integer from 0-1599.
A template maps a single ID to a LIST of these combined positions.
"""

from math import log2, ceil

print("=" * 70)
print("COMBINED VERTICAL + HORIZONTAL TEMPLATE MATH")
print("=" * 70)

ROWS = 100
SLOTS = 16  # typical max words per 80-char line
TOTAL_POSITIONS = ROWS * SLOTS

print(f"\nGrid: {ROWS} rows x {SLOTS} word slots = {TOTAL_POSITIONS} possible positions")
print(f"Bits to encode one position: {ceil(log2(TOTAL_POSITIONS))} bits")
print(f"A single (row, slot) pair fits in: {ceil(log2(TOTAL_POSITIONS)/8)} bytes")
print()

# Method 1: Pack (row, slot) into a single integer
print("METHOD 1: Pack (row, slot) into one integer")
print("-" * 40)
print(f"  position_id = row * {SLOTS} + slot")
print(f"  Range: 0 to {TOTAL_POSITIONS - 1}")
print(f"  Fits in: 11 bits = 2 bytes (uint16, with 5 spare bits)")
print()
print(f"  Example: row=37, slot=5 → {37 * SLOTS + 5} = 0x{37 * SLOTS + 5:04X}")
print(f"  Decode:  {37 * SLOTS + 5} // {SLOTS} = row {(37 * SLOTS + 5) // SLOTS}, {37 * SLOTS + 5} % {SLOTS} = slot {(37 * SLOTS + 5) % SLOTS}")
print()

# Method 2: Template lookup for combined positions
print("METHOD 2: Template for COMBINED positions (both dimensions)")
print("-" * 40)

# For K occurrences, each at one of 1,600 positions
# If ORDER MATTERS (which it does for reconstruction):
# possibilities = 1600^K (permutations with repetition)

# If order is SORTED (positions in grid order):
# possibilities = C(1600+K-1, K) (combinations with repetition)
# But sorted is fine since we reconstruct by grid position anyway

from math import comb as C

print(f"  Unique templates needed (positions sorted, with repetition):")
for k in range(1, 8):
    # Combinations with repetition: C(n+k-1, k) where n=1600
    combos = C(TOTAL_POSITIONS + k - 1, k)
    if combos > 0:
        bits = ceil(log2(combos)) if combos > 1 else 1
        template_id_bytes = ceil(bits / 8)

        # Storage on Hive: each template stores K position IDs (2 bytes each)
        template_data_bytes = k * 2
        total_hive_storage = combos * template_data_bytes

        hive_mb = total_hive_storage / (1024 * 1024)
        feasible = "YES" if hive_mb < 1000 else "NO (too large)"

        print(f"  {k} occurrences:")
        print(f"    Templates: {combos:>15,}")
        print(f"    Template ID: {template_id_bytes} bytes ({bits} bits)")
        print(f"    Hive storage: {hive_mb:,.1f} MB  [{feasible}]")
    else:
        print(f"  {k} occurrences: overflow")

print()
print("=" * 70)
print("THE SWEET SPOT")
print("=" * 70)
print(f"""
  1 occurrence:  1,600 templates, 1.5 bytes ID → use 2 bytes
    Hive: 3 KB. TRIVIAL.

  2 occurrences: ~1.3 million templates, 3 bytes ID
    Hive: 5 MB. EASY.

  3 occurrences: ~683 million templates, 4 bytes ID
    Hive: 4 GB. TOO MUCH for full pre-computation.

  SOLUTION: Pre-compute 1-2 occurrences. Use delta for 3-4. Blank 5+.
""")

# But wait - can we be smarter about 3+ occurrences?
print("=" * 70)
print("SMARTER APPROACH: HYBRID ENCODING")
print("=" * 70)

# Instead of one template for ALL positions, use:
# Template for horizontal (1-2 bytes) + compact vertical encoding

# Horizontal only: 16 slots
# For K occurrences: 16^K possibilities
# K=1: 16 → 4 bits
# K=2: 256 → 8 bits = 1 byte
# K=3: 4096 → 12 bits = 2 bytes
# K=4: 65536 → 16 bits = 2 bytes
# K=5: 1048576 → 20 bits = 3 bytes

# Vertical: row numbers 1-100
# For K occurrences: encode as delta list
# First row: 7 bits (0-99)
# Each subsequent delta: 7 bits (0-99 gap)
# K rows = 7*K bits

print(f"""
Instead of one mega-template, split into:
  HORIZONTAL TEMPLATE (small, pre-computed on Hive):
    Encodes which SLOTS the word occupies on each of its lines.
    K=1: 4 bits, K=2: 1 byte, K=3: 2 bytes, K=4: 2 bytes

  VERTICAL ENCODING (compact, per-document):
    Which LINES the word appears on.
    Use existing coordinate tier system (1-2 bytes for 1-3 lines).

  COMBINED per word:
    word_id (1-2 bytes) + horiz_template (1-2 bytes) + vert_template (1-2 bytes)
    = 3-6 bytes total for ANY number of occurrences up to 4
""")

# Now the real estimate
print("=" * 70)
print("REAL ESTIMATE: Combined horizontal + vertical templates")
print("=" * 70)

# Horizontal templates needed:
h_templates = {}
for k in range(1, 8):
    n = SLOTS ** k
    bits = ceil(log2(n)) if n > 1 else 1
    h_bytes = ceil(bits / 8)
    hive_kb = n * k / 1024
    h_templates[k] = {'count': n, 'id_bytes': h_bytes, 'hive_kb': hive_kb}
    print(f"  Horizontal templates for {k} occurrences: {n:>10,} templates, {h_bytes}-byte ID, {hive_kb:.0f} KB on Hive")

print()
# Vertical templates (already exist): 8,946 covering 1-3 positions + delta for 4+
print(f"  Vertical templates (ALREADY BUILT): 8,946 templates, 1-2 byte ID")
print()

# Per-word encoding cost
print("  PER WORD ENCODING:")
print(f"    word_id:          1-2 bytes (frequency rank)")
print(f"    horiz_template:   1-2 bytes (horizontal slot pattern)")
print(f"    vert_template:    1-2 bytes (vertical line pattern)")
print(f"    ─────────────────────────────")
print(f"    TOTAL:            3-6 bytes per word")
print()

# Savings vs current system
print("  VS CURRENT SYSTEM:")
print(f"    Current: word_id(1-3) + vert_pos_len(2) + vert_data(var) + horiz_pos_len(2) + horiz_data(var)")
print(f"    Word appearing 3x: ~15 bytes currently")
print(f"    Word appearing 3x: ~5 bytes with combined templates")
print(f"    Savings: ~10 bytes per 3-occurrence word")
print()

# Article x10 estimate with this approach
print("=" * 70)
print("ARTICLE x10 ESTIMATE (15,000 bytes raw)")
print("=" * 70)
print(f"""
  244 unique words:
    ~14 words (5+ occurrences): BLANKED = 0 bytes each
    ~30 words (3-4 occurrences): 5 bytes each = 150 bytes
    ~80 words (2 occurrences): 4 bytes each = 320 bytes
    ~120 words (1 occurrence): 3 bytes each = 360 bytes

  Word table: 150 + 320 + 360 = 830 bytes
  Header: 16 bytes
  Caps bitmap: ceil(2500/8) = 313 bytes
  Punctuation: ~150 bytes
  Blank markers: ~50 bytes
  Line word counts: ~100 bytes

  TOTAL: ~1,459 bytes
  RATIO: {15000/1459:.1f}:1 compression!

  vs current 7,020 bytes (2.1:1)
  vs target 5,000 bytes (3:1)

  THIS SMASHES THE TARGET.
""")

# Hive template storage totals
print("HIVE TEMPLATE STORAGE (one-time):")
total_h = sum(t['hive_kb'] for k, t in h_templates.items() if k <= 4)
print(f"  Horizontal templates (1-4 occ): {total_h:.0f} KB")
print(f"  Vertical templates (existing): ~900 KB")
print(f"  Word dictionary: ~5 MB")
print(f"  TOTAL: ~6 MB on Hive (one-time)")
