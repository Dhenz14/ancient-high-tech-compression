# Blueprint Roadmap — Build Order & Phase Gates

## Current Baseline (March 17, 2026)

- **189 tests passing**, 100% lossless round-trip
- **249,777 word dictionary** (NLTK Brown + Gutenberg + WordNet)
- **Two working approaches** preserved side by side
- **BREAKTHROUGH**: Two-stage sequential v3 beats brotli on diverse text

### Approach A: Inverted Index (`src/pipeline/`)

- 2.1:1 on Article x10 (inverted index + blank system + coordinate encoding)
- Rich feature set: morphology, blanking, bitpacking, checksum recovery
- Many untapped ideas in the legacy codebase for future improvement

### Approach B: Sequential Rank Stream v3 (`src/sequential/`) — CURRENT BEST

- **30.8:1 on Article x10** (merged varint ranks + brotli stage 2)
- **Beats brotli standalone on Article x1 (471 vs 477 bytes, +1.3%)**
- **Beats brotli standalone on blog posts (285 vs 325 bytes, +12.3%)**
- **Beats brotli standalone on mixed text (694 vs 757 bytes, +8.3%)**
- **Within 1% of brotli on repeated articles**
- AI-optimized rank assignment: Brown re-rank + simulated annealing (+2.8% vs frequency-only)
- v3 format: merged varint (rank*32+variant), extra section for ALL CAPS/mixed/leading/unknown
- 95 dedicated tests: contractions, ALL CAPS, mixed case, leading/trailing punct, unicode, dialogue, rank optimizer
- Simpler architecture, massive compression, 100% lossless

### Target

- Beat brotli consistently across all text types
- 20:1+ on repetitive content, 3:1+ on diverse content
- Dictionary on Hive = zero per-document overhead (automatic advantage)

---

## Idea Audit Summary

| # | Idea | Verdict | Why |
|---|------|---------|-----|
| 1 | SVO Row Template | **REVISIT** | Row position can't encode POS reliably (bin wraps by char count, not grammar). BUT the concept of "free intel from structure" is valid — see Idea 11. |
| 2 | POS-Partitioned Checksums | **BUILD** | Enables blanking multiple words per POS category. Checksum deficit + word_length + first_char narrows to unique word. Large compression gain. |
| 3 | 1-Character Symbol Mapping (standalone) | **EVOLVED** | Plain Unicode symbols are larger than word IDs. But UNIFIED symbol codes (word + morph + POS in one code) save bytes. See Idea 11. |
| 4 | 16-Bit Constraint Features | **CONDITIONAL** | Only build if POS checksums (Idea 2) produce non-unique solutions. Don't build speculatively. |
| 5a | Super Symbols TYPE 1 (repeated) | **SKIP** | Already covered by inverted index (word stored once, positions separate). |
| 5b | Super Symbols TYPE 2 (word families) | **BUILD** | Merge morphological variants into single inverted index entries. Combined position list hits better templates. Real compression win beyond what lemmatizer alone does. |
| 5c | Super Symbols TYPE 3 (phrases) | **BUILD** | Common phrases ("in order to") as single tokens. Reduces token count 5-15%. |
| 5d | Super Symbols TYPE 4 (contractions) | **BUILD** | "can't"/"don't" stored as unknowns today. Adding to dictionary saves 5-15 bytes each. |
| 6 | Three-Phase Blank System | **DEFER** | Current single-phase works. Optimize after POS checksums are measured. |
| 7 | Morph Opacity (467 levels as floats) | **EVOLVED** | Float opacity is too expensive for bytes. BUT the concept lives on as 1-byte morph_flags in the compression layer, and as visual opacity in the scanner/rendering layer. Two layers, one concept. |
| 8 | Grid Scaling (spillover) | **BUILD** | Needed for real documents >1,600 words. Header needs uint32 fields. |
| 9 | Outstanding Numbers | **SKIP** | Debugging/visualization tool. Adds bytes, doesn't save them. |
| 10 | Hive Integration | **BUILD LAST** | Deployment target. All compression must be optimized first. |
| 11 | **Visual Super Symbol Encoding (NEW)** | **BUILD** | Custom font/glyph system where visual properties (opacity, marks, rotation) are data channels. Scanner reads rendered symbols to extract word + morph + POS. Template = font file on Hive. |
| 12 | **Unified Symbol Codes (NEW)** | **BUILD** | Single code point encodes word + morph + POS. Replaces separate word_id + morph_flag. Saves 0.5-1 byte per token. |
| 13 | **Word Family Merging (NEW)** | **BUILD** | Merge all morphological variants into one inverted index entry with per-occurrence morph flags. Fewer entries = better coordinate template hits. |

