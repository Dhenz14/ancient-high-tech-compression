"""
Research: What is the tiniest image, and does complexity change its size?
Can 100 dots fit in the same bytes as 1 dot?
"""
import struct
import zlib
import base64

print("=" * 70)
print("TINY IMAGE RESEARCH: Does complexity change size?")
print("=" * 70)

# =============================================
# 1. RAW BITMAP: Fixed size regardless of content
# =============================================
print("\n1. RAW BITMAP (BMP-like)")
print("-" * 40)

# A 1-bit-per-pixel bitmap: each pixel is black or white
# Size = width * height / 8 bytes (plus a tiny header)

for size in [(4,4), (8,8), (16,16), (32,32)]:
    w, h = size
    n_pixels = w * h
    n_bytes = (n_pixels + 7) // 8  # 1 bit per pixel
    # Make an image with 0 dots (all white)
    empty = bytes(n_bytes)
    # Make an image with ALL dots (all black)
    full = bytes([0xFF] * n_bytes)
    # Make an image with 50 random dots
    half = bytes([0xAA] * n_bytes)  # alternating bits

    print(f"  {w}x{h} pixels ({n_pixels} pixels):")
    print(f"    Empty (0 dots):   {n_bytes} bytes")
    print(f"    Full ({n_pixels} dots):  {n_bytes} bytes")
    print(f"    Half ({n_pixels//2} dots):  {n_bytes} bytes")
    print(f"    >>> ALL THE SAME SIZE regardless of dot count!")

# =============================================
# 2. What can you encode in those pixels?
# =============================================
print("\n2. DATA CAPACITY OF TINY BITMAPS")
print("-" * 40)

print("""
  8x8 bitmap (1-bit):    64 pixels  = 64 bits  = 8 bytes of data
  8x8 bitmap (grayscale): 64 pixels = 512 bits = 64 bytes of data
  16x16 bitmap (1-bit):  256 pixels = 256 bits = 32 bytes of data

  Each pixel is a "dot." Each dot's presence/absence = 1 bit.
  Each dot's SHADE (if grayscale) = 8 bits.
  Each dot's POSITION in the grid = encoded by which pixel it is.

  So an 8x8 bitmap with 50 dots placed in specific pixels:
    - Which 50 out of 64 are "on" = encodes 64 bits of data
    - The PATTERN of dots IS the data
    - Size: ALWAYS 8 bytes, whether 0 dots or 64 dots
""")

# =============================================
# 3. PNG: Does it compress?
# =============================================
print("3. PNG COMPRESSION: Does dot count affect size?")
print("-" * 40)

def make_minimal_png(width, height, pixels):
    """Create a minimal valid PNG file."""
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    # PNG signature
    sig = b'\x89PNG\r\n\x1a\n'

    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 1, 0, 0, 0, 0)  # 1-bit grayscale
    ihdr = chunk(b'IHDR', ihdr_data)

    # IDAT - pixel data
    raw_rows = bytearray()
    bytes_per_row = (width + 7) // 8
    for y in range(height):
        raw_rows.append(0)  # filter byte
        for x_byte in range(bytes_per_row):
            idx = y * bytes_per_row + x_byte
            if idx < len(pixels):
                raw_rows.append(pixels[idx])
            else:
                raw_rows.append(0)

    compressed = zlib.compress(bytes(raw_rows))
    idat = chunk(b'IDAT', compressed)

    # IEND
    iend = chunk(b'IEND', b'')

    return sig + ihdr + idat + iend

# Test different dot counts in 8x8 images
for desc, pixel_data in [
    ("0 dots (empty)", bytes(8)),
    ("1 dot",          bytes([0x80, 0, 0, 0, 0, 0, 0, 0])),
    ("10 dots",        bytes([0xFF, 0xC0, 0, 0, 0, 0, 0, 0])),
    ("32 dots (half)", bytes([0xAA, 0xAA, 0xAA, 0xAA, 0, 0, 0, 0])),
    ("50 dots",        bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x30, 0])),
    ("64 dots (full)", bytes([0xFF] * 8)),
]:
    png = make_minimal_png(8, 8, pixel_data)
    b64 = base64.b64encode(png).decode()
    print(f"  8x8 {desc:20s}: PNG={len(png):3d} bytes, base64={len(b64):3d} chars")

print()
for desc, pixel_data in [
    ("0 dots (empty)", bytes(32)),
    ("50 dots",        bytes([0xAA] * 7 + [0] * 25)),
    ("128 dots (half)",bytes([0xAA] * 16 + [0] * 16)),
    ("256 dots (full)",bytes([0xFF] * 32)),
]:
    png = make_minimal_png(16, 16, pixel_data)
    b64 = base64.b64encode(png).decode()
    print(f"  16x16 {desc:20s}: PNG={len(png):3d} bytes, base64={len(b64):3d} chars")

