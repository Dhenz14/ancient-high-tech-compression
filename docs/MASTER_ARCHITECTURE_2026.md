# Ancient High-Tech Compression System — Master Architecture 2026

## Philosophy

**Ancient/High-Tech**: Store only tiny codes on-chain. All intelligence lives in
pre-computed templates on the Hive blockchain. The decoder reconstructs everything
deterministically from codes + templates with zero ambiguity. Symbols are
meaningless marks — templates contain ALL intelligence.

```
Raw Text (50,000 words)
    ↓
Convert to 1-char symbols (ping Hive master dictionary)
    ↓
Arrange symbols in 80-char wide bin (SVO row structure)
    ↓
Blank system removes recoverable words
    ↓
Encode remaining symbols + blank markers + checksum
    ↓
5KB payload → Hive Custom JSON (per document)

Reconstruction:
    ↓
Decode payload → symbols + blank markers
    ↓
Recover blanked words (checksum + row type + Venn constraints)
    ↓
Reconstruct word order from grid positions
    ↓
Lookup symbols → words (ping Hive master dictionary)
    ↓
100% exact original text
```

---

## The Formula

Every word in the master dictionary has:

```
word = symbol + number + type + form
```

| Field  | What it is                        | Stored where        |
|--------|-----------------------------------|---------------------|
| symbol | 1-character visual marker         | Hive dictionary template (one-time) |
| number | frequency rank (1-249,777)        | Hive dictionary template (one-time) |
| type   | POS / supersense category (400+)  | Hive dictionary template (one-time) |
| form   | morphological form (base/past/ing)| Hive dictionary template (one-time) |

The dictionary is stored on Hive ONCE. It costs nothing per document.
Every document just references it.

---

## The Grid — Battleship Architecture

### The 80-Character Bin

Text is wrapped into lines of exactly 80 characters. Each word becomes a
1-character symbol, so a line holds up to 80 word-symbols. This creates a
fixed-width grid where every position has exact coordinates.

```
Line 1: [sym][sym][sym][sym][sym][sym][sym]...  (up to 80 symbols)
Line 2: [sym][sym][sym][sym][sym][sym]...
Line 3: [sym][sym][sym][sym]...
...
```

### SVO Row Structure — Free Intel from Vertical Position

**Key insight**: Rows are structured like English sentences. Each row follows
Subject-Verb-Object (SVO) order, repeating until the line is full:

```
Row pattern: [noun][verb][noun][adj][noun][verb][noun]...
             S      V     O         S      V     O
```

This means **vertical position tells you the word type FOR FREE**. When a word
is blanked, its row position reveals what POS category it belongs to (noun,
verb, adjective, etc.) without storing that information explicitly.

The row template is stored on Hive once. The decoder knows:
- Position 0 in pattern = noun (subject)
- Position 1 = verb
- Position 2 = noun (object)
- etc.

### Dual-Dimension Coordinates

Each word's position is encoded as two independent coordinates:
- **Vertical**: which line (1-100) — encoded via position templates
- **Horizontal**: which slot within the line (0-79) — encoded via position templates

Both dimensions use the same 8,946 pre-computed template system:

| Tier | Size    | Templates | Coverage                      |
|------|---------|-----------|-------------------------------|
| 0A   | 1 byte  | 16        | Ultra-common single positions |
| 0B   | 1 byte  | 94        | Common 1-2 position patterns  |
| 1    | 2 bytes | 8,836     | 3-position patterns           |
| 2    | variable| unlimited | Delta encoding (any pattern)  |

**Tier-marker-free**: No tier marker bytes. Tier inferred from byte-length.
Zero redundancy — every byte earns its place.

Total capacity: 8,946 × 8,946 = 80+ million unique position combinations.

---

## The Blank System — The Compression Engine

### How It Works

The blank system removes words from the grid that can be mathematically recovered.
When a word is blanked:

1. **Its entry is removed** from the word table (saves word_id + all position data)
2. **A small constraint marker** is stored instead (3-5 bytes per blanked word)
3. **Gap positions** are detectable by the decoder (it knows how many words per line)

### What the Decoder Knows About a Blanked Word

When encountering a gap in the grid, the decoder has multiple signals:

