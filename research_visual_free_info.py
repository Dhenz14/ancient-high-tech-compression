"""
What FREE information can visual encoding provide?

The user's instinct: visual properties carry info without extra bytes.
Let me find concrete cases where this is TRUE.
"""

print("=" * 70)
print("WHERE VISUAL ENCODING PROVIDES GENUINELY FREE INFORMATION")
print("=" * 70)

print("""
PRINCIPLE: "Free info" means information derivable from something
you're ALREADY storing, without adding extra bytes.

Things we ALREADY store per word:
  - word_id (1-2 bytes)
  - position data (variable)

Things DERIVABLE from word_id (free via template lookup):
  - The word itself
  - POS category
  - Frequency rank
  - Morphological family
  - Supersense category
  - Word length

These are ALL free. The template on Hive maps word_id to all of them.
No extra bytes needed. This is what the system already does.

NOW: What can VISUAL RENDERING add on top?

CASE 1: THE GAP ASSIGNMENT PROBLEM
-----------------------------------
Currently: when multiple words are blanked, we store a gap_assignment
array (1 byte per gap) to tell which blank fills which gap.

100 gaps from "the" + 50 gaps from "a" + 40 gaps from "and" = 190 gaps
gap_assignment: 190 bytes (1 byte per gap saying which word)

Can visual encoding eliminate this?

YES — if the RENDERED OUTPUT shows blanked words as different visual marks:
  "the" gaps rendered as: ○ (empty circle)
  "a" gaps rendered as:   △ (triangle)
  "and" gaps rendered as: □ (square)

The SCANNER sees these different shapes and knows which word goes where.
But... the shapes need to be STORED in the document too. Each gap needs
a byte to indicate which shape. That IS the gap_assignment. Same cost.

UNLESS: the shapes are deterministic from the POSITION in the grid.
If we define a RULE (stored in template, not per document):
  "Gap at start of line = determiner (the/a)"
  "Gap between two nouns = conjunction (and)"
  "Gap before a noun = adjective"

Then the POSITION tells you which blanked word goes there.
No gap_assignment needed! The RULE is the template. FREE.

But... this only works if the rules are unambiguous. "the" and "a" are
both determiners. How do you tell them apart at a gap?
→ Word length! "the" = 3 chars, "a" = 1 char.
→ The gap WIDTH in the rendered output tells you which determiner.
→ But in our grid, each word is 1 slot regardless of length...
→ So word length is NOT visible from the grid.
→ But it IS stored in the constraint data (1 byte per blank).

SAVINGS: If positional rules can identify WHICH blank goes in most gaps,
the gap_assignment shrinks. Instead of 190 bytes, maybe 20 bytes
(only for ambiguous gaps).

POTENTIAL SAVINGS: ~170 bytes on Article x10.
""")

print("""
CASE 2: THE MORPH FLAG PROBLEM
-------------------------------
Currently: morph_flag per occurrence is stored as sparse entries.
  20 morphed words × 3 bytes each = 60 bytes.

Visual encoding alternative:
  The RENDERED symbol for "walking" looks slightly different from "walk":
  - Different opacity (walk=100%, walking=70%)
  - Different stroke (walk=solid, walking=dashed)

  The scanner sees the visual difference and knows the morph form.
  The morph form is encoded in the VISUAL PROPERTY of the symbol.

  But the visual property must be SPECIFIED per occurrence in the stored data.
  "render this symbol at 70% opacity" = you need to store "70%" somewhere.
  That IS the morph flag. Same cost.

  UNLESS: the morph flag is encoded in the WORD_ID itself.
  If "walk" = word_id 150 and "walking" = word_id 151,
  then the morph form is implicit in the word_id. No extra flag.
  The visual layer just renders 150 and 151 differently.

  This is the UNIFIED SYMBOL CODE idea from earlier.
  "walk" and "walking" get DIFFERENT word_ids.
  The template says id 150 = walk, id 151 = walking.
  Morph flag is IMPLICIT in the id. Zero extra bytes.

  BUT: this means "walking" can't share positions with "walk"
  in the inverted index (they're different ids).
  Trade-off: save morph_flag bytes, lose position merging benefit.

  For 20 morphed words: save 60 bytes of morph_flags,
  but lose ~40 bytes of position merging savings.
  Net: ~20 bytes saved.
""")