### Key Evolution: Two-Layer Architecture

The audit revealed that several "skipped" ideas were right in concept but
wrong in implementation approach. The solution is a **two-layer architecture**:

```
Layer 1 — Compression (bytes):  word_id + morph_flag (optimal for storage)
Layer 2 — Presentation (visual): rendered glyphs with opacity/marks/rotation
                                  (optimal for scanning and human reading)
```

Both layers reference the SAME Hive templates. The compression layer produces
minimal bytes. The presentation layer renders those bytes as rich visual
symbols that encode the same data in visual properties. A scanner can read
either layer.

---

## Phase 0: Foundation Cleanup — COMPLETED

### Status: DONE (March 17, 2026)

Completed via Approach B (Sequential Rank Stream v3):

- **0.2 Contractions**: DONE — apostrophe mid-word never stripped. "don't", "can't",
  "they're" all round-trip perfectly. Contractions in the 249K dictionary get efficient
  rank encoding; others stored as unknown words with original casing.
- **0.3 Tokenizer fix**: DONE — new tokenizer in `src/sequential/encoder.py` handles
  all edge cases. 82 dedicated tests cover contractions, ALL CAPS, mixed case,
  leading/trailing punct, unicode, possessives, dialogue, abbreviations.
- **ALL CAPS support**: DONE — "NASA", "FBI", "THE" stored in extra section with
  original casing. Was silently title-cased in v2 (bug).
- **Mixed case support**: DONE — "iPhone", "McDonald's" preserved via extra section.
- **Leading punct**: DONE — `"hello`, `(test)` correctly encoded via extra section.
- **Multi-char trailing**: DONE — `."` `,"` `!"` `?"` encoded as single codes (13-15).

### Gate Tests: ALL PASSING

```text
[x] All 189 tests pass (94 pipeline + 95 sequential)
[x] round-trip with "I can't believe they won't do it" → exact match
[x] "don't" round-trips correctly (contraction preserved)
[x] ALL CAPS: "NASA" → "NASA" (not "Nasa")
[x] Mixed case: "iPhone" → "iPhone"
[x] Dialogue: 'She said "Hello."' → exact match
[x] Unicode: "café naïve résumés" → exact match
[x] Benchmark: 2.3% improvement over v2 across all test cases
```

### Items deferred to later phases (Approach A specific)

- 0.1: Activate dead constraint verification in `src/blanks/constraint_checker.py`
- 0.4: Word family merging for inverted index (Approach A only)

---

## Phase 1: Phrase Dictionary (TYPE 3 Super Symbols)

### Goal
Detect common multi-word phrases and compress them as single tokens.

### What to Build

**1.1: Phrase dictionary**
A frozen list of 500-2,000 common English phrases ranked by frequency.
Sources: Google n-grams, Brown corpus bigrams/trigrams.
Phrases stored in `dictionary_cache.json` with dedicated rank range.

Format: `"in order to": rank_X, "as well as": rank_Y, ...`

**1.2: Phrase detection in tokenizer**
Before splitting text into words, scan for known phrases (longest match first).
Replace matched phrases with single tokens.

Example: "in order to understand" → ["in_order_to", "understand"]

Files: `src/tokenizer/tokenizer.py`

**1.3: Phrase-aware detokenizer**
On decompression, phrase tokens expand back to their component words.

Files: `src/tokenizer/detokenizer.py`

### Gate Tests
```
[ ] All previous tests still pass
[ ] New: "in order to" compressed as 1 token, reconstructed as 3 words
[ ] New: overlapping phrases handled correctly (longest match wins)
[ ] New: phrase at end of line doesn't break 80-char binning
[ ] Benchmark: token count reduced by 5-15% on Article x10
[ ] Benchmark: compressed size smaller than Phase 0
```

### Expected Improvement
- 5-15% token reduction → ~300 bytes saved on Article x10
- From ~2.15:1 to ~2.25:1

---

## Phase 2: POS-Partitioned Checksums