| Signal | Source | Narrows candidates |
|--------|--------|-------------------|
| **Row position** | SVO template on Hive | Tells you POS (noun/verb/adj) |
| **Checksum deficit** | Stored per-partition | Uniquely identifies the rank |
| **Word length** | Visible from bin structure | Eliminates ~90% of candidates |
| **Supersense** | 400+ categories in template | Eliminates ~95% of candidates |
| **Morphological form** | Stored in constraint marker | base/past/ing/plural |
| **16-bit constraint pattern** | Syllables, vowel clusters, etc. | 40-70% elimination |
| **Sentence context** | Surrounding words' POS flow | Grammatical coherence |

### The Venn Diagram — Constraint Intersection

Each signal is a circle in a Venn diagram. The intersection narrows to exactly
one word:

```
Universe: 249,777 words
  → POS = verb (~30,000 words)
    → length = 4 chars (~3,000 words)
      → supersense = verb.motion (~200 words)
        → checksum deficit = rank 847 → "walk" ✓ (exactly 1 word)
```

### POS-Partitioned Checksums

Instead of one checksum for the whole document, partition by POS category:

```
noun_checksum = sum(ranks of all nouns)
verb_checksum = sum(ranks of all verbs)
adj_checksum  = sum(ranks of all adjectives)
...
```

When 5 verbs are blanked:
- verb_checksum = stored value
- sum of remaining known verbs = calculated
- deficit = verb_checksum - known_sum
- The 5 missing verbs' ranks must sum to deficit
- Combined with position, length, and supersense signals → unique solution

### Gap Detection

The decoder knows the complete grid structure:
- **line_word_counts**: how many words on each line (stored in blob, 1 byte per line)
- **claimed positions**: all positions from non-blanked word entries
- **gaps** = total positions - claimed positions = where blanked words go

---

## Symbol System — Two Layers

The system has TWO encoding layers that serve different purposes:

### Layer 1: Byte-Level Encoding (Compression Pipeline)

For the binary compressed blob, words are identified by frequency rank using
variable-length encoding. This is the storage-optimal representation:

```
Rank 1-127:          1 byte   0xxxxxxx       (top ~55% of text tokens)
Rank 128-16,511:     2 bytes  10xxxxxx xxxxxxxx  (next ~37% of tokens)
Rank 16,512-249,777: 3 bytes  11xxxxxx xxxxxxxx xxxxxxxx  (rare words)
Unknown words:       0x00 + length + UTF-8    (not in dictionary)
```

### Layer 2: Visual Symbol Encoding (Presentation / Scanner Layer)

On Hive and in rendered output, each word maps to a **visual symbol** — a
custom glyph whose visual properties ARE data channels. A scanner (AI or
algorithmic) reads the rendered symbol and extracts multiple dimensions
of information simultaneously:

```
One rendered super symbol encodes:
  ┌─────────────────────────────────────────────────┐
  │  SHAPE (which glyph)    → word family identity  │
  │  OPACITY layer 1        → morphological form    │
  │  OPACITY layer 2        → POS category          │
  │  INTERNAL LINES/MARKS   → word count inside     │
  │  TILT / ROTATION        → sequence position     │
  │  SIZE                   → word length hint       │
  └─────────────────────────────────────────────────┘
```

**Key insight**: Visual properties are FREE data channels. The byte cost of
storing a symbol code is fixed (1-3 bytes), but the RENDERED symbol carries
5+ dimensions of information. Every visual property encodes data that would
otherwise cost additional bytes.

**The font IS the template**: A custom font file stored on Hive defines how
each glyph looks. The visual properties baked into each glyph ARE the
metadata. No separate metadata bytes needed — the rendering itself is the data.

### Complete Visual Data Channel Inventory

Every visual property = free information. A template on Hive defines
what each value means. The document stores only the code; the scanner
reads the rendered result.

```
VISUAL CHANNEL          WHAT IT ENCODES              TEMPLATE ON HIVE
─────────────────────────────────────────────────────────────────────
Shape (glyph identity)  Word family                  Glyph → word mapping
Opacity                 Morphological form           Opacity level → suffix/prefix
Thickness               POS category                 Thickness → noun/verb/adj/etc
Size                    Word length bucket           Size → 1-4 / 5-8 / 9+ chars
Rotation / tilt         Sequence position data       Angle → position offset
Color / shade           Supersense category          Shade → 400+ categories
Internal micro-lines    OCCURRENCE POSITIONS         Each line = one occurrence
  - line Y position     → vertical grid coordinate   Y offset → line number
  - line X position     → horizontal grid coordinate X offset → word slot
  - line thickness      → confidence / frequency     Thick = high freq
  - line length         → word length at that pos    Length → char count
  - line spacing        → gap to next occurrence     Gap → delta position
Dots / marks            Occurrence count             N dots = N occurrences
Layer count             Super symbol type            1 layer = TYPE 1, etc.
```

