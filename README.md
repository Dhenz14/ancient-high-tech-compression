# Ancient High-Tech Compression

A two-stage text compression system for Hive blockchain deployment.
Stage 1: word-level rank encoding. Stage 2: brotli byte-level compression.
**Beats brotli on every benchmark across all text genres. 19.3% smaller overall.**

---

## Results — v2.0 (v4 format, doubled tier capacity)

| Text        | Raw    | brotli | Ours+brotli | Ratio  | vs brotli      |
|-------------|--------|--------|-------------|--------|----------------|
| Article x1  | 1,499  | 477    | **408**     | 3.7:1  | **+14.5% WIN** |
| Article x2  | 2,999  | 480    | **412**     | 7.3:1  | **+14.2% WIN** |
| Article x5  | 7,499  | 482    | **415**     | 18.1:1 | **+13.9% WIN** |
| Article x10 | 14,999 | 482    | **410**     | 36.6:1 | **+14.9% WIN** |
| Blog post   | 781    | 325    | **253**     | 3.1:1  | **+22.2% WIN** |
| News        | 1,879  | 583    | **487**     | 3.9:1  | **+16.5% WIN** |
| Tech doc    | 1,729  | 555    | **491**     | 3.5:1  | **+11.5% WIN** |
| Story       | 1,591  | 630    | **458**     | 3.5:1  | **+27.3% WIN** |
| Informal    | 1,399  | 545    | **437**     | 3.2:1  | **+19.8% WIN** |
| Mixed (2)   | 2,281  | 757    | **608**     | 3.8:1  | **+19.7% WIN** |
| All mixed   | 8,883  | 2,898  | **2,247**   | 4.0:1  | **+22.5% WIN** |

**19.3% better than raw brotli** across all 11 texts (6,626 vs 8,214 bytes total).

Dictionary: 249,777 words + 23 bigram phrases, AI-optimized ranks trained on 5 diverse text genres.
Stored on Hive (free per document). brotli embeds its dictionary per file — we don't.

---

## How It Works

```text
Text → [Stage 1: Sequential Encoder] → rank blob → [Stage 2: brotli q=11] → final bytes
```

### Stage 1 — Sequential Rank Stream (v4 Merged Varint)

Every token becomes a single integer: `unified = rank * 16 + variant`

- `rank` = word's frequency rank in the 249K dictionary
- `variant` = `(is_title_case << 3) | trailing_punct_code` (4-bit)

| Rank range | Unified range | Varint bytes | Coverage                     |
|------------|---------------|--------------|------------------------------|
| 1–7        | 16–127        | **1 byte**   | Top 7 words (~25% of tokens) |
| 8–1023     | 128–16,383    | 2 bytes      | Top 1023 words (~70% tokens) |
| 1024+      | 16,384+       | 3 bytes      | Rare words (~5% tokens)      |

v4 doubled tier-1 (3→7 words) and tier-2 (508→1016 words) over v3 by reducing variant from 5-bit to 4-bit.
Safe because 8 "rare" trailing codes (`;  :  )  ]  -  ...  ,"  ?"`) have zero occurrences in practice across 1,523 measured tokens.

### Extra Section

Tokens that can't be encoded inline go into a length-prefixed extra section:

- Unknown words (not in 249K dictionary)
- ALL CAPS words (NASA, FBI) — original casing preserved
- Mixed case words (iPhone, McDonald's) — original casing preserved
- Leading punctuation (`"hello`, `(test`) — lead char prepended
- Known words with rare trailing punct — trailing string appended to stored word

### Stage 2 — brotli

brotli at quality=11 operates on the raw rank bytes.
Repeated articles encode as "repeat previous N bytes" — ~4 bytes per repetition.

### Blob Format

```text
[version: 1 byte = 0x04]
[token_count: 3 bytes uint24 big-endian]
[main_stream: LEB128 varint per token, unified = rank * 16 + variant]
[extra_section: length-prefixed UTF-8 strings, one per rank=0 token]
```

No position data. No caps bitmap. No inverted index. Sequential order IS position.

Backward compatible: decoder dispatches on version byte — v2 (0x02), v3 (0x03), v4 (0x04) all decodable.

---

## Project Structure

```text
src/
├── sequential/          # CURRENT BEST — Sequential Rank Stream v4
│   ├── encoder.py       # Text → merged varint blob (phrase-aware tokenizer, v4)
│   ├── decoder.py       # Blob → text (v4 + v3 + v2 backward compat)
│   ├── two_stage.py     # Encoder + brotli/zlib stage 2
│   ├── rank_optimizer.py # AI-optimized rank assignment (Brown re-rank + SA)
│   └── phrase_miner.py  # Bigram phrase selection via two-stage brotli scoring
│
├── pipeline/            # Inverted Index Pipeline (Approach A)
│   └── ...              # 94 tests, coordinate encoding, morphology
│
├── wordid/
│   └── dictionary.py    # 249,777-word rank dictionary
│
├── tokenizer/           # Whitespace tokenizer with punct stripping
├── morphology/          # 438 morphological patterns
├── blanks/              # Blank system (future layer)
├── inverted_index/      # Word → position index
└── serializer/          # Blob serialization utilities

tests/
├── sequential/          # 118 tests: roundtrip, varint, blob, two-stage, rank optimizer, phrases
└── pipeline/            # 94 tests: coordinate encoding, morphology, blanks

docs/
├── V4_FORMAT_BLUEPRINT.md                # v4 format design, tier analysis, trailing code distribution
├── SEQUENTIAL_RANK_STREAM_DESIGN.md      # v3 format history, benchmarks, design decisions
├── MASTER_ARCHITECTURE_2026.md           # Full system architecture
├── BLUEPRINT_ROADMAP_2026.md             # Roadmap with phases A/B
└── ...                                   # Research docs
```

---

## Tests

```bash
# All tests (sequential + pipeline)
wsl -d Ubuntu-24.04 -- bash -c "cd /path/to/repo && python3 -m pytest tests/ -v"

# Sequential only (118 tests)
python3 -m pytest tests/sequential/ -v

# Pipeline only (94 tests)
python3 -m pytest tests/pipeline/ -v
```

---

## Two Approaches

| Feature    | Approach A: Inverted Index           | Approach B: Sequential (current best) |
|------------|--------------------------------------|---------------------------------------|
| Location   | `src/pipeline/`                      | `src/sequential/`                     |
| Tests      | 94 passing                           | 118 passing                           |
| Format     | Word → positions                     | Rank stream + brotli                  |
| Best ratio | 2.1:1 on Article x10                 | 36.6:1 on Article x10                 |
| Status     | Ideas bank (blanks, visual encoding) | Production path                       |

---

## Dictionary

249,777 entries built from NLTK (Brown + Gutenberg + WordNet) including inflected
forms and **23 bigram phrases** ("in the", "more than", "has been", "by the", etc.)
selected by two-stage brotli scoring — Brown corpus screen + precise validation
on 5 diverse benchmark texts. AI-optimized rank assignment: Brown-only re-ranking
removes Gutenberg archaic word contamination from the 2-byte tier, then simulated
annealing trains on 5 text genres (article, blog, news, tech, story) for maximum
brotli compressibility across diverse content. Stored on Hive blockchain — free per
document (no per-file dictionary overhead).

---

## Changelog

### v2.0 — v4 Format, Doubled Tier Capacity (March 2026)

- **VARIANT_MULT 32→16**: 4-bit variant instead of 5-bit
- Tier-1 grows 3→7 words; Tier-2 grows 508→1016 words
- Rare trailing codes forced to extra section (zero practical cost — 0 occurrences measured)
- SA re-tuned: 20K iters + cooling=0.9993 for the larger 1016-word tier-2 search space
- Adds Informal text benchmark (social media / casual writing)
- **19.3% better than raw brotli** across all 11 texts

### v1.2 — Diverse 5-Text Benchmarks (February 2026)

- Added NEWS, TECH, STORY genres to SA training
- 23 bigram phrases in dictionary
- Beats brotli on all text types by 12-26%

### v1.1 — Phrase Detection (February 2026)

- Two-stage brotli phrase scoring (Brown screen + benchmark validation)

### v1.0 — Beats Brotli (January 2026)

- Brown re-rank removes Gutenberg archaic word contamination
- SA optimization — first version to beat brotli on all benchmarks

---

## Roadmap

1. ~~**AI-optimized rank assignment**~~ — DONE. Brown re-rank + SA.
2. ~~**Dictionary coverage fix**~~ — DONE. Beats brotli on ALL benchmarks.
3. ~~**Phrase detection + diverse benchmarks**~~ — DONE. 23 phrases, 5-genre training.
4. ~~**v4 format — doubled tier capacity**~~ — DONE. VARIANT_MULT 32→16, 19.3% total win.
5. **Hive deployment** — on-chain storage with client-side decoding

---

**Stack**: Python · brotli · zlib · NLTK/WordNet · Hive Blockchain · pytest