### Goal
Enable blanking multiple words per POS category using partitioned
checksums + constraint signals for unique word identification.

### What to Build

**2.1: POS tagger consistency guarantee**
The existing `_get_pos()` heuristic must be deterministic: same word always
gets same POS on both compression and decompression sides. Write tests
proving this. The tagger doesn't need to be linguistically accurate —
it needs to be CONSISTENT.

Files: `src/blanks/constraint_checker.py`

**2.2: Partition checksum computation**
For each POS category (function, noun, verb, adj, adv, proper, unknown),
compute the sum of frequency ranks of all words in that category.

```python
checksums = {
    POS_FUNCTION: sum(ranks of all function words),
    POS_NOUN: sum(ranks of all nouns),
    POS_VERB: sum(ranks of all verbs),
    ...
}
```

Store in blob metadata: 7 partitions × 4 bytes = 28 bytes overhead.

Files: `src/blanks/constraint_checker.py`, `src/serializer/encoder.py`,
`src/serializer/decoder.py`

**2.3: Multi-blank constraint solver**
Given a POS partition's checksum deficit and a list of N blanked words
in that partition, find the unique set of N words whose ranks sum to
the deficit AND match the per-blank constraints (word_length, first_char).

Algorithm:
```
1. deficit = partition_checksum - sum(known_ranks_in_partition)
2. For each blank in partition:
   - candidates = words matching (POS, length, first_char)
   - typically 10-50 candidates per blank
3. Find the combination where candidate ranks sum to deficit
4. If exactly 1 solution: ACCEPT
5. If 0 or 2+ solutions: REJECT (don't blank these words)
```

Files: `src/blanks/blank_resolver.py`

**2.4: Blank selector upgrade**
Allow multiple blanks per POS partition, but ONLY when the solver
can prove unique reconstruction. Run the solver as a pre-check:
if it can't find a unique solution, don't blank.

Files: `src/blanks/blank_selector.py`

**2.5: Global checksum safety net**
After full reconstruction, compute the global checksum and compare
to the stored value. If mismatch → fail loudly (never return wrong text).

Files: `src/pipeline/decompressor.py`

### Gate Tests
```
[ ] All previous tests still pass
[ ] New: POS tagger is deterministic (same word → same POS, always)
[ ] New: partition checksums round-trip correctly through serializer
[ ] New: multi-blank resolver finds unique solution for 3 blanks in same partition
[ ] New: resolver correctly REJECTS non-unique blank sets
[ ] New: global checksum catches deliberately corrupted reconstruction
[ ] New: round-trip with 20+ blanks on Article x10
[ ] Stress: 100 random text samples, all reconstruct perfectly
[ ] Benchmark: blank count increases from ~10 to ~25-30
[ ] Benchmark: Article x10 compressed size drops below 6,000 bytes
```

### Expected Improvement
- 2-3x more words blanked → ~200 bytes additional savings
- From ~2.25:1 to ~2.5:1

### Risk Mitigation
- Global checksum is the ultimate safety net. Wrong reconstruction = hard fail.
- Conservative mode: only blank when solver PROVES uniqueness.
- Log all ambiguous cases during testing → feed into Phase 3 if needed.

---

## Phase 3: 16-Bit Constraint Features (CONDITIONAL)

### Decision Gate
**Only build this phase if Phase 2 testing reveals non-unique solutions
that prevent blanking otherwise-profitable words.**

Review Phase 2 test logs. If >90% of profitable blanks are already
unique with (POS + checksum + length + first_char), SKIP this phase.

### What to Build (if needed)

**3.1: Feature extractor**
Compute 16 binary features per word:
syllable_count, vowel_clusters, repeated_letters, silent_letters,
top_2000, age_of_acquisition, phonetic_complexity, morph_family_size,
char_length_bucket, vowel_count_bucket, consonant_cluster,
double_letter, common_prefix, common_suffix, rare_flag, reserved.

Uses CMU Pronouncing Dictionary (via NLTK) for syllable/phonetic data.

Files: new `src/blanks/feature_extractor.py`

**3.2: Feature storage in constraints**
Add 2-byte feature vector to each blank's constraint data.

Files: `src/blanks/constraint_checker.py`

**3.3: Feature-aware solver**
Multi-blank resolver uses features as additional Venn diagram filter.

Files: `src/blanks/blank_resolver.py`

