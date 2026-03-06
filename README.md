# Ancient High-Tech Symbol Compression System

A deterministic text compression system that transforms words into 1-bit visual symbols
with template-based positional reconstruction for Hive blockchain deployment.

**Target**: 5KB on-chain storage | 19.3:1 compression ratio | 100% reconstruction accuracy

---

## Core Philosophy

**Ancient/High-Tech**: Store only tiny codes on-chain. All intelligence lives in
pre-computed templates. Decoder reconstructs everything deterministically from codes + templates.

```
Raw Text → 1-bit Symbols + Position Codes → Hive Blockchain (5KB)
                                    ↓
                          Templates (client-side)
                                    ↓
                         100% Exact Reconstruction
```

---

## Project Structure

```
/
├── production_scanner.py                           # AUTHORITATIVE scanner
├── stepped-pipeline-server.py                      # Main 6-step pipeline
├── real-extraction-server.py                       # Content extraction
├── SIMPLE_WORD_SYMBOL_MAPPING_SYSTEM.py            # 249,777 word→symbol mappings
├── MICROSCOPIC_INTERNAL_LINE_ARCHITECTURE_2025.py  # Line positioning
├── COMPREHENSIVE_MORPHOLOGICAL_PATTERN_DETECTOR.py # 438 morphological patterns
├── CONTRACTION_SUPER_SYMBOL_INTEGRATION.py         # 36 contraction types
│
├── src/
│   └── coordinate_encoding/       # Coordinate Lookup Encoding System
│       ├── coordinate_encoder.py  # Tier-marker-free encoder
│       ├── coordinate_decoder.py  # Byte-length-based tier inference
│       ├── pattern_matcher.py     # Template lookup O(1)
│       ├── template_cache.py      # 8,946 pre-computed templates
│       ├── scanner_integration.py # Drop-in for production_scanner.py
│       ├── migration_utils.py     # Migration validator (2-tier guards)
│       └── templates/
│           └── coordinate_patterns/
│               ├── horizontal_coordinate_templates.json
│               └── vertical_coordinate_templates.json
│
├── tests/
│   └── coordinate_encoding/       # 54 tests, 100% passing
│
└── docs/
    ├── COORDINATE_ENCODING_TIER_MARKER_FREE_ARCHITECTURE.md
    ├── TEMPLATE_SYSTEM_DEEP_DIVE.md
    └── COORDINATE_ENCODING_EMPIRICAL_PERFORMANCE.md
```

---

## Coordinate Encoding System

The core innovation: encoding word positions as minimal template codes rather than raw arrays.

### How It Works

```
Word "the" appears 3 times at lines [1, 5, 10], positions [5, 15, 25]

WITHOUT encoding:  6 bytes (raw arrays)
WITH encoding:     4 bytes (2 template codes)

[word_symbol][vertical_code][horizontal_code]
    0x7E         0x0926         0x11D7
    1 byte       2 bytes        2 bytes = 5 bytes total for ALL 3 instances
```

### Template Tiers (Tier-Marker-FREE)

| Tier | Size    | Templates | Coverage                       |
|------|---------|-----------|--------------------------------|
| 0A   | 1 byte  | 16        | Ultra-common single positions  |
| 0B   | 1 byte  | 94        | Common 1-2 position patterns   |
| 1    | 2 bytes | 8,836     | 3-position patterns            |
| 2    | variable| unlimited | Delta encoding (any pattern)   |

**Key**: No tier marker bytes. Tier inferred from byte-length. Zero redundancy.

### Total Capacity

```
8,946 templates × 2 dimensions = 80+ million unique position combinations
```

### Performance

| Scenario                  | Storage    |
|---------------------------|------------|
| Single-instance word      | 3 bytes    |
| 3-instance word (Tier 1)  | 5 bytes    |
| 50-instance word (delta)  | ~103 bytes |
| vs. raw position arrays   | 40-60% smaller |

---

## Pipeline

```
Text → [Extract] → [Bin 1.0] → [Scan] → [Grid] → [Blank] → [Store] → [Reconstruct]
                                  ↓
                       TYPE 1: Morphological super symbols
                       TYPE 2: Word form super symbols
                       TYPE 3: Fixed sentence super symbols
                       TYPE 4: Contraction super symbols (36 types)
```

---

## Symbol System

Every word in the 250K Oxford dictionary has a permanent 1-byte symbol.
Symbols never change. Position data encoded separately via coordinate templates.

---

## Grid Dimensions

Document grid: **100 lines × 80 characters per line**

- Vertical templates: which lines (1-100) a word appears on
- Horizontal templates: which position (1-80) within each line
- Both dimensions encoded independently, paired in order during reconstruction

---

## Running

```bash
python stepped-pipeline-server.py   # Main pipeline
python real-extraction-server.py    # Content extraction
```

---

## Documentation

| File | Contents |
|------|----------|
| `replit.md` | Master architecture reference |
| `.cursorrules` | Cursor AI project guide |
| `docs/COORDINATE_ENCODING_TIER_MARKER_FREE_ARCHITECTURE.md` | Encoding design |
| `docs/TEMPLATE_SYSTEM_DEEP_DIVE.md` | How 8,946 templates work |
| `docs/COORDINATE_ENCODING_EMPIRICAL_PERFORMANCE.md` | Performance data |

---

**Stack**: Python · Flask · PostgreSQL · NLTK/WordNet · Hive Blockchain · pytest