### The Micro-Barcode: How Super Symbols Encode Positions

This is the core innovation. A super symbol for a word that appears 100
times contains 100 micro-lines, each encoding WHERE that occurrence goes:

```
Word "the" → super symbol glyph ◆ with 100 micro-lines:

  ◆ ┌──────────────────────────────────────┐
    │ ╎    ╎╎   ╎  ╎╎╎    ╎   ╎  ╎╎      │  ← 100 micro-lines
    │ each micro-line encodes:             │
    │                                      │
    │   Y position of line = which row     │  (line 1, line 5, line 12...)
    │   X position of line = which column  │  (slot 0, slot 3, slot 7...)
    │   thickness = frequency tier         │  (how common at this position)
    │   length = word length hint          │  (confirms "the" = 3 chars)
    │                                      │
    └──────────────────────────────────────┘

Scanner reads: "100 occurrences of 'the' at positions:
  (1,0), (1,6), (2,3), (3,1), (3,8), (4,0), (4,5)..."
```

**Storage cost**: 1 glyph reference code (2-3 bytes)
**Information extracted**: word identity + 100 exact grid positions
**Without micro-barcode**: would need word_id + 200 bytes of position data

The glyph template containing the micro-line pattern is stored on Hive
ONCE. Every document referencing "the" points to the same glyph template
and only stores which subset of the 100 positions apply to THIS document.

### Three Architectural Layers (from production_scanner.py)

```
STORAGE LAYER:  1 symbol code (2-3 bytes in blob)
                Zero overhead. Just a pointer.

VISUAL LAYER:   Rendered glyph with micro-lines, opacity, thickness, etc.
                AI scanner extracts: positions, morph form, POS, count
                Zero storage — exists only when rendered

TEMPLATE LAYER: Font file + micro-line templates on Hive
                Mathematical formulas (article-agnostic)
                Deterministic reconstruction
                Stored once, referenced forever
```

### Unified Symbol Codes (Future)

The ultimate goal: a single code point that encodes word identity + morph form
+ POS simultaneously. Instead of separate fields:

```
Current:  [word_id: 1-3 bytes] + [morph_flag: 1 byte]  = 2-4 bytes per token
Unified:  [symbol_code: 2-3 bytes]                      = 2-3 bytes per token
          (encodes word + morph + POS in one code)
```

With 249,777 words × ~5 morph forms = ~500K real combinations.
Fits in 2.5 bytes average with variable-length prefix-free encoding.

The Hive template maps each symbol_code to its visual glyph AND its
decoding properties (word, morph, POS). Stored once, referenced forever.

### Symbol Assignment Policy

Symbols are assigned by frequency tier and NEVER change:
- **Tier 1** (top 10 words): premium single-char symbols
- **Tier 2** (top 100): alphanumeric characters
- **Tier 3** (top 300): extended ASCII
- **Tier 4** (remaining): Unicode mathematical operators / custom glyphs

Once assigned, a word's symbol is permanent across all documents.

---

## Super Symbol System (4 Types)

Super symbols consolidate multiple words into a single symbol. Each super
symbol is a **multi-dimensional visual object** — its shape, opacity layers,
internal marks, and rotation ALL carry data that a scanner can read.

| Type | What it does | Example | Visual property |
|------|-------------|---------|-----------------|
| TYPE 1 | Repeated words → 1 symbol | "the the the" → ◆ | Internal lines = count |
| TYPE 2 | Morphological variants → 1 family | run/runs/running/ran → ◇ | Opacity = which form |
| TYPE 3 | Fixed phrases → 1 symbol | "in my opinion" → ◈ | Marks = word count |
| TYPE 4 | Contractions → component symbols | "can't" → ["can", "not"] | Size = component count |

### How Super Symbols Pack Data Into Visual Properties

A TYPE 2 super symbol for the "walk" family:

```
Glyph: ◇ (base shape = "walk" word family)

When rendered at opacity 1.0  → scanner reads: "walk" (base form)
When rendered at opacity 0.70 → scanner reads: "walking" (-ing)
When rendered at opacity 0.60 → scanner reads: "walked" (-ed)
When rendered at opacity 0.50 → scanner reads: "walks" (-s)
When rendered at opacity 0.40 → scanner reads: "walker" (-er)
```