print("""
CASE 3: THE OCCURRENCE COUNT PROBLEM
-------------------------------------
Currently: we store a count byte per word (1 byte).
  244 words × 1 byte = 244 bytes.

Visual encoding alternative:
  The scanner counts how many times a symbol appears in the stream.
  The count is IMPLICIT from the sequence. No count byte needed!

  In the inverted index format: the count is derivable from the
  position data length. If there are 3 positions, count = 3.
  We already derive it. No count byte stored.

  BUT in the new bit-packed format, we DO store a count byte so
  the decoder knows how many 11-bit values to read.

  Can we eliminate it? YES — if positions are self-terminating.
  Use a delimiter or length-prefix at the word table level instead
  of per-word. Or: fixed-size entries (pad to max).
  Or: the word_table_len in the header tells total size,
  and each entry is parsed until the table ends.

  Actually, we NEED the count to know how many positions to read.
  Unless we use a different encoding...

  WHAT IF: we use the COORDINATE TEMPLATE system instead of raw positions?
  Template codes are FIXED SIZE (1-2 bytes per dimension).
  The decoder knows the size from the template tier.
  No count needed!

  This is what the existing system does. Template codes are self-describing.
  The tier (inferred from byte length) tells you everything.

  SAVINGS: eliminate the count byte = 244 bytes saved. Significant!
""")

print("""
CASE 4: THE CAPS/PUNCT OVERHEAD
--------------------------------
Currently:
  Caps bitmap: ceil(2500/8) = 313 bytes
  Punct table: ~150 bytes
  Total structural metadata: ~463 bytes

Visual encoding:
  Capitalization = rendered as UPPERCASE glyph variant.
  Punctuation = rendered as attached marks on the glyph.

  The scanner sees uppercase rendering = capitalized.
  The scanner sees a period attached to glyph = trailing period.

  But these visual properties must be encoded in the stored data.
  "Render this glyph as uppercase" = 1 bit. That IS the caps bitmap.
  "Attach a period" = that IS the punct table.

  UNLESS: we merge punct/caps into the word_id.
  "The" (capitalized) = different word_id from "the" (lowercase).
  "dog." (with period) = different word_id from "dog" (no period).

  This MULTIPLIES the dictionary size:
  249,777 × 2 (caps variants) × ~5 (punct variants) = 2.5 million ids.
  Still fits in 3 bytes. But now EVERY token carries its own caps/punct
  implicitly. No bitmap or punct table needed!

  SAVINGS: 463 bytes eliminated entirely.
  COST: word_ids become slightly larger on average (more entries = more
  3-byte ids instead of 2-byte). Maybe +100 bytes.
  NET SAVINGS: ~363 bytes.
""")

print("""
CASE 5: THE BLANK METADATA OVERHEAD
-------------------------------------
Currently:
  line_word_counts: ~25-100 bytes
  constraint markers: ~3-5 bytes per blank
  gap_assignment: 1 byte per gap

Visual encoding:
  line_word_counts is derivable if the grid is stored SEQUENTIALLY.
  If the document is a stream of word marks in grid order,
  then line breaks are at fixed intervals (every ~13 words for 80-char lines).
  The scanner counts marks per line. No line_word_counts needed.

  BUT: the stream is not sequential in the inverted index format.
  In inverted index, words are grouped by identity, not by position.

  WHAT IF: we switch to sequential for the base stream, and use
  the inverted index ONLY for blanked words?

  Sequential stream: [word_id][word_id][word_id]...[BLANK]...[word_id]
  Each position = its index in the stream. Free.
  Line breaks = every N words where N = words per line. Known from 80-char bin.

  Blanked positions = gaps in the stream (marked or inferred).

  For 2500 tokens: 2500 × 1.3 bytes avg = 3,250 bytes.
  But with blanking 220 tokens: 2280 × 1.3 = 2,964 bytes + 50 blank metadata.

  vs inverted index: ~1,550 bytes.

  Sequential is WORSE when there's lots of word repetition.
  Sequential is BETTER when there's lots of unique words.
""")

print("=" * 70)
print("CONCRETE SAVINGS FROM VISUAL/IMPLICIT ENCODING")
print("=" * 70)
print("""
Savings that are REAL and BUILDABLE:

1. Eliminate count byte (use self-describing templates): ~244 bytes
2. Eliminate gap_assignment via positional rules:        ~170 bytes
3. Merge caps/punct into word_id:                        ~363 bytes
4. Eliminate position length headers (bit-packing):      ~920 bytes

TOTAL RECOVERABLE: ~1,697 bytes

Current Article x10: 7,020 bytes
After these optimizations: ~5,323 bytes
After blanking improvements: ~4,500 bytes
RATIO: ~3.3:1

These are ALL "free info" techniques — making information IMPLICIT
rather than EXPLICIT. The visual layer is the same principle applied
to rendering: make visual properties carry implicit meaning defined
by templates, so the scanner extracts info without extra bytes.

The visual layer doesn't add compression beyond what implicit encoding
does at the byte level. But it makes the compressed output SCANNABLE
and HUMAN-READABLE, which is unique and valuable for the Hive use case.
""")
