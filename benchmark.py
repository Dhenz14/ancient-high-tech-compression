"""Final benchmark: Phase 1-3 compression system."""
import gzip
import sys
sys.path.insert(0, '.')

from src.pipeline.compressor import Compressor
from src.pipeline.decompressor import Decompressor
from src.wordid.dictionary import Dictionary

d = Dictionary()
c = Compressor(dictionary=d)
dec = Decompressor(dictionary=d)

texts = {
    "Short sentence": "The quick brown fox jumped over the lazy dog.",
    "Paragraph": (
        "I have a dog. The dog is good. He was my best friend. "
        "She said that the world is not what it was before. "
        "They were all very happy about the new house by the river. "
        "He had been there before but could not find his way back. "
        "The old man said he would make time for his family."
    ),
    "Repeated x20": " ".join(["The quick brown fox jumped over the lazy dog."] * 20),
    "Repeated x50": " ".join(["The quick brown fox jumped over the lazy dog."] * 50),
}

print("=" * 70)
print("ANCIENT HIGH-TECH COMPRESSION - Phase 1-3 Benchmark")
print("=" * 70)
print(f"Dictionary: {d.size} words (bootstrap; full 249K in Phase 5)")
print()

header = f"{'Text':<20s} {'Raw':>5s} {'Ours':>5s} {'gzip':>5s} {'Ratio':>7s} {'vs_gz':>6s} {'OK':>3s}"
print(header)
print("-" * 70)

for name, text in texts.items():
    blob = c.compress(text)
    raw = len(text.encode("utf-8"))
    gz = len(gzip.compress(text.encode("utf-8"), 9))

    result = dec.decompress(blob)
    ok = "Y" if result == text else "N"
    ratio = f"{len(blob)/raw:.1%}"
    vs_gz = f"{len(blob)/gz:.1f}x"

    print(f"{name:<20s} {raw:5d} {len(blob):5d} {gz:5d} {ratio:>7s} {vs_gz:>6s}  {ok:>2s}")

print()
print("NOTE: Our system excludes dictionary from compressed size (stored on")
print("      Hive blockchain once, free forever). gzip is self-contained.")
print()

# Verify all round-trips
all_ok = True
for name, text in texts.items():
    blob = c.compress(text)
    result = dec.decompress(blob)
    if result != text:
        all_ok = False
        print(f"  FAIL: {name}")

if all_ok:
    print("Round-trip: ALL PASS - 100% lossless word-for-word reconstruction")
