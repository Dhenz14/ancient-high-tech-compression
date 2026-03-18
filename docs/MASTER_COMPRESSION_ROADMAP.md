# Master Compression Roadmap — Post v2.0

**Baseline**: Sequential Rank Stream v4 + brotli q=11
**Current performance**: 19.3% better than raw brotli across all 11 benchmarks
**Best single ratio**: 36.6:1 on Article x10
**Locked version**: v2.0 (tag: `v2.0-v4-format-doubled-tiers`)

---

## Rules of Engagement

1. **Every phase has a test gate.** All 118 existing sequential tests must pass. The benchmark must not regress on any of the 11 texts.
2. **If it degrades, revert immediately.** Run `git checkout v2.0-v4-format-doubled-tiers` and continue from the last working base.
3. **Lock each win.** When a phase improves results, commit + tag before starting the next phase.
4. **Measure pre-brotli AND post-brotli.** A change that saves bytes pre-brotli might be absorbed by brotli's LZ77. The post-brotli number is the only one that counts.
5. **Never break backward compatibility.** v2/v3/v4 blobs must remain decodable.

---

## Phase Order (priority = expected gain ÷ implementation effort)

```
Phase 1  → Trigram Phrases
Phase 2  → Phrase Dictionary Expansion (50+ phrases)
Phase 3  → Blank System — Tier-1 Prototype
Phase 4  → Blank System — Full Cascade
Phase 5  → Morphological Fallback (Extra-Section Reduction)
Phase 6  → SA Re-Training After Each Dictionary Change
Phase 7  → Cross-Sentence Blank Cascade
Phase 8  → Hive Blockchain Deployment
Phase 9  → Visual Encoding / Scanner (Readability Layer)
```

---

## Phase 1 — Trigram Phrases ❌ DITCHED

