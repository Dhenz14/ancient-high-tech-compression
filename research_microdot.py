"""
Micro-dot encoding: Can position data fit FREE inside a fixed-size image?

The idea: a raw bitmap of fixed size (e.g., 8x8 = 8 bytes).
Each dot's position in the grid encodes a (row, slot) coordinate.
The number of dots = number of occurrences.
The image size is ALWAYS the same regardless of dot count.
Position data is FREE — it's the dot pattern, not extra bytes.
"""

print("=" * 70)
print("MICRO-DOT ENCODING: Position data as dot patterns in fixed-size images")
print("=" * 70)

# The grid: 100 rows x 16 slots = 1600 possible positions
# The image grid: NxN pixels

# Question: how big does the image need to be to uniquely address
# all 1600 positions?

# If each pixel = one possible position:
#   Need 1600 pixels minimum
#   sqrt(1600) = 40 → 40x40 pixel image
#   Size: 40*40/8 = 200 bytes (1-bit bitmap)
#   That's TOO BIG. Worse than just storing positions.

# BUT: we don't need 1 pixel per position.
# We need: row (0-99) encoded in Y, slot (0-15) encoded in X.
# Image grid: 16 columns x 100 rows → 16x100 pixel image
# Size: 16*100/8 = 200 bytes. Still too big.

# What if we scale down?
# Use a SMALLER image where pixels map to RANGES?
# 8x8 image: 8 columns x 8 rows = 64 pixels
# Each column represents 2 horizontal slots (16/8 = 2 slots per column)
# Each row represents ~12.5 vertical rows (100/8 = 12.5 rows per pixel row)
# Resolution: can distinguish 8 horizontal zones x 8 vertical zones = 64 zones
# NOT enough for exact positioning.

print("\nPROBLEM: Image resolution vs grid resolution")
print("-" * 40)

for img_size in [4, 8, 12, 16, 20, 32]:
    n_pixels = img_size * img_size
    n_bytes = n_pixels // 8
    h_resolution = 16 / img_size  # slots per pixel column
    v_resolution = 100 / img_size  # rows per pixel row
    exact_h = h_resolution <= 1.0
    exact_v = v_resolution <= 1.0
    print(f"  {img_size}x{img_size} image: {n_bytes:3d} bytes, "
          f"H-res: {'EXACT' if exact_h else f'{h_resolution:.1f} slots/px'}, "
          f"V-res: {'EXACT' if exact_v else f'{v_resolution:.1f} rows/px'}")

print()
print("=" * 70)
print("THE REAL INSIGHT: The image doesn't need to be THE storage format")
print("=" * 70)
print("""
The micro-dot image is a VISUAL REPRESENTATION, not the storage format.
The storage format is the binary blob we already have.

The question is: can we make position storage MORE COMPACT?

Currently: 11 bits per position (row*16 + slot), bit-packed.
  1 occurrence:  2 bytes (11 bits padded)
  2 occurrences: 3 bytes (22 bits padded)
  3 occurrences: 5 bytes (33 bits padded)
  10 occurrences: 14 bytes (110 bits)
  100 occurrences: 138 bytes (1100 bits)

Can we do better? YES — with a LOOKUP TABLE (the template).
""")

# The key: a 2-byte template ID can reference ANY pre-computed pattern.
# But for 100 occurrences, the number of possible patterns is astronomical.
#
# HOWEVER: if we store the image AS the data (not a reference to it),
# then a fixed-size image encodes positions for free.
#
# The trick: we DON'T need pixel-perfect resolution.
# We need to encode which of the 1600 positions are occupied.
# That is: a BIT VECTOR of 1600 bits = 200 bytes.
# Each bit = "is this position occupied?" (1=yes, 0=no)

print("=" * 70)
print("THE BIT VECTOR APPROACH: 1 bit per grid position")
print("=" * 70)

grid_positions = 100 * 16  # 1600 positions
bitvector_bytes = (grid_positions + 7) // 8

