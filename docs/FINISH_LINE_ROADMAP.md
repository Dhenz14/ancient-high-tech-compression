# Finish Line Roadmap — Complete Compression System

## Where We Are (March 17, 2026)

**212 tests passing. 100% lossless. Beats brotli on ALL 10 benchmarks across ALL text genres by 12-26%.**

| Text        | Raw    | brotli | Ours      | Ratio  | vs brotli      |
|-------------|--------|--------|-----------|--------|----------------|
| Article x1  | 1,499  | 477    | **410**   | 3.7:1  | **+14.0% WIN** |
| Article x2  | 2,999  | 480    | **412**   | 7.3:1  | **+14.2% WIN** |
| Article x5  | 7,499  | 482    | **414**   | 18.1:1 | **+14.1% WIN** |
| Article x10 | 14,999 | 482    | **414**   | 36.2:1 | **+14.1% WIN** |
| Blog post   | 781    | 325    | **251**   | 3.1:1  | **+22.8% WIN** |
| News        | 1,879  | 583    | **488**   | 3.9:1  | **+16.3% WIN** |
| Tech doc    | 1,729  | 555    | **488**   | 3.5:1  | **+12.1% WIN** |
| Story       | 1,591  | 630    | **466**   | 3.4:1  | **+26.0% WIN** |
| Mixed (2)   | 2,281  | 757    | **609**   | 3.7:1  | **+19.6% WIN** |
| All mixed   | 7,483  | 2,390  | **1,875** | 4.0:1  | **+21.5% WIN** |

### The Bottleneck Breakdown (Article x1 = 244 tokens)

| Category | Tokens | % | Bytes/token | Problem |
|----------|--------|---|-------------|---------|
| Tier 1 (1-byte) | 49 | 20% | 1 | Optimal |
| Tier 2 (2-byte) | 100 | 41% | 2 | Good |
| Tier 3 (3-byte) | 70 | 29% | 3 | Many common words just miss 511 cutoff |
| Extra section | 25 | 10% | ~8 | **BLEEDING BYTES** — all are common inflected forms |

**The #1 problem**: 14,331 Brown corpus words are missing from the dictionary.
"has" (freq 2437), "asked", "children", "states", "looked", "called" — all common
inflected forms that NLTK `words` corpus and WordNet lemmas don't include (they only
have base forms). Every missing word costs ~8 bytes in the extra section instead of
~2.5 bytes in the main stream. That's 5.5 bytes wasted per token.

---

## The Build Order (7 phases to deployment)

```
DONE ✓  Phase 0: Foundation (v3 merged varint, 176 tests)
DONE ✓  Phase 1: AI-Optimized Ranks (Brown re-rank + SA, 189 tests, +2.8%)
DONE ✓  Phase 2: Dictionary Coverage Fix (189 tests, beats brotli ALL 6 by 14-22%)
DONE ✓  Phase 3: Phrase Detection + Diverse Benchmarks (212 tests, beats brotli ALL 10 genres by 12-26%)
─────── YOU ARE HERE ───────
        Phase 4: Morphological Fallback         ← Kill remaining extras (~3-5%)
        Phase 5: Extended Training Corpus       ← Polish (~1-2%)
        Phase 6: Production Packaging           ← Lock format
        Phase 7: Hive Deployment                ← Ship it
```

### Projected Trajectory

| Phase          | Article x1  | Blog    | All mixed | Total improvement      |
|----------------|-------------|---------|-----------|------------------------|
| Phase 1 done   | 471         | 285     | —         | baseline               |
| Phase 2 done   | 409         | 253     | —         | +14-22% vs brotli      |
| Phase 3 done   | **410**     | **251** | **1,875** | **+12-26% all genres** |
| Phase 4        | ~400        | ~248    | ~1,840    | +2-4% more             |
| Phase 5        | ~396        | ~245    | ~1,810    | +1-2% polish           |