The font template on Hive defines what each opacity level means.
The document stores just the glyph code + opacity value.
The scanner reads the VISUAL RESULT and decodes both word identity
AND morphological form from a single rendered symbol.

**Sequence is free**: The order symbols appear in the grid encodes word
order — no extra bytes needed for position within the sequence.

**Visual properties are free**: Opacity, rotation, internal marks, and
size encode metadata — no extra bytes needed for morph/POS/count info.

The game is: **how many data channels can we pack into a single symbol's
visual rendering, backed by templates stored once on Hive?**

### Super Symbol Jobs (Three-Job Architecture)

Each super symbol has three responsibilities:

1. **Job 1: Multi-instance condensation** — Collapse 2+ word instances into 1 symbol
2. **Job 2: Tilt removal guidance** — Guide removal of OTHER symbols' coordinates
3. **Job 3: Backup intelligence guidance** — Provide row/width intel for backup blanks

### Backup Blank Assignment

Super symbols are assigned backup blanks in appearance order:
- First super symbol appearing → gets first backup blank
- Hardcoded correspondence: appearance_N → backup_N
- Same row requirement with size intelligence

---

## Morphological Compression

438 morphological patterns with 467 opacity levels (0.0015 precision):

| Process | Patterns | Opacity | Example |
|---------|----------|---------|---------|
| Base form | — | 1.0 | "run" |
| Prefix | 100+ | 0.8 | "un-" + "happy" |
| Suffix | 210+ | 0.7 | "happi" + "-ness" |
| Ablaut | 60+ | 0.6 | sing/sang/sung |
| Umlaut | 35+ | 0.5 | foot/feet |
| Consonant alternation | 25+ | 0.4 | live/lives |
| Infixation | 8+ | 0.35 | complex insertions |
| Simultaneous affixation | variable | 0.32 | "un-" + "happi" + "-ness" |

The opacity value encodes which morphological transformation was applied,
allowing the decoder to reconstruct the exact inflected form from the base.

---

## Checksum System — 426-Layer Validation

### Outstanding Numbers Integration

The frequency rank of each word serves as its "outstanding number" — a
visual indicator of how important the word is and whether it should be
blanked or kept:

```
Rank 1-127       (1-byte word_id):  ALWAYS KEEP — cheap to store, never blank
Rank 128-16,511  (2-byte word_id):  BLANK IF HIGH OCCURRENCE — moderate storage
Rank 16,512+     (3-byte word_id):  BLANK AGGRESSIVELY — expensive to store
```

The blank selector naturally prioritizes by byte savings, which aligns
with the outstanding numbers strategy: expensive words (high rank, many
positions) get blanked first, cheap words (low rank, few positions) stay.

### Tier 1: Total Checksum
Sum of frequency ranks of all words in the document (or partition).

### Tier 2: POS Checksums (10 categories)
noun, verb, adjective, adverb, pronoun, preposition, conjunction,
interjection, determiner, number — each with its own sub-checksum.

### Tier 3: Supersense Checksums (400+ categories)
Fine-grained semantic categories:
- Nouns: 26 base + 54 animal taxonomy + 8 extended
- Verbs: 16 base + 6 extended
- Adjectives: 32 GermaNet-based categories
- Adverbs: 9 categories
- Spatial: 6 categories
- Temporal: 5 categories
- Participant roles: 7 categories
- Circumstantial: 7 categories
- Relational: 7 categories
- Quantitative: 5 categories

Each supersense category maintains its own checksum. The intersection of
category + checksum deficit uniquely identifies a word.

---

## 16-Bit Constraint Intelligence

16 binary features per word for Venn diagram candidate elimination:

1. Syllable count
2. Vowel clusters (yes/no)
3. Repeated letters (yes/no)
4. Silent letters (yes/no)
5. Top 2000 frequency (yes/no)
6. Age of acquisition (scaled)
7. POS category
8. Phonetic complexity
9. Morphological family size
10. Character length
11. Vowel count
12. Consonant cluster (yes/no)
13. Double letter presence (yes/no)
14. Common prefix indicator (yes/no)
15. Common suffix indicator (yes/no)
16. Rare word flag (yes/no)

These 16 bits create 65,536 unique patterns. When reconstructing a blanked
word, matching the 16-bit pattern eliminates 40-70% of candidates before
other constraints are applied.

---

## Three-Phase Blank System