print(f"\n  Grid: 100 rows x 16 slots = {grid_positions} positions")
print(f"  Bit vector: {bitvector_bytes} bytes (1 bit per position)")
print(f"  This encodes ALL positions for a word, regardless of count.")
print(f"  1 occurrence or 100 occurrences = SAME {bitvector_bytes} bytes.")
print()

# Compare:
print("  COMPARISON: bit vector vs bit-packed positions")
print(f"  {'Occurrences':>12s}  {'Bit-packed':>10s}  {'Bit vector':>10s}  {'Winner':>8s}")
for k in [1, 2, 3, 5, 10, 20, 50, 100]:
    packed = (11 * k + 7) // 8 + 1  # +1 for count byte
    vector = bitvector_bytes
    winner = "packed" if packed < vector else "VECTOR" if vector < packed else "tie"
    print(f"  {k:12d}  {packed:9d}B  {vector:9d}B  {winner:>8s}")

print(f"""
  CROSSOVER POINT: bit vector wins at ~{bitvector_bytes * 8 // 11} occurrences.
  Below that, bit-packed positions are smaller.
  Above that, the fixed-size bit vector is smaller.
""")

# But 200 bytes is big. Can we make the grid smaller?
print("=" * 70)
print("OPTIMIZED BIT VECTORS FOR SMALLER GRIDS")
print("=" * 70)

for rows, slots in [(100, 16), (50, 16), (100, 8), (50, 8), (25, 16), (25, 8)]:
    positions = rows * slots
    bv_bytes = (positions + 7) // 8
    crossover = bv_bytes * 8 // 11
    print(f"  {rows:3d} rows x {slots:2d} slots = {positions:4d} positions = {bv_bytes:3d} byte vector (wins at {crossover}+ occurrences)")

print()
print("=" * 70)
print("THE PRACTICAL ANSWER")
print("=" * 70)
print("""
For the compression pipeline (bytes on chain):

  LOW OCCURRENCE (1-4x):  Bit-packed 11-bit positions = 2-6 bytes
  MEDIUM OCCURRENCE (5-14x): Bit-packed positions = 8-20 bytes
  HIGH OCCURRENCE (15+x):   BLANK IT (checksum recovery, 0 bytes)

  OR if we keep words instead of blanking:
  HIGH OCCURRENCE (15+x):   200-byte bit vector (fixed, same for 15 or 100)

  But blanking is BETTER than a 200-byte vector. So: BLANK high-frequency words.

For the VISUAL layer (how it looks when rendered):

  The bit vector IS a micro-dot image!
  A 100x16 bit vector rendered as pixels = the micro-dot barcode.
  Dots show where the word appears in the grid.
  1 dot or 100 dots = same image dimensions.

  The visual representation is the bit vector, visualized.

  On Hive: the FONT GLYPH for word "the" could display this bit vector
  as a pattern of dots. The scanner reads the dots = reads the bit vector.

  In the compressed BLOB: store the most compact format (bit-packed for
  low occurrence, blank for high occurrence).

  The two representations are EQUIVALENT:
    Bit-packed positions = compact bytes for storage
    Micro-dot image = visual rendering for scanning
    Both encode the same information.
    Use the smaller one for storage. Render the visual one for display.
""")

# Final: the winning format
print("=" * 70)
print("WINNING FORMAT: Combined encoding")
print("=" * 70)
print("""
PER WORD IN DOCUMENT:

  [word_id: 1-2 bytes] [count: 1 byte] [positions: bit-packed 11-bit]

  1 occurrence:  1 + 1 + 2 = 4 bytes  (vs current 7-10)
  2 occurrences: 1 + 1 + 3 = 5 bytes  (vs current 9-14)
  3 occurrences: 1 + 1 + 5 = 7 bytes  (vs current 11-18)
  5+ occurrences: BLANKED = 0 bytes    (vs current 15-26)

  SAVINGS: 3-8 bytes per word x 230 words = 690-1840 bytes

  This IS the micro-dot system in byte form.
  Each 11-bit position is a "dot" with (row, slot) baked in.
  The count byte tells you how many dots.
  The packed bits ARE the dot pattern.

  Render it as an image → micro-dot barcode.
  Store it as bytes → compact binary.
  Same data, two views.
""")
