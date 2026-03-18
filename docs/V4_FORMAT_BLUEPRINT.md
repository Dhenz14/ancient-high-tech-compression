# v4 Format Blueprint — VARIANT_MULT=16

## The Problem

v3 uses a 5-bit variant per token: `[caps:1][trailing:4]`
This forces VARIANT_MULT=32, which hard-caps tier-2 at 508 words.

Empirical measurement (1,523 tokens, 6 diverse genres):
- Only 4 of the 16 trailing codes ever appear in practice
- 8 "rare" codes (;  :  )  ]  -  ...  ,"  ?") = 0 occurrences
- We're paying 5 bits to encode a 2-bit problem

## The Fix

Reduce variant to 4 bits: `[caps:1][trailing:3]` → VARIANT_MULT=16.

### New Tier Boundaries

```
unified = rank * 16 + variant   (variant: 0-15)

Tier 1 (1-byte varint):  unified 0–127   → ranks 0–7    (was ranks 0–3)
Tier 2 (2-byte varint):  unified 128–16383 → ranks 8–1023  (was ranks 4–511)
Tier 3 (3-byte varint):  unified 16384+  → ranks 1024+  (was ranks 512+)
```

Tier-1 grows from 3 → **7 words** (to, a, in, that join the, of, and).
Tier-2 grows from 508 → **1016 words** (doubles).

### New Trailing Codes (3 bits, 8 values)

| Code | Meaning | Frequency |
|------|---------|-----------|
| 0 | none | 89.4% |
| 1 | . | 6.5% |
| 2 | , | 3.9% |
| 3 | ! | ~0% (common in fiction) |
| 4 | ? | 0.1% |
| 5 | ' (close-single / possessive) | ~0% |
| 6 | " (close-double) | ~0% |
| 7 | ." (period-quote, dialogue) | ~0% |

Rare codes (;  :  )  ]  -  ...  ,"  ?") → word goes to **extra section**, trailing string appended to stored word. Zero-cost in practice.

### Rare Trailing Handling

When a token has rare trailing (encoder-side):
1. Note `rare_trail_str = _TRAIL_STRING[trail]`
2. Reset `trail = T_NONE`
3. Force `go_extra = True`
4. Store `lead_char + original + rare_trail_str` in extra section
5. Variant in main stream = `T_NONE`

Decoder sees `rank=0, trail=0 (T_NONE)`, reads extra section word (which already contains the trailing), appends nothing. Fully lossless.

### Variant Encoding

```python
# Known word (main stream):
variant = (is_cap << 3) | (trail & 0x07)   # 4-bit
unified = rank * 16 + variant

# Extra section (rank=0 in main stream):
variant = trail & 0x07                      # caps bit unused (original casing in extra section)
unified = 0 * 16 + variant = variant
```

---

## Expected Gains (pre-SA)

From measurement: 295 bytes pre-brotli across 6 texts.

| Text | Pre-brotli | Est. final |
|------|-----------|------------|
| Article | +38 bytes | ~+17 bytes |
| Blog | +18 bytes | ~+8 bytes |
| News | +64 bytes | ~+29 bytes |
| Tech | +60 bytes | ~+27 bytes |
| Story | +52 bytes | ~+24 bytes |
| Informal | +40 bytes | ~+18 bytes |

After SA re-trains on new tier boundaries: additional improvement expected (~2-3% more).
**Overall: ~5-8% improvement** over v1.2 baseline.

---

## Files Changed

| File | Change |
|------|--------|
| `src/sequential/encoder.py` | VERSION=0x04, VARIANT_MULT=16, new T_* constants, rare-trail handling |
| `src/sequential/decoder.py` | Add `_decode_v4()`, dispatch on version byte, keep v3/v2 paths |
| `src/sequential/rank_optimizer.py` | Fix `_fast_encode()` variant formula (bit 3 not bit 4) |
| `tests/sequential/test_roundtrip.py` | Update 2 version-byte assertions 0x03 → 0x04 |
| `optimized_dictionary_cache.json` | Re-generate via `bench_rank_optimizer.py` (SA re-trains) |

---

## Backward Compatibility

Old v3 blobs (on Hive blockchain) remain fully decodable. The decoder dispatches by version byte:
- `0x02` → `_decode_v2()` (legacy)
- `0x03` → `_decode_v3()` (previous)
- `0x04` → `_decode_v4()` (new)

New encoder always writes v4. New decoder reads all versions.