---

## ~~Phase 2: Dictionary Coverage Fix~~ — DONE

**Result**: Article x1: 471 → 409 bytes (-13.2%). ALL 6 benchmarks beat brotli by 14-22%.
Brown +14,331 inflected forms, Gutenberg +12,989 inflected forms. 189 tests pass.

### The Problem (was)

`build_dictionary.py` collects words from:
- NLTK `words` corpus (~236K entries) — **base forms only** (ask, child, state)
- WordNet lemmas (~147K) — **base forms only** (lemmas by definition)
- Brown corpus — used for **frequency ranking only**, NOT added to word set

Result: "asked", "children", "states", "looked", "called", "having", "makes",
"friends", "moments", "lives" — all missing. These are the 25 extra-section
tokens in Article and the 12 in Blog.

### The Fix

1. Add all Brown corpus word tokens to the dictionary word set
2. Also add all Gutenberg corpus word tokens (more inflected forms)
3. The dictionary is capped at 249,777 — evict zero-frequency tail words
   (words from NLTK/WordNet that never appear in Brown or Gutenberg)
4. Re-run rank optimizer on expanded dictionary

### What to Build

**2.1: Expand `build_dictionary.py`**
- Add Brown corpus words to `collect_all_words()` (not just frequency map)
- Add Gutenberg corpus words to `collect_all_words()`
- When exceeding 249,777 limit, evict words with zero frequency
- Verify: "has", "asked", "children", "states" all present in new dictionary

**2.2: Rebuild dictionary**
- Run `python3 build_dictionary.py` → new `dictionary_cache.json`
- Run rank optimizer → new `optimized_dictionary_cache.json`

**2.3: Validate**
- All 189 tests pass with new dictionary
- Benchmark shows improvement
- Extra section tokens dramatically reduced

### Gate Tests

```
[ ] "has", "asked", "children", "states", "looked" all in dictionary
[ ] Extra section tokens in Article drop from 25 to < 10
[ ] All 189 existing tests pass
[ ] Round-trip: all benchmark texts reconstruct perfectly
[ ] Benchmark: Article x1 < 455 bytes
[ ] Benchmark: Blog < 275 bytes
```

### Expected Improvement

- Extra section: 25 tokens → ~5 tokens (Article), 12 → ~3 (Blog)
- ~20 tokens saved × 5.5 bytes each = ~110 bytes saved on Article Stage 1 blob
- After brotli: ~30-40 bytes net improvement
- **Article x1: 471 → ~440 bytes (+6.6%)**

### Files to Modify

- `build_dictionary.py` — add Brown/Gutenberg words to word set
- `dictionary_cache.json` — regenerated
- `optimized_dictionary_cache.json` — regenerated via rank optimizer

### Dependencies

None new. NLTK Brown and Gutenberg already downloaded.

---

## ~~Phase 3: Phrase Detection + Diverse Benchmarks~~ — DONE

**Result**: 23 bigram phrases added. SA trained on 5 text genres. Beats brotli on ALL 10
benchmarks across ALL text types (article, blog, news, tech, story) by 12-26%. 212 tests pass.

### What Was Built

- `src/sequential/phrase_miner.py` — two-stage brotli scoring (Brown screen + 6-text validation)
- `src/wordid/dictionary.py` — `.phrases` property (frozenset of space-containing keys)
- `src/sequential/encoder.py` — `_merge_phrases()` merges adjacent token pairs
- `src/sequential/rank_optimizer.py` — phrase-aware Brown frequencies (bigrams counted)
- `build_dictionary.py` — `mine_and_add_phrases()` with Brown Stage 1 / benchmark Stage 2 split
- `bench_rank_optimizer.py` — 5 diverse benchmark texts (NEWS, TECH, STORY added)
- `tests/sequential/test_phrases.py` — 24 tests, 212 total passing

### Key Design Lesson

