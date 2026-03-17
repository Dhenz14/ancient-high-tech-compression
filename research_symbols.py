"""Research: How far can custom symbols go?"""
import base64, zlib

print("=" * 70)
print("SYMBOL FORMAT CAPACITY ANALYSIS")
print("=" * 70)

print("\n1. UNICODE CODE POINT")
print("   Storage: 1-4 bytes (UTF-8)")
print("   Total code points: 1,114,112")
print("   Private Use Area: 137,468 code points (for custom symbols)")
print("   Visual complexity: UNLIMITED (defined by the font)")
print("   A 2-byte code point can render as ANY visual pattern")

print("\n2. OPENTYPE VARIABLE FONT (THE KEY)")
print("   Custom variation axes: up to 32,000+ per font")
print("   Each axis: continuous value (float precision)")
print("   CSS: font-variation-settings: 'VPOS' 1523, 'HPOS' 742;")
print("   The VARIATION VALUES change the glyph WITHOUT changing the code point")
print("   ")
print("   Example: character U+E000 with variations:")
print("     'VCNT' 100    -> glyph renders with 100 internal marks")
print("     'VPS1' 1523   -> first position data")
print("     'HPS1' 742    -> second position data")
print("   ")
print("   The font file defines HOW each axis changes the glyph")
print("   The document specifies the VALUES for each axis")

print("\n3. COLOR FONTS (COLR/CPAL or SVG-in-OpenType)")
print("   Multiple colored layers per glyph")
print("   Each layer can have different opacity")
print("   SVG-in-OpenType: full SVG per glyph (unlimited complexity)")
print("   A single character can render as a multi-layer micro-barcode")

print("\n4. PIXEL-LEVEL DATA DENSITY")
print("   At 8x8 pixels (tiny symbol):")
print("     1-bit (B/W):     64 bits  = 8 bytes of data")
print("     8-bit (grayscale): 512 bits = 64 bytes of data")
print("     32-bit (RGBA):   2048 bits = 256 bytes of data")
print("   At 16x16 pixels:")
print("     1-bit:           256 bits  = 32 bytes")
print("     8-bit:          2048 bits  = 256 bytes")
print("   ")
print("   100 word positions need ~200 bytes (line + column each)")
print("   A 16x16 grayscale pixel grid can hold 256 bytes")
print("   So 100 positions FIT in a 16x16 pixel symbol!")

print("\n5. QR-CODE-LIKE MICRO SYMBOLS")
print("   QR Version 1 (21x21 modules): 152 bits = 19 bytes")
print("   Micro QR M4 (17x17 modules):   80 bits = 10 bytes")
print("   Data Matrix 10x10:             ~36 bits =  4.5 bytes")
print("   Custom 8x8 matrix:             ~40 bits =  5 bytes")

print("\n6. THE REAL QUESTION: WHAT DOES HIVE ACTUALLY STORE?")
print("   Hive custom_json stores: UTF-8 text (max ~8KB)")
print("   You CANNOT store raw pixels in custom_json")
print("   You CAN store:")
print("     - Unicode characters (rendered by client-side font)")
print("     - Base64-encoded binary (133% overhead)")
print("     - Compact numeric sequences")
print("   ")
print("   The FONT FILE is stored separately on Hive (one-time upload)")
print("   The document stores only CHARACTER CODES")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)
print("""
The answer to 'how far can we customize' has TWO parts:

PART 1 - WHAT THE FONT CAN DO (unlimited, stored once):
  The font can define glyphs of arbitrary complexity.
  Micro-lines, dots, opacity layers, color layers, variable axes.
  A single glyph can visually encode HUNDREDS of data points.
  The font file lives on Hive forever. Cost: one-time only.

PART 2 - WHAT THE DOCUMENT STORES (the real constraint):
  The document stores CHARACTER CODES (1-3 bytes each).
  The document can also store VARIATION VALUES per character.
  But variation values cost bytes. Each axis value = ~2-4 bytes.

  If positions are BAKED INTO THE GLYPH (static per word):
    1 code point = 1-3 bytes = holds everything. Maximum compression.
    BUT: positions are different per document, so this only works
    if you have a glyph for every possible position combination.
    With 8,946 position templates, you need 8,946 glyphs per word.
    249,777 words x 8,946 = 2.2 BILLION glyphs. Too many.

  If positions are ENCODED AS VARIATION VALUES (dynamic per document):
    1 code point + N variation values = 1-3 + N*2 bytes
    100 positions = 1 + 200 = 201 bytes
    That is the SAME as byte-level position encoding (no savings)

THE HONEST TRUTH:
  The font/visual system cannot compress BEYOND what bytes can do.
  Information is information - it takes the same bits whether stored
  as bytes or as visual properties.

  BUT the font system does something bytes CAN'T:
  It makes compressed data HUMAN/AI READABLE without decompression.
  A scanner sees the rendered page and understands it directly.
  That is genuinely unique and valuable.

WHERE VISUAL ENCODING ACTUALLY WINS:
  When the visual property is IMPLICIT in the format, not stored.

  Example: SEQUENCE POSITION.
  A character's position in the text stream is FREE - you don't
  store it, it's implied by order. That is 'free information.'

  The 80-char bin is the same idea: line breaks are implied by
  the 80-char width. You don't store them.

  The question is: what OTHER information can be made implicit?

  - Character ORDER in stream = word order (FREE)
  - Line breaks from 80-char width = vertical position (FREE)
  - Word index within line = horizontal position (FREE)
  - These are ALL already used in our grid system.

  The font adds: VISUAL PROPERTIES rendered at display time.
  If a property can be computed from the code point alone
  (without per-document variation), it is truly free.

  Word identity: FREE (it IS the code point)
  POS category: FREE (computable from the word)
  Morph form: ALMOST FREE (can be encoded in code point choice)
  Positions: NOT FREE (per-document, must be stored somehow)
""")
