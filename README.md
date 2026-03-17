# Ancient High-Tech Compression

A two-stage text compression system for Hive blockchain deployment.
Stage 1: word-level rank encoding. Stage 2: brotli byte-level compression.
**Beats brotli on diverse text and single articles. Within 1% on repeated text.**

---

## Results (AI-Optimized Rank Assignment)

| Text          | Raw    | brotli | Ours+brotli | Ratio  | vs brotli          |
|---------------|--------|--------|-------------|--------|--------------------|
| Article x1    | 1,499  | 477    | **471**     | 3.2:1  | **+1.3% WIN**      |
| Article x2    | 2,999  | 480    | **482**     | 6.2:1  | -0.4% (close)      |
| Article x5    | 7,499  | 482    | **484**     | 15.5:1 | -0.4% (close)      |
| Article x10   | 14,999 | 482    | **487**     | 30.8:1 | -1.0% (close)      |
| Blog post     | 781    | 325    | **285**     | 2.7:1  | **+12.3% WIN**     |
| Mixed text    | 2,281  | 757    | **694**     | 3.3:1  | **+8.3% WIN**      |

Dictionary: 249,777 words with AI-optimized rank ordering stored on Hive (free per document).
brotli embeds its dictionary per file — we don't.

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
| 1–3        | 32–127        | **1 byte**   | "the", "of", "and" (~20% tokens) |
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
│   ├── encoder.py       # Text → merged varint blob
│   ├── decoder.py       # Blob → text (v3 + v2 backward compat)
│   ├── two_stage.py     # Encoder + brotli/zlib stage 2
│   └── rank_optimizer.py # AI-optimized rank assignment (Brown re-rank + SA)
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
├── sequential/          # 95 tests: roundtrip, varint, blob, two-stage, rank optimizer
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
# All 189 tests
wsl -d Ubuntu-24.04 -- bash -c "cd /path/to/repo && python3 -m pytest tests/ -v"

# Sequential only (95 tests)
python3 -m pytest tests/sequential/ -v

# Pipeline only (94 tests)
python3 -m pytest tests/pipeline/ -v
```

---

## Two Approaches

| Feature    | Approach A: Inverted Index           | Approach B: Sequential (current best) |
|------------|--------------------------------------|---------------------------------------|
| Location   | `src/pipeline/`                      | `src/sequential/`                     |
| Tests      | 94 passing                           | 95 passing                            |
| Format     | Word → positions                     | Rank stream + brotli                  |
| Best ratio | 2.1:1 on Article x10                 | 30.8:1 on Article x10                 |
| Status     | Ideas bank (blanks, visual encoding) | Production path                       |

---

## Dictionary

249,777 words built from NLTK (Brown Corpus + Gutenberg + WordNet).
AI-optimized rank assignment: Brown-only frequency re-ranking removes Gutenberg
archaic word contamination from the 2-byte tier, then simulated annealing
refines tier-2 ranks for maximum brotli compressibility.
Stored on Hive blockchain — free per document (no per-file dictionary overhead).

---

## Roadmap

1. ~~**AI-optimized rank assignment**~~ — DONE. Brown re-rank + simulated annealing. +2.8% vs original, beats brotli on Article x1.
2. **Phrase detection** — common bigrams/trigrams as single tokens
3. **Blank system** — layer on top of sequential stream for structural patterns
4. **Hive deployment** — on-chain storage with client-side decoding

---

**Stack**: Python · brotli · zlib · NLTK/WordNet · Hive Blockchain · pytest