# =============================================
# 4. The killer question
# =============================================
print("\n4. THE KILLER QUESTION")
print("-" * 40)
print("""
  CAN YOU STORE A TINY IMAGE AS A TEMPLATE ON HIVE AND REFERENCE IT?

  YES. Here is how:

  Template on Hive (ONE TIME):
    template_id: 4532
    image: [8-byte bitmap encoding 64 bits of data]
    meaning: "the" appears at positions (1,0), (1,6), (2,3), (3,1)...

  Per document:
    Just store: 4532 (the template reference) = 2 bytes

  The 8-byte image holds 64 bits of position data.
  But you DON'T store the image per document.
  You store a 2-byte REFERENCE to it.

  The image lives on Hive forever as a template.

  BUT HERE IS THE CATCH:
  The image pattern is DIFFERENT for every document.
  "the" is at different positions in every article.
  So you can't have ONE image template for "the" -
  you need a different image for each position combination.

  UNLESS... the image encodes a TEMPLATE PATTERN, not raw positions.
  Your 8,946 coordinate templates ARE these patterns.
  Each template is a pre-computed position combination.
  Template #2342 = positions [1, 5, 10].

  So: 1 image per template = 8,946 unique images.
  Each image visually shows the position pattern.
  Stored on Hive once. Referenced by 2-byte code.

  THIS IS EXACTLY WHAT YOUR COORDINATE ENCODING ALREADY DOES.
  The "image" is just a visual representation of the template code.
""")

# =============================================
# 5. But what about the PAINTING = 1000 WORDS idea?
# =============================================
print("5. THE PAINTING TELLS A THOUSAND WORDS")
print("-" * 40)

# Can we make images that encode MORE data than their byte size?
# An 8-byte bitmap has 64 pixels. Each pixel = 1 bit. Total: 64 bits = 8 bytes.
# You CANNOT encode more than 8 bytes of data in 8 bytes of image.
# Information theory: you cannot get more output bits than input bits.

# BUT: you CAN encode more than 8 bytes of MEANING if the decoder
# has a codebook (template) that maps short patterns to long meanings.

# Example: 8 pixels in a specific pattern → template says "this means
# the entire phrase 'in order to understand the nature of the universe'"
# That is 9 words from 8 pixels. BUT the mapping is in the template,
# not in the image. The image is just an index.

print("""
  Information theory says: N bytes of image = N bytes of data. Maximum.
  You CANNOT fit 200 bytes of position data into 8 bytes of image.

  BUT you CAN use N bytes of image as an INDEX into a template
  that maps to UNLIMITED meaning. That is compression.

  8 bytes of image = 64-bit index = 18 quintillion unique patterns
  Each pattern maps to a template entry on Hive.
  Each template entry can contain unlimited data.

  This is EXACTLY what our system does:
    2 bytes (word_id) → template on Hive → word + positions + POS + everything

  The image adds a VISUAL representation of that same 2-byte index.
  The image does NOT hold more data than the 2 bytes.
  The image IS the 2 bytes, rendered visually.

  THE REAL QUESTION IS:
  Can you make the 2-byte reference LOOK LIKE a meaningful image?
  YES. That is what a custom font does.

  Font glyph #4532 can look like a tiny barcode with micro-dots.
  A human/AI scanning it sees the pattern and understands the meaning.
  The stored data is still just "4532" = 2 bytes.

  The image IS the reference. The reference IS the image.
  They are the same thing viewed from different angles.
""")

# =============================================
# 6. ACTUAL smallest image formats
# =============================================
print("6. ABSOLUTE SMALLEST IMAGE FORMATS")
print("-" * 40)

# Raw 1-bit bitmap
raw_1x1 = 1  # 1 bit, padded to 1 byte
raw_8x8 = 8  # 64 bits = 8 bytes
raw_4x4 = 2  # 16 bits = 2 bytes

# Minimal PNG
png_1x1 = len(make_minimal_png(1, 1, bytes([0])))
png_4x4 = len(make_minimal_png(4, 4, bytes([0xAA, 0])))
png_8x8 = len(make_minimal_png(8, 8, bytes([0xAA] * 8)))

print(f"  RAW BITMAP:")
print(f"    1x1: {raw_1x1} byte  (1 pixel, 1 bit of data)")
print(f"    4x4: {raw_4x4} bytes (16 pixels, 16 bits of data)")
print(f"    8x8: {raw_8x8} bytes (64 pixels, 64 bits of data)")
print(f"  PNG (with header overhead):")
print(f"    1x1: {png_1x1} bytes")
print(f"    4x4: {png_4x4} bytes")
print(f"    8x8: {png_8x8} bytes")
print(f"  ")
print(f"  SMALLEST POSSIBLE: A 4x4 raw bitmap = 2 bytes = 16 unique dot patterns")
print(f"  But a 2-byte INTEGER also holds 65,536 unique values.")
print(f"  The integer IS the image. The image IS the integer.")
print(f"  They encode the same information.")