### Gate Tests
```
[ ] Previously non-unique blanks now resolve uniquely
[ ] All previous tests still pass
[ ] Net savings still positive (2 extra bytes per blank recovered by more blanking)
```

### Expected Improvement
- 5-10 additional blanks → ~50 bytes saved
- From ~2.5:1 to ~2.6:1

---

## Phase 4: Grid Scaling

### Goal
Support documents larger than ~1,600 words (current 100-line limit).

### What to Build

**4.1: Header v2**
Bump version byte to 2. Use uint32 for total_tokens, word_table_len,
and checksum. Header grows from 16 to 24 bytes.

Files: `src/pipeline/config.py`, `src/serializer/encoder.py`,
`src/serializer/decoder.py`

**4.2: Extended coordinate templates**
Generate position templates for line ranges beyond 100.
The coordinate encoder already handles uint16 positions, but
templates only cover lines 1-100. Generate templates for 1-1000.

Files: template generation script, `src/coordinate_encoding/templates/`

**4.3: Backward compatibility**
Version 1 blobs must still decompress correctly.

### Gate Tests
```
[ ] All previous tests still pass
[ ] New: round-trip with 10,000-word document
[ ] New: round-trip with 50,000-word document (book chapter)
[ ] New: version 1 blobs still decompress correctly
[ ] Benchmark: compression ratio on large documents
```

### Expected Improvement
- No compression improvement (scalability feature)
- Unlocks real-world document support

---

## Phase 5: Unified Symbol Codes + Visual Encoding

### Goal
Replace separate word_id + morph_flag with a single unified symbol code
that encodes word identity + morphological form + POS in one code point.
Then build the visual rendering layer (custom font) that makes these
codes scannable as rich visual symbols.

### What to Build

**5.1: Unified symbol code table**
Generate a mapping of (word, morph_form, POS) → unique code point.
With ~500K real combinations, use 3-byte variable-length encoding.
Store the table on Hive as a one-time template.

The code table replaces BOTH `dictionary_cache.json` AND morph_flags.
One code = one complete token identity.

Files: new `src/symbols/symbol_table.py`

**5.2: Symbol codec**
Encode/decode unified symbol codes. Like word_id_codec but covers
the (word, morph, POS) triple:

```text
Code 1-127:           1 byte   (top 127 base forms of function words)
Code 128-32,767:      2 bytes  (common words + common morph forms)
Code 32,768-524,287:  3 bytes  (rare words, all morph forms)
```

Files: new `src/symbols/symbol_codec.py`

**5.3: Custom font generator (visual layer)**
Generate a WOFF2/OTF font where each code point maps to a glyph
with visual properties encoding the token's metadata:

- Glyph shape = word family
- Opacity = morphological form (base/past/ing/s/er/est)
- Internal marks = POS category indicator
- Size variant = word length hint

The font file IS the visual template. Stored on Hive once.

Files: new `src/symbols/font_generator.py`

**5.4: Scanner module**
Read rendered symbols (from canvas/SVG/image) and extract the
multi-dimensional data: word identity + morph + POS from visual
properties. This is the "AI scanner" that reads the visual encoding.

Files: new `src/symbols/scanner.py`

### Gate Tests

```text
[ ] All previous tests still pass
[ ] New: unified code round-trip (encode word+morph+POS → code → decode)
[ ] New: compression pipeline uses unified codes instead of word_id+morph
[ ] New: font renders correctly in browser (visual verification)
[ ] New: scanner extracts correct word+morph+POS from rendered glyphs
[ ] Benchmark: per-token byte cost drops from 2-4 to 2-3 bytes
```

### Expected Improvement

- 0.5-1 byte saved per token from merging word_id + morph_flag
- On Article x10 (~2500 tokens): ~1,250-2,500 bytes saved
- Projected ratio: ~3:1 or better

### Why This Phase Matters

This is where the "ancient/high-tech" vision fully materializes:
- **Ancient**: tiny codes on chain (1-3 byte unified symbols)
- **High-Tech**: rich visual rendering via custom font (scanner-readable)
- **Free information**: visual properties (opacity, marks, rotation) encode
  data that would otherwise cost extra bytes
- **Two layers, one template**: the font file defines both the byte→word
  mapping AND the visual rendering simultaneously

---

## Phase 6: Hive Blockchain Deployment

### Goal
Deploy the compression system on Hive.

### What to Build

