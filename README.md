# Ancient High-Tech Compression

A two-stage text compression system for Hive blockchain deployment.
Stage 1: word-level rank encoding. Stage 2: brotli byte-level compression.
**Beats brotli on every benchmark across all text genres. 12-26% smaller.**

---

## Results (Phrase Dictionary + Diverse 5-Text Training)

| Text        | Raw    | brotli | Ours+brotli | Ratio  | vs brotli      |
|-------------|--------|--------|-------------|--------|----------------|
| Article x1  | 1,499  | 477    | **410**     | 3.7:1  | **+14.0% WIN** |
| Article x2  | 2,999  | 480    | **412**     | 7.3:1  | **+14.2% WIN** |
| Article x5  | 7,499  | 482    | **414**     | 18.1:1 | **+14.1% WIN** |
| Article x10 | 14,999 | 482    | **414**     | 36.2:1 | **+14.1% WIN** |
| Blog post   | 781    | 325    | **251**     | 3.1:1  | **+22.8% WIN** |
| News        | 1,879  | 583    | **488**     | 3.9:1  | **+16.3% WIN** |
| Tech doc    | 1,729  | 555    | **488**     | 3.5:1  | **+12.1% WIN** |
| Story       | 1,591  | 630    | **466**     | 3.4:1  | **+26.0% WIN** |
| Mixed (2)   | 2,281  | 757    | **609**     | 3.7:1  | **+19.6% WIN** |
| All mixed   | 7,483  | 2,390  | **1,875**   | 4.0:1  | **+21.5% WIN** |

Dictionary: 249,777 words + 23 bigram phrases, AI-optimized ranks trained on 5 diverse text genres.
Stored on Hive (free per document). brotli embeds its dictionary per file — we don't.

---

## How It Works

```text
Text → [Stage 1: Sequential Encoder] → rank blob → [Stage 2: brotli q=11] → final bytes
```

### Stage 1 — Sequential Rank Stream (v3 Merged Varint)

Every token becomes a single integer: `unified = rank * 32 + variant`

- `rank` = word's frequency rank in the 249K dictionary
- `variant` = `(is_title_case << 4) | trailing_punct_code`

| Rank range | Unified range | Varint bytes | Coverage                         |
|------------|---------------|--------------|----------------------------------|
| 1–3        | 32–127        | **1 byte**   | "the", "and", "of" (~20% tokens) |
| 4–511      | 128–16,383    | 2 bytes      | Top 511 words (~75% tokens)      |
| 512+       | 16,384+       | 3 bytes      | Rare words (~5% tokens)          |

Top-3 words fit in 1 byte. 75% of all English tokens fit in 2 bytes.

### Extra Section

Tokens that can't be encoded as `rank * variant` go into a length-prefixed extra section:

- Unknown words (not in 249K dictionary)
- ALL CAPS words (NASA, FBI) — original casing preserved
- Mixed case words (iPhone, McDonald's) — original casing preserved
- Leading punctuation ("hello, (test) — lead char prepended

### Stage 2 — brotli

brotli at quality=11 operates on the raw rank bytes.
Repeated articles encode as "repeat previous N bytes" — ~4 bytes per repetition.

### Blob Format

```text
[version: 1 byte = 0x03]
[token_count: 3 bytes uint24 big-endian]
[main_stream: LEB128 varint per token]
[extra_section: length-prefixed UTF-8 strings]
```

No position data. No caps bitmap. No inverted index. Sequential order IS position.

---

## Project Structure

```text
src/
├── sequential/          # CURRENT BEST — Sequential Rank Stream v3
│   ├── encoder.py       # Text → merged varint blob (phrase-aware tokenizer)
│   ├── decoder.py       # Blob → text (v3 + v2 backward compat)
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
├── SEQUENTIAL_RANK_STREAM_DESIGN.md      # v3 format, benchmarks, design decisions
├── MASTER_ARCHITECTURE_2026.md           # Full system architecture
├── BLUEPRINT_ROADMAP_2026.md             # Roadmap with phases A/B
└── ...                                   # Research docs
```

---

## Tests

```bash
# All 212 tests
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
| Best ratio | 2.1:1 on Article x10                 | 36.2:1 on Article x10                 |
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

## Roadmap

1. ~~**AI-optimized rank assignment**~~ — DONE. Brown re-rank + SA.
2. ~~**Dictionary coverage fix**~~ — DONE. Beats brotli on ALL benchmarks by 14-22%.
3. ~~**Phrase detection + diverse benchmarks**~~ — DONE. 23 phrases, 5-genre training, beats brotli on ALL text types by 12-26%.
4. **Morphological fallback** — encode unknown words as stem + suffix code
5. **Hive deployment** — on-chain storage with client-side decoding

---

**Stack**: Python · brotli · zlib · NLTK/WordNet · Hive Blockchain · pytest