**Result**: 2 trigrams survived strict Stage 2 brotli gate ("of the old" +7B, "is one of" +6B).
Combined pre-brotli savings: 13 bytes. SA re-training with the expanded dictionary
found a worse local minimum (48 improvements vs v2.0's 66), losing 47 bytes total.
Net: −47 bytes. Clear regression on 7/11 texts.

**Root cause**: SA variance (~30-50 bytes) is larger than trigram gains (~13 bytes).
Adding phrases reshuffles the tier-2 landscape, causing SA to converge differently.
Signal is drowned by noise.

**Infrastructure kept**: `_merge_phrases` now handles trigrams-first, and `mine_trigrams`
works correctly. The mechanism is sound; the signal just isn't strong enough.

---

## Phase 1 — Trigram Phrases (archived)

### What it is
Currently the phrase dictionary contains 23 bigrams (2-word phrases like "in the",
"more than", "has been"). Trigrams are 3-word combinations:

```
"in order to"      "at the same time"     "on the other hand"
"as well as"       "in the case of"       "at the end of"
"as a result"      "one of the"           "some of the"
"part of the"      "many of the"          "out of the"
"because of the"   "in addition to"       "due to the"
```

A trigram match turns 3 tokens into 1, saving 4 bytes (3 × 2-byte tier-2 → 1 × 2-byte).

### How to implement
Extend `src/sequential/phrase_miner.py` to handle n=3. The two-stage scoring pipeline
already supports arbitrary n-grams — just needs a trigram candidate generator:

```python
# In phrase_miner.py, add trigram candidate generation:
for i in range(len(words) - 2):
    trigram = words[i] + ' ' + words[i+1] + ' ' + words[i+2]
    candidate_counts[trigram] += 1
```

The two-stage brotli scoring (Brown corpus screen → benchmark validation) filters out
any trigram that doesn't actually reduce compressed size in practice.

Extend `_merge_phrases` in encoder.py to support merging 3-token sequences:

```python
# Current: checks i and i+1
# New: check i, i+1, i+2 first, then fall back to bigram check
```

Dictionary key format unchanged: trigrams stored as "word1 word2 word3" with a space.

### Test gate
- All 118 existing tests pass
- At least 1 trigram found with positive brotli score on benchmark texts
- No benchmark text regresses (all 11 texts must stay at or above current bytes)
- Total savings across 11 texts must be positive

### Expected gain
- 1–2% on Article, News, Tech (formal writing uses fixed phrases heavily)
- Minimal on Informal, Blog (casual writing avoids fixed phrases)
- Trigrams are rarer than bigrams — realistic to find 3–8 good ones

### Revert condition
If no trigram passes the two-stage brotli screen, or if any benchmark regresses,
discard and stay at v2.0. Lock and tag if any improvement is found.

---

## Phase 2 — Phrase Dictionary Expansion ❌ DITCHED

**Result**: Same root problem as Phase 1. The 23 bigrams already in the dictionary
are the best ones — they were selected with a strict brotli gate. Lowering the
threshold to add marginal bigrams produces gains of 1–3 bytes pre-brotli, which is
well within SA variance (~30-50 bytes). Any marginal addition risks SA finding a
worse local minimum that erases the gain and then some.

**Root cause**: SA noise dominates signal at this margin. The dictionary expansion
idea only makes sense after SA variance is brought under control (Phase 6) or after
a format change increases tier-2 diversity.

**Decision**: Skip. The 23 bigrams stay. Move to Phase 3.

---

## Phase 2 — Phrase Dictionary Expansion (50+ Phrases) (archived)

### What it is
The current 23 bigrams were selected with a conservative savings threshold. Lowering
the threshold and running on a larger corpus would likely yield 20–30 more bigrams,
including some less common but still valuable phrases.

### How to implement
1. Lower the minimum bytes-saved threshold in `phrase_miner.py` from the current
   value to 1 byte (currently may be set higher).
2. Run phrase mining on expanded corpus: all 7 benchmark texts + Brown corpus words.
3. Re-run after Phase 1 (trigrams already in dictionary change the bigram landscape —
   some bigrams become redundant if their trigram is already handled).
4. Target: 50 total phrases (bigrams + trigrams combined).

### Diminishing returns warning
Each additional phrase costs 1 entry in the dictionary but produces progressively
smaller gains. Stop adding phrases when the marginal gain per phrase drops below
0.5 bytes on the benchmark suite.

### Test gate
- All 118 existing tests pass
- Net improvement on total bytes across all 11 texts
- No single text regresses

### Expected gain
- 0.5–1.5% additional on top of Phase 1
- Most gain comes from a handful of high-frequency additions — long tail is noise

---

## Phase 3 — Blank System: Tier-1 Prototype ❌ DITCHED

**Result**: 8/8 texts regressed. Total: +92 bytes worse post-brotli across all benchmark texts.
Article x1: +12 bytes. Story: +14 bytes. All mixed: +32 bytes.

**Root cause**: Tier-1 tokens (ranks 1-7) cost 1 byte in the main stream. The blank
section stores rank (1 byte) + delta_position (1 byte) = 2 bytes per blank. Net per
blank = +1 byte overhead before brotli. For 55 blanks in Article x1: +55 bytes pre-brotli
(499→556). Brotli recovers ~43 bytes of structure benefit, but final delta is still −12.

**The fundamental math**: blanking tier-1 tokens can NEVER break even pre-brotli when
position storage costs ≥ savings. The only viable blank system requires:
  (a) blanking tier-2+ tokens (2 bytes each), AND
  (b) multiple blanks sharing overhead amortization
Phase 4 needs to be redesigned around this constraint — not tier-1 words.

**Infrastructure kept**: V5 encoder/decoder in `blank_encoder.py` + decoder.py proves
the mechanism works (100% round-trip on all 21 tests). The puzzle-solving concept is
sound — just needs a different target tier.

---

## Phase 3 — Blank System: Tier-1 Prototype (archived)

### What it is
The most novel idea in this codebase. Instead of storing every word in the stream,
OMIT the most common words (tier-1: ranks 1–7 = the, of, and, to, a, in, that) and
reconstruct them on decode using a mathematical checksum.

**The core insight**: rank IDs are unique integers. If a sentence has 1 word omitted
and you store the sum of all rank IDs in the sentence, the decoder can calculate the
missing rank exactly: `missing_rank = stored_checksum − sum(present_ranks)`.

No trial-and-error needed for the 1-blank case. It's pure arithmetic.

### Design

**Encoder side**:
```
Per sentence (split on T_PERIOD token):
  1. Encode all non-tier-1 tokens normally into main stream
  2. Store sentence header: [token_count: 1 byte] [blank_count: 1 byte] [checksum: 2 bytes]
     checksum = sum(all rank IDs in sentence) mod 65536
  3. Omit tier-1 tokens from main stream
  4. Store blank positions as deltas from their neighbors (1 byte each, usually <16)
```

**Decoder side**:
```
Read sentence header → know total count, blank count, checksum
Read non-blank tokens → sum their ranks
Solve: sum_of_blanks = checksum − sum_of_present_ranks
For 1 blank: missing_rank = sum_of_blanks (exact, no ambiguity)
For 2 blanks: find pair (r1, r2) from tier-1 set where r1 + r2 = sum_of_blanks
  If unique pair exists → solved
  If multiple pairs possible → fall back to storing positions explicitly
For 3+ blanks: use cascade (Phase 4)
```

**Position recovery**:
Blank positions are stored as a compact "gap array" in a separate section:
- 1 byte per blank: gap = distance from blank to previous token (0–15 fits in 4 bits)
- 2 blanks per byte packed (nibbles): saves 50% of position storage

### Cost/benefit analysis (Article x1, ~100 tokens, ~25 tier-1 tokens):
```
Savings: 25 tier-1 tokens × 1 byte = 25 bytes removed from main stream
Overhead:
  - Sentence headers: ~6 sentences × 4 bytes = 24 bytes
  - Gap array: ~25 positions × 0.5 bytes = 12-13 bytes
Net pre-brotli: 25 − 37 = −12 bytes (WORSE before brotli)
```

This looks bad — but brotli changes the math. The main stream without tier-1 noise
compresses differently. The gap array and headers are highly structured (small values,
low entropy) and compress better than the removed tier-1 bytes did.

**Key unknown**: does post-brotli net work out positive? Must benchmark.

### Alternative: sentence-length-only (no gap array)

For 1-blank sentences:
- Store sentence length (1 byte)
- Decoder knows exactly 1 slot is empty — position is deterministic (scanning stream,
  the one unfilled position is the blank)
- No gap array needed for 1-blank case
- Only blanks in 1-blank sentences (conservative start)

This version is simpler and might already show a net gain.

### Test gate
- New roundtrip tests: sentences with tier-1 words omitted reconstruct correctly
- Mathematical proof: for all sentences in benchmark texts, checksum recovery is
  unique (no ambiguous cases in the 1-blank prototype)
- All 118 existing tests pass
- Benchmark: net post-brotli improvement across the 11 texts
- Round-trip accuracy: 100% (any reconstruction error = immediate discard)

### Expected gain (conservative estimate)
- 0–3% on single documents (depends heavily on post-brotli behavior)
- Near zero on repetitive documents (brotli already handles tier-1 repetition)
- High uncertainty: this is novel territory — could be neutral, could be 3%+

### Revert condition
If post-brotli results are neutral or negative on any benchmark text, discard this
phase entirely. The overhead (sentence headers + gap array) may not pay off.

---

## Phase 4 — Blank System: Full Cascade

### What it is
Extends Phase 3 from "1-blank sentences only" to "multi-blank sentences with
cascade solving."

**The cascade algorithm**:
```
Pass 1: Solve all 0-blank sentences (checksum validates, no inference needed)
Pass 2: Solve all 1-blank sentences (arithmetic: missing = checksum − sum)
Pass 3: For 2-blank sentences, now that many tier-1 positions are resolved from
        neighboring sentences, constrain the search space.
        Try all pairs from tier-1 set {1,2,3,4,5,6,7} that sum to sum_of_blanks.
        Typically 0–2 valid pairs → often unique.
Pass 4: 3-blank sentences. Now combine: use sentence-level checksum + document-level
        frequency constraint (e.g., "the" has appeared 14 times so far, so appears
        approximately 2 more times in remaining sentences based on frequency model).
        Narrows candidates further.
Pass N: Any remaining ambiguous sentences fall back to explicit position storage.
```

**POS-partitioned checksums (from legacy `src/blanks/`)**:
Instead of one checksum per sentence, store per-POS checksums:
- Noun checksum (sum of all noun ranks)
- Function word checksum (sum of ranks 1–7: the, of, and, to, a, in, that)
- Verb checksum (sum of verb ranks)

Each POS checksum narrows the search space dramatically. A missing FUNCTION WORD
(POS=function) can only be rank 1–7. Combined with the function-word checksum, this
usually uniquely identifies even 2-blank sentences without a gap array.

The legacy code for this lives in:
- `src/blanks/constraint_checker.py` — POS-partitioned checksum logic
- `src/blanks/blank_resolver.py` — gap detection and blank assignment
- `src/blanks/blank_selector.py` — word eligibility for blanking

These were designed for Approach A (inverted index). For Phase 4, they need to be
adapted to the sequential stream model.

### Prerequisite
Phase 3 must show a measurable post-brotli gain. If Phase 3 is neutral, Phase 4
won't help either.

### Test gate
- All reconstruction tests pass (100% round-trip accuracy required)
- Multi-blank cascade solves correctly for all sentences in benchmark texts
- No false reconstructions: verify decoded text === original text character-by-character
- Net improvement on benchmark suite

### Expected gain
- 2–5% on single documents if Phase 3 showed positive results
- The cascade system is designed to blank ~25–30 words per article
- Each successfully blanked tier-2 word (2 bytes) saves more than a tier-1 word (1 byte)

---

## Phase 5 — Morphological Fallback (Extra-Section Reduction)

### What it is
Currently, unknown words (not in the 249,777-word dictionary) go to the extra section
as raw UTF-8 strings: a length byte + the full word. For "computerized" = 1 + 12 = 13
bytes. For "reorganizing" = 1 + 12 = 13 bytes.

If the word's BASE FORM (stem) IS in the dictionary, encode as:
```
[morph_escape_code: 1 byte] [stem_rank: 1-2 bytes] [morph_flag: 1 byte]
```

Total: 3 bytes instead of 13. Savings: 10 bytes per unknown-but-morphologically-regular word.

### Morph flags (from legacy `src/morphology/`)

31 morph flags already defined and tested:
```
MORPH_S     → "dogs" from "dog"
MORPH_ED    → "walked" from "walk"
MORPH_ING   → "running" from "run"
MORPH_ER    → "faster" from "fast"
MORPH_EST   → "fastest" from "fast"
MORPH_LY    → "quickly" from "quick"
MORPH_NESS  → "happiness" from "happy"
MORPH_TION  → "creation" from "create"
MORPH_ABLE  → "readable" from "read"
MORPH_MENT  → "movement" from "move"
MORPH_FUL   → "hopeful" from "hope"
MORPH_LESS  → "hopeless" from "hope"
MORPH_OUS   → "famous" from "fame"
MORPH_UN    → "unhappy" from "happy"
MORPH_RE    → "redo" from "do"
+ 16 irregular forms (went→go, came→come, saw→see, etc.)
```

438 morphological patterns catalogued in `COMPREHENSIVE_MORPHOLOGICAL_PATTERN_DETECTOR.py`.

### Implementation

In `encoder.py`, before writing an unknown word to the extra section:
```python
# Try morphological decomposition
stem, morph_flag = morph_decompose(word)
if stem in dictionary:
    stem_rank = dictionary.word_to_rank(stem)
    write_morph_escaped(main_buf, stem_rank, morph_flag)
    # No extra section entry needed
else:
    # Fall through to existing extra section handling
    write_extra_section(extra_buf, word)
```

In `decoder.py`, when rank=0 token is encountered:
```python
# Check if this is a morph-escaped token
if variant == MORPH_ESCAPE:
    stem_rank = read_varint(extra_buf)
    morph_flag = read_byte(extra_buf)
    stem_word = dictionary.rank_to_word(stem_rank)
    word = morph_inflect(stem_word, morph_flag)
else:
    # Existing extra section handling
    word = read_extra_word(extra_buf)
```

### Test gate
- All 118 existing tests pass
- New morphological roundtrip tests: "computerized" → encodes → decodes → "computerized"
- Benchmark: improvement on texts with academic/technical vocabulary (News, Tech, Article)
- Zero regressions

### Expected gain
- 3–5% on texts with academic/formal vocabulary
- Near zero on Informal (simple words, mostly in dictionary)
- Highest impact on Novel/Tech texts with inflected forms

---

## Phase 6 — SA Re-Training After Dictionary Changes

### What it is
Every time the phrase dictionary changes (Phases 1, 2) or morphological encoding
changes the rank distribution (Phase 5), the SA-optimized rank assignments become
stale. The SA was trained to maximize brotli compression on the OLD byte patterns.

After any dictionary change, re-run:
```bash
python3 bench_rank_optimizer.py
# Parameters: n_iterations=20000, cooling=0.9993, start_temp=3.0
# 6 SA training texts (News, Article, Blog, Tech, Story, All-mixed)
```

### This is not a "phase" in the same sense — it's maintenance

After Phase 1 (trigrams added): re-run SA, compare, keep if better.
After Phase 2 (more phrases): re-run SA, compare, keep if better.
After Phase 5 (morphological fallback): re-run SA (rank distribution shifts).

### Key parameters (locked in v2.0, only adjust if tier boundaries change)
```
n_iterations = 20000
start_temp   = 3.0
cooling_rate = 0.9993   ← tuned for 1016 tier-2 words
min_temp     = 0.001
training_texts = 6 (News, Article, Blog, Tech, Story, All-mixed)
```

If a future phase changes VARIANT_MULT again (e.g., to 8), recalculate cooling:
```
iterations_warm = log(min_temp / start_temp) / log(cooling_rate)
# Must be > 50% of n_iterations for sufficient exploration
```

---

## Phase 7 — Cross-Sentence Blank Cascade

### What it is
Phase 4 solves blanks sentence-by-sentence. Phase 7 uses DOCUMENT-LEVEL frequency
constraints to solve blanks that are ambiguous at the sentence level.

**Example**: "the" appears 23 times in an article. If 20 have been placed by the
cascade solver, the remaining 3 must account for the known total frequency. The
frequency constraint narrows which sentences still need "the" inserted.

**Frequency table**:
```
[header block: per-blanked-word total frequency, 1 byte each]
e.g., "the":23, "of":8, "and":12, "to":9, "a":7, "in":6, "that":4
= 7 bytes for the full tier-1 frequency table
```

The decoder tracks running counts. When a sentence has 2 possible blank assignments
but one would overshoot the document frequency, it's eliminated.

### Prerequisite
Phases 3 and 4 must both show positive results. Phase 7 is an optimization on top
of the cascade, not a standalone win.

### Expected gain
- Additional 0.5–1% by resolving ambiguous sentences that Phase 4 had to fall back on
- Mainly improves recall on longer, denser documents

---

## Phase 8 — Hive Blockchain Deployment

### What it is
The dictionary (249,777 words, ~5MB JSON) is stored ONCE on the Hive blockchain
as a custom_json transaction. All users share it at zero additional per-document cost.

Per-document: only the compressed blob is stored (~400–500 bytes for a 1,500-byte article).

**Architecture**:
```
Write path:
  Text → encode(v4) → brotli → base64 → custom_json on Hive

Read path:
  custom_json → base64 decode → brotli decompress → decode(v4) → Text
  Dictionary: fetched once from Hive, cached in IndexedDB (browser) or local file
```

**Client decompressor**: JavaScript/TypeScript port of `decoder.py`.
- LEB128 varint decode
- Dictionary lookup (word_to_rank reverse: array indexed by rank)
- Extra section parsing
- brotli decompression (via `brotli-wasm` npm package)

### What needs building
1. `src/sequential/decoder.js` — JS port of decoder.py
2. Dictionary upload script — posts `optimized_dictionary_cache.json` to Hive
3. Round-trip test: Python encode → JS decode → verify
4. Performance test: decode latency < 200ms for typical article

### Prerequisites
All compression phases complete and locked. No point deploying a format that will
change next week.

---

## Phase 9 — Visual Encoding / Scanner (Readability Layer)

### What it is
This phase does NOT improve compression. It makes the compressed data HUMAN AND
AI READABLE without decompression.

A custom font (stored on Hive alongside the dictionary) renders each compressed token
as a visual glyph where:
- **Shape**: identifies word family
- **Internal micro-lines**: encode position coordinates (Y = row, X = slot)
- **Opacity**: morphological form (base/past/ing/s/er/est)
- **Size**: word length bucket
- **Tilt/rotation**: sequence position data

An AI scanner reads the rendered glyphs and extracts the full compressed data without
a decoder. A human reader sees structured visual patterns, not random bytes.

### Why it's last
It's a readability/UX feature, not compression. Everything before it is compression.
The visual layer is built ON TOP of the final locked format — any format change
invalidates the font.

### Expected compression gain
**Zero.** Visual properties encode the same information as bytes — they just present it
differently. Visual encoding is about making the data SCANNABLE, not smaller.

### When to build
Only after Hive deployment (Phase 8) is stable and the format is truly locked.

---

## Summary Table

| Phase | What | Effort | Expected Gain | Revert if... |
|-------|------|--------|---------------|--------------|
| 1 | Trigram phrases | Low | ❌ DITCHED | SA noise > signal |
| 2 | Expand phrase dict (50+) | Low | ❌ DITCHED | SA noise > signal |
| 3 | Blank system prototype (tier-1) | Medium | ❌ DITCHED | +92 bytes, all texts worse |
| 4 | Blank system full cascade | High | +2–5% | Phase 3 showed no gain |
| 5 | Morphological fallback | Medium | ✅ DONE | −8 bytes total, 0 regressions |
| 6 | SA re-training (maintenance) | Low | +0.1–0.5% per cycle | Never regresses (pure optimization) |
| 7 | Cross-sentence blank cascade | High | +0.5–1% | Phase 4 showed no gain |
| 8 | Hive deployment | High | N/A (infrastructure) | Not a compression phase |
| 9 | Visual encoding / scanner | Very High | 0% (readability only) | N/A |

---

## Current Baseline (v2.0, March 2026)

| Text | brotli | v2.0 | vs brotli |
|------|--------|------|-----------|
| Article x1 | 477 | 408 | +14.5% |
| Article x10 | 482 | 410 | +14.9% |
| Blog post | 325 | 253 | +22.2% |
| News | 583 | 487 | +16.5% |
| Tech doc | 555 | 491 | +11.5% |
| Story | 630 | 458 | +27.3% |
| Informal | 545 | 437 | +19.8% |
| All mixed | 2,898 | 2,247 | +22.5% |
| **Total** | **8,214** | **6,626** | **+19.3%** |

Every phase is measured against this table. Improvement = lower bytes. Any regression
on any row = revert.

---

## Decision Tree

```
Start each phase →
  Build minimum viable implementation →
    Run: python3 -m pytest tests/sequential/ -v
      FAIL → fix before benchmarking
      PASS →
        Run: python3 bench_rank_optimizer.py (if dict changed)
        Run: python3 bench_two_stage.py (or equivalent)
          ANY REGRESSION → git checkout [last-tag] and discard
          ALL BETTER OR EQUAL →
            git add -A && git commit && git tag vX.Y-[phase-name]
            Mark phase DONE, proceed to next
```

---

*Last updated: March 2026 — v2.0 base, 19.3% above brotli across 11 texts.*