**5.1: Dictionary template upload**
Split 249,777-word dictionary into 4KB chunks.
Upload each chunk as a Hive custom_json transaction.
Build index transaction pointing to all chunks.

**5.2: Position template upload**
Upload the 8,946 coordinate patterns as Hive transactions.

**5.3: Compression + upload pipeline**
`compress(text) → base64(blob) → Hive custom_json`

**5.4: Retrieval + decompression pipeline**
`Hive custom_json → base64_decode → decompress(blob) → text`

**5.5: Client-side reconstruction**
JavaScript/TypeScript decompressor for browser-based reconstruction.
Template caching in IndexedDB.

### Gate Tests
```
[ ] Hive testnet: upload dictionary template, retrieve, verify
[ ] Hive testnet: compress document, upload, retrieve, decompress, verify exact match
[ ] Blob size under 5KB for target documents
[ ] Dictionary lookup latency < 100ms from Hive
[ ] End-to-end latency (compress + upload + retrieve + decompress) < 5 seconds
```

---

## Projected Compression Trajectory

### Approach B (Sequential + brotli) — Primary Path

| Phase | Ratio (Article x10) | Ours+brotli | What Changed |
|-------|---------------------|-------------|--------------|
| **Phase 0 (DONE)** | **30.0:1** | **500 bytes** | v3 merged varint, all bug fixes, 176 tests |
| **Phase 1b (DONE)** | **30.8:1** | **487 bytes** | AI-optimized rank assignment (Brown re-rank + SA), 189 tests |
| Phase 1 | ~33:1 | ~455 bytes | Phrase detection (bigrams as single tokens) |
| Phase 5 | ~35:1 | ~430 bytes | Unified symbol codes |
| Phase 6 | ~35:1 | ~430 bytes | Hive deployment |

### Approach A (Inverted Index) — Legacy / Research Path

| Phase | Ratio | Article x10 | What Changed |
|-------|-------|-------------|--------------|
| Current | 2.1:1 | 7,020 bytes | Baseline (inverted index + blank system) |
| Phase 0 deferred | 2.3:1 | ~6,500 bytes | Word family merging |
| Phase 1 | 2.5:1 | ~6,000 bytes | Phrase dictionary |
| Phase 2 | 2.8:1 | ~5,350 bytes | POS checksums (25-30 blanks) |
| Phase 3 | 2.9:1 | ~5,150 bytes | 16-bit features (if needed) |

### Path to 5KB

The previous trajectory stalled at 2.6:1. Three new mechanisms close the gap:

1. **Word family merging** (Phase 0): Combines morphological variants into
   single entries. Fewer word table entries + combined positions hit better
   coordinate templates. Estimated ~260 bytes saved.

2. **Unified symbol codes** (Phase 5): Replaces word_id (1-3 bytes) + morph_flag
   (1 byte per occurrence) with a single code (2-3 bytes total). Saves 0.5-1
   byte per token. On ~2,500 tokens: ~1,250-2,500 bytes.

3. **Visual encoding layer** (Phase 5): The custom font / scanner system means
   rendered symbols carry FREE data in their visual properties. Any information
   the scanner can extract from opacity/marks/rotation is information that
   doesn't need separate bytes in the payload.

The honest math: with all phases, 3:1 on diverse text is achievable.
On repetitive text (articles, blog posts, news), ratios of 4:1+ are realistic
because word families repeat heavily and the blank system removes more.

### The Blockchain Advantage

Traditional compressors (gzip, brotli, zstd) include their dictionary in
every compressed file. Our system stores the dictionary on Hive ONCE.

If you factor out the dictionary cost:
- gzip at 3:1 with ~100 bytes of dictionary overhead = effective 2.9:1
- Our system at 3:1 with ZERO dictionary overhead = true 3:1

For archiving thousands of documents, the amortized advantage compounds.
The first document pays for the templates. Every subsequent document is pure
compression with zero dictionary tax.

---

## Rules

1. **No phase starts until the previous phase's gate tests ALL pass.**
2. **Every phase includes regression tests** — all previous tests must still pass.
3. **Compression must never get worse** — each phase must improve or maintain ratio.
4. **No speculative building** — Phase 3 only happens if Phase 2 data demands it.
5. **Global checksum is the ultimate safety net** — wrong reconstruction = hard fail.
6. **Original documents preserved** — never modify old docs, only add new ones.