### Phase 1: Super Symbol Vertical Placement
- Super symbols placed with three-job architecture
- Multi-instance condensation: 2+ words → 1 symbol
- Tilt removal: guide removal of other symbols
- Backup intelligence: provide row/width intel for backup blanks

### Phase 2: 465×465 Semantic Grid
- Individual words placed on semantic grid
- 16-bit constraint intelligence applied for candidate elimination
- Outstanding numbers system for visual disambiguation
- Spillover grid (465×465 → 1500×1500) for large documents

### Phase 3: Eye-for-Eye Shrinking
- Shrink from both ends of the grid
- Final optimization with temporary cache
- Zero overhead: all temporary data deleted after use

---

## Pipeline

```
Text → [Extract] → [Bin 80-char] → [Scan] → [Blank] → [Store] → [Reconstruct]
                                      ↓
                           5-Phase Scanner:
                           Phase 1: Fixed sentences (TYPE 3)
                           Phase 2: Word forms (TYPE 2)
                           Phase 3: Contractions (TYPE 4)
                           Phase 4: Repeated words (TYPE 1)
                           Phase 5: Single words (TYPE 0)
```

---

## What's Built and Working (March 2026)

### Two Compression Approaches (both working, preserved side by side)

**Approach A: Inverted Index Pipeline** (`src/pipeline/`)
- Stores each unique word once with coordinate-encoded positions
- Multi-blank system removes high-frequency words, recovers via checksum
- Best for: documents where the blank system can be aggressive
- Current: 2.1:1 on Article x10