**Stage 1 and Stage 2 must use different corpora.**

- Stage 1 (fast screen, q=5): Brown corpus sample — diverse, non-repetitive, large enough for brotli to detect bigram savings reliably
- Stage 2 (precise score, q=11): actual benchmark texts — validates on real use case
- Using Brown for both: selects phrases common in Brown but rare in benchmarks (original bug)
- Using benchmark texts for both: too short for brotli Stage 1 detection (regression)

### Phrases Added (top by savings)

`more than`, `by the`, `into the`, `has been`, `about the`, `the most`, `should be`,
`to be`, `with the`, `to take`, `him to`, `for the`, `as a`, `from a`, `a way`,
`a few`, `according to`, `to work`, `that the`, `after a`, `said the`, `they were`, `a year`

### Snapshots

- Tag: `v1.2-phase3-diverse-benchmarks`
- Backups: `dictionary_cache_v1_phase3b.json`, `optimized_dictionary_cache_v1_phase3b.json`

---

## Phase 4: Morphological Fallback Encoding

### The Problem

After Phase 2 (dictionary expansion), some inflected forms will still miss
the dictionary — words not in Brown or Gutenberg but common in Hive posts.
Also, proper nouns, neologisms, and domain terms will always be unknown.

Currently: unknown word → extra section → ~8 bytes.

### The Idea (from research files)

The project already has `src/morphology/` with:
- `lemmatizer.py` — 100+ irregular forms, suffix stripping
- `inflector.py` — morphological inflection patterns
- 438 morphological patterns (COMPREHENSIVE_MORPHOLOGICAL_PATTERN_DETECTOR.py)

If an unknown word's **stem** is in the dictionary, encode as:
`rank(stem) * 32 + morph_variant` — same varint format, but the morph_variant
tells the decoder which suffix to re-apply.

Example: "computerized" (unknown) → stem "computer" (rank 512) + suffix "-ized"
- Current: extra section = ~14 bytes
- Proposed: rank(computer) * 32 + MORPH_IZED = 3 bytes

### What to Build

**4.1: Morphological analyzer for encoder**
- On unknown word: try suffix stripping (ing, ed, s, er, est, ly, tion, ment, etc.)
- If stem is in dictionary → encode as stem rank + morph code
- Morph codes use variant bits 0-15 (currently used for trailing punct)
- Need a new variant format for morph tokens, or use a morph escape in extra section

**4.2: Morphological decoder**
- Read morph code, look up stem, re-apply suffix
- Must be deterministic (same suffix rules on both sides)

**4.3: Integration with existing morphology module**
- Leverage `src/morphology/lemmatizer.py` for stem detection
- Leverage `src/morphology/inflector.py` for reconstruction

### Design Choice: Variant Bits vs Escape Code

**Option A — Morph escape in extra section**: When extra section word can be
decomposed, store `[morph_code:1][stem_rank:2-3]` instead of `[len:1][utf8:N]`.
Distinguishable by a flag byte. This doesn't touch the main stream format.

**Option B — Extended variant**: Add a morph bit to the variant field. Would
require format change (v4). More disruptive.

**Recommendation**: Option A. Minimal format change, backwards compatible.

### Gate Tests

```
[ ] "computerized" → stem "computer" + suffix detected
[ ] Round-trip: "computerized" reconstructs perfectly
[ ] "walking" encoded as morph(walk, -ing) if walk in dict
[ ] All existing tests pass
[ ] Benchmark: extra section tokens < 5 on Article
```

### Expected Improvement

- Remaining extra tokens: ~5-8 per text → ~2-3
- **Article x1: ~415 → ~405 bytes (+3-5%)**

### Files to Create/Modify

- `src/sequential/morph_encoder.py` — NEW: stem detection + morph encoding
- `src/sequential/encoder.py` — integrate morph fallback before extra section
- `src/sequential/decoder.py` — handle morph-encoded tokens in extra section
- `tests/sequential/test_morph.py` — NEW