**Approach B: Sequential Rank Stream v3** (`src/sequential/`) — THE BREAKTHROUGH
- Stores words sequentially as merged varints: `rank * 32 + variant`
- Position is FREE (implied by stream order)
- Caps + trailing punct encoded in 5-bit variant (top 3 words = 1 byte each)
- ALL CAPS, mixed case, leading punct, unknown words → extra section with original casing
- brotli applied as stage 2 for byte-level compression
- **Beats brotli standalone on diverse text**
- Current: 30.0:1 on Article x10, **2.7:1 on blog posts (beats brotli's 2.4:1)**

### All Modules

| Module | File | Status |
|--------|------|--------|
| Tokenizer | `src/tokenizer/` | 80-char grid, punct/caps extraction |
| Word ID Codec | `src/wordid/word_id_codec.py` | Variable-length 1-3 byte encoding |
| Dictionary | `src/wordid/dictionary.py` | 249,777 words from NLTK corpus |
| Inverted Index | `src/inverted_index/` | Battleship grid builder + reader |
| Coordinate Encoding | `src/coordinate_encoding/` | 8,946 templates, 4 tiers (legacy) |
| Morphology | `src/morphology/` | Lemmatizer + inflector, 100+ irregular forms |
| Blank System | `src/blanks/` | Multi-blank with gap detection + constraints |
| Serializer | `src/serializer/` | Binary blob format + bitpacking |
| Pipeline (Approach A) | `src/pipeline/` | Inverted index compressor/decompressor |
| **Sequential (Approach B)** | **`src/sequential/`** | **Two-stage: rank stream + brotli** |

### Test Results

- **176 tests passing** (82 sequential + 94 pipeline)
- **100% lossless reconstruction** on all natural text including contractions, ALL CAPS, mixed case, leading/trailing punct, unicode
- Two approaches benchmarked against world's best compressors

### Compression Performance vs World's Best

**Approach B v3 (Sequential + brotli) vs standalone compressors:**

| Text | Raw | brotli | gzip | **Ours** | Result |
|------|-----|--------|------|----------|--------|
| Article x1 | 1,499 | 477 | 777 | **486** | Close (3.1:1 vs 3.1:1) |
| Article x5 | 7,499 | 482 | 839 | **500** | Close (15.0:1 vs 15.6:1) |
| Article x10 | 14,999 | 482 | 897 | **500** | Close (30.0:1 vs 31.1:1) |
| Blog post | 781 | 325 | 437 | **291** | **WE WIN** (2.7:1 vs 2.4:1) |
| Mixed text | 2,281 | 757 | 1,140 | **718** | **WE WIN** (3.2:1 vs 3.0:1) |

**We beat brotli on diverse text. We're within 2-4% on repetitive text.**
And our dictionary is on Hive (free), theirs is embedded per-file.

---

## What's Next — Remaining Ideas to Implement

### Immediate: Approach B Optimizations (v3 is stable, 176 tests passing)
- ~~Fix complex punctuation handling~~ DONE (16 trailing codes, leading punct via extra section)
- ~~Add contraction support~~ DONE (apostrophe mid-word never stripped)
- ~~Write comprehensive test suite~~ DONE (82 sequential tests: contractions, ALL CAPS, mixed case, unicode, dialogue, etc.)
- AI-optimized rank assignment: co-occurring words get adjacent IDs → better brotli compression
- Add phrase detection to sequential encoder (common bigrams/trigrams as single tokens)
- Benchmark on 100+ diverse text samples

### Ideas in the Legacy Pipeline (return to later)
These ideas are built/partially built in the inverted index pipeline.
They may apply to the sequential approach too:

- **POS-Partitioned Checksums**: enables aggressive multi-blank
- **16-Bit Constraint Intelligence**: Venn diagram candidate elimination
- **SVO Row Structure**: free POS from vertical position (needs validation)
- **Super Symbol Types 1-4**: word family merging, phrases, contractions
- **Morphological Opacity**: visual encoding of morph forms
- **Three-Phase Blank System**: super symbols → grid → eye-for-eye
- **Spillover Grid**: 465×465 → 1500×1500 for large documents
- **Outstanding Numbers**: frequency-tier blanking heuristic
- **Micro-Dot Visual Encoding**: scanner-readable position barcodes

### AI-Enhanced Compression (Future)
- **AI-optimized rank assignment**: train a model to assign word IDs that
  produce the most compressible byte patterns for brotli's stage 2
- **AI scanner**: reads rendered visual symbols and extracts multi-dimensional
  data (word identity, morph form, positions) from visual properties
- **AI-guided blanking**: ML model predicts which words can be safely
  blanked and recovered, optimizing the blank/keep boundary
- **Learned compression models**: neural network trained on English text
  to predict next-word probabilities, enabling arithmetic coding that
  beats entropy-only approaches

### Hive Blockchain Integration
- Deploy dictionary as Hive template (one-time upload)
- Per-document: compressed blob as custom_json
- Client-side reconstruction with IndexedDB template caching
- Target: 5KB per document (achieved on repetitive text, close on diverse)

---

## Hive Blockchain Template Structure

Templates stored ONCE on Hive (free forever after initial deployment):

| Template | Content | Size |
|----------|---------|------|
| Master Dictionary | word → symbol + rank + POS + supersense | ~10 MB |
| Position Templates | 8,946 coordinate patterns (horiz + vert) | ~1 MB |
| Row Structure | SVO pattern definition per row | ~1 KB |
| Morphological Rules | Base → inflection transformation rules | ~50 KB |
| Contraction Map | 36 contraction → component mappings | ~1 KB |
| Fixed Phrases | Common 3-4 word phrase → symbol map | ~100 KB |
| 16-Bit Features | Word → 16-bit constraint pattern | ~500 KB |

**Total one-time cost**: ~12 MB on Hive
**Per-document cost**: target 5 KB

---

## Core Principles (Non-Negotiable)

1. **Zero Overhead**: Every byte must earn its place. No redundant metadata.
2. **Template Dependency**: Symbols are meaningless marks. Templates hold ALL intelligence.
3. **Tier-Marker-Free**: Tier inferred from byte-length, never stored explicitly.
4. **100% Reconstruction**: Lossless, deterministic, word-for-word reconstruction guaranteed.
5. **Dictionary Permanence**: The 249,777-word dictionary is permanent. Never truncate or purge.
6. **Military-Grade Protection**: Overhead injection is impossible. Violations are blocked, not worked around.
7. **Blockchain as Shared Memory**: Templates deployed once, referenced forever, cost amortized to zero.

---

## Original Documentation

The following original documents contain detailed implementation notes and
should be preserved for reference. Each contains ideas that informed this
master document:

| File | Contains |
|------|----------|
| `docs/COORDINATE_ENCODING_TIER_MARKER_FREE_ARCHITECTURE.md` | Tier-marker-free design philosophy, byte-efficiency analysis |
| `docs/TEMPLATE_SYSTEM_DEEP_DIVE.md` | How 8,946 templates cover 95%+ of patterns |
| `docs/COORDINATE_ENCODING_EMPIRICAL_PERFORMANCE.md` | Benchmarks, tier distribution, validation guards |
| `replit.md` | Full system architecture reference, all policies |
| `.cursorrules` | Critical rules, grid dimensions, super symbol types |
| `README.md` | Project overview and structure |