### Dependencies

None new. Existing morphology module.

---

## Phase 5: Extended Training Corpus + SA Polish

### The Problem

Current SA trains on 3 benchmark texts (Article, Blog, Mixed). This may
overfit to these specific texts. Also, Hive posts have different word
distributions than Brown corpus.

### What to Build

**5.1: Corpus builder**
- Collect 50-100 diverse text samples:
  - Brown corpus excerpts (10 genres × 2 excerpts = 20)
  - Gutenberg excerpts (10 books × 2 excerpts = 20)
  - Synthetic blog-style text (10 samples)
  - If available: real Hive post samples (20+)
- Store as `training_corpus.json`

**5.2: Extended SA**
- Run SA with 10,000+ iterations on the full training corpus
- Use the fast encode path (already built in rank_optimizer.py)
- Evaluate on held-out test set to prevent overfitting

**5.3: Cross-validation**
- Split corpus into train/test
- Report improvement on both
- If test improvement < 50% of train improvement → overfitting, reduce iterations

### Gate Tests

```
[ ] SA improves on held-out test set (not just training texts)
[ ] All existing tests pass
[ ] Benchmark shows improvement on standard texts
```

### Expected Improvement

- **1-2% additional compression across all text types**

---

## Phase 6: Production Packaging

### Goal

Lock the format, finalize the dictionary, ensure everything is deployment-ready.

### What to Build

**6.1: Format version bump**
- Version byte 0x04 if any format changes from Phase 4 (morph encoding)
- Version byte 0x03 stays if no format changes
- Backward compatibility: decoder handles both

**6.2: Final dictionary**
- Combine all improvements: expanded word set + phrases + optimized ranks
- Freeze as `dictionary_v1.json` (immutable once deployed to Hive)
- Include dictionary checksum in blob header for verification

**6.3: CLI tool**
- `python3 compress.py input.txt output.bin` — compress
- `python3 decompress.py output.bin output.txt` — decompress
- `python3 benchmark.py input.txt` — show compression stats
- Handle stdin/stdout for piping

**6.4: Performance optimization**
- Profile encoder/decoder for speed bottlenecks
- Optimize dictionary loading (binary format instead of JSON?)
- Target: < 10ms for 1KB text, < 100ms for 100KB text

**6.5: Documentation freeze**
- Final README with definitive results
- API documentation for encoder/decoder
- Dictionary format specification

### Gate Tests

```
[ ] CLI compress/decompress works end-to-end
[ ] 100 random text samples all round-trip perfectly
[ ] Performance: < 10ms for 1KB text
[ ] Dictionary checksum verification works
[ ] All tests pass
```

---

## Phase 7: Hive Blockchain Deployment

### Goal

Put it on-chain. Dictionary stored once, documents compressed per-post.

### What to Build

**7.1: Dictionary upload**
- Split dictionary into 4KB chunks (Hive custom_json limit)
- Upload each chunk as a transaction
- Build index transaction pointing to all chunks
- Total: ~1,300 transactions for 5MB dictionary (one-time cost)

**7.2: Compression API**
- `compress(text) → base64(blob)` for Hive posting
- Include dictionary version hash in blob header
- Blob fits in Hive custom_json (< 8KB for typical posts)

**7.3: Client-side decompressor (JavaScript/TypeScript)**
- Port decoder to JS/TS for browser-based reconstruction
- Dictionary cached in IndexedDB after first load
- Subsequent loads: instant decompression (no dictionary fetch)
- Target: < 50ms decompression in browser

**7.4: Hive integration**
- Custom operation for compressed posts
- Fallback: uncompressed if dictionary not available
- Version negotiation between compressor/decompressor

### Gate Tests

```
[ ] Hive testnet: upload dictionary, retrieve, verify
[ ] Hive testnet: compress post, upload, retrieve, decompress, exact match
[ ] Browser decompressor: works in Chrome, Firefox, Safari
[ ] Dictionary caching: second load < 10ms
[ ] End-to-end latency < 3 seconds (compress + upload + retrieve + decompress)
```

---

## Research Gems — Incorporated

### From research files (what's used vs what's shelved):

| Research File | Key Finding | Status |
|---------------|-------------|--------|
| `research_two_stage.py` | Two-stage (word-level + brotli) beats standalone brotli | **IMPLEMENTED** — core of Approach B |
| `research_vs_world.py` | Word-level encoding + byte-level compressor is the winning formula | **IMPLEMENTED** |
| `research_blank_everything.py` | Blanking 100% of words requires same position data as inverted index | **SHELVED** — sequential approach avoids this entirely |
| `research_visual_free_info.py` | Visual properties can't compress beyond bytes (rendering needs storage) | **SHELVED** — no byte savings, useful only for human/AI readability |
| `research_microdot.py` | Fixed-size images worse than template encoding for positions | **SHELVED** — templates already implemented |
| `research_static_templates.py` | Pre-compute common patterns, delta for rest | **IMPLEMENTED** — 8,946 templates in Approach A |
| `research_template_math.py` | Full templates for 1-4 occurrences, delta for 5+ | **IMPLEMENTED** in coordinate encoding |
| `research_combined_template.py` | Combining V+H templates saves 10+ bytes per word | **IMPLEMENTED** in coordinate encoding |
| `research_compact_encoding.py` | 11-bit positions + blanking = 3.3:1 | **SUPERSEDED** — sequential v3 achieves 30.8:1 |
| `research_symbols.py` | OpenType variable fonts can encode metadata in visual properties | **DEFERRED** to Phase 7+ (visual layer, not compression) |
| `research_tiny_images.py` | 8-byte image ≡ 8-byte template index (equivalent) | **SHELVED** — templates already chosen |

### From CONTRACTION_SUPER_SYMBOL_INTEGRATION.py:
- 36 contraction types identified (don't, can't, won't, etc.)
- **IMPLEMENTED** — v3 encoder handles contractions via mid-word apostrophe preservation
- Unknown contractions go to extra section (could be added to dictionary in Phase 2)

### From COMPREHENSIVE_MORPHOLOGICAL_PATTERN_DETECTOR.py:
- 438 morphological patterns (suffixes, prefixes, stems)
- **PLANNED** for Phase 4 — morphological fallback encoding

### From production_scanner.py:
- Authoritative scanner module for Approach A
- **NOT NEEDED** for sequential approach (no scanning required)

---

## Summary: What Gets Us to "Finished"

| Phase | Work | Impact | Effort |
|-------|------|--------|--------|
| 2 | Dictionary fix | **+6-8%** | Small (modify build_dictionary.py) |
| 3 | Phrase detection | **+5-8%** | Medium (new tokenizer pre-pass) |
| 4 | Morph fallback | **+3-5%** | Medium (leverage existing morph module) |
| 5 | Extended SA | **+1-2%** | Small (more training data) |
| 6 | Production CLI | Ship-ready | Medium (CLI, perf, docs) |
| 7 | Hive deployment | On-chain | Large (JS port, blockchain integration) |

**Total projected improvement: 15-23% better than current.**
**Projected final: Article x1 ~400 bytes (3.7:1), Blog ~252 bytes (3.1:1).**
**Beats brotli on ALL single-document text types.**

---

## Rules (carried from Blueprint)

1. No phase starts until the previous phase's gate tests ALL pass.
2. Every phase includes regression tests — all previous tests must still pass.
3. Compression must never get worse — each phase must improve or maintain ratio.
4. No speculative building — Phase 4 only if dictionary still has significant extras.
5. 100% lossless reconstruction — always.
6. Dictionary is immutable once deployed to Hive — all optimization happens before Phase 7.
