"""
Two-stage compression: Our word-level encoding + best byte-level compressor.
Can we beat the world's best by chaining them?
"""
import gzip
import zlib
import sys
sys.path.insert(0, '.')

from src.pipeline.compressor import Compressor
from src.pipeline.decompressor import Decompressor
from src.wordid.dictionary import Dictionary

try:
    import brotli
    has_brotli = True
except ImportError:
    has_brotli = False

try:
    import zstandard
    has_zstd = True
except ImportError:
    has_zstd = False

d = Dictionary()

ARTICLE = "The history of science is a story of human curiosity and determination. From the ancient Greeks who first asked questions about the nature of the world to the modern researchers who probe the depths of space and the structure of atoms, people have always been driven to understand the universe around them. In the beginning, science was not separate from philosophy. Thinkers like Aristotle and Plato tried to explain the world through reason alone, without the benefit of experiments or measurements. It was not until the Renaissance that the scientific method began to take shape. Francis Bacon argued that knowledge should be built on observation and experiment, not just logic and tradition. Galileo turned his telescope to the sky and discovered that the earth was not the center of the universe. Newton showed that the same force that makes an apple fall from a tree also keeps the moon in orbit around the earth. These discoveries changed the way people thought about the world and their place in it. The industrial revolution brought science into everyday life. Steam engines, railways, and factories transformed society. Medicine advanced as doctors began to understand the causes of disease. In the twentieth century, science gave us computers, space travel, and the ability to split the atom. Today, science continues to push the boundaries of what we know and what we can do. From artificial intelligence to gene therapy, the frontiers of knowledge are expanding faster than ever before."

BLOG = "I was walking down the street yesterday when I saw something that completely changed my perspective on life. There was an old man sitting on a bench, feeding pigeons, and he looked so peaceful and content. I stopped and talked to him for a while. He told me he had been coming to that same bench every day for thirty years, ever since his wife passed away. He said the pigeons were his friends now, and they never judged him or asked him to be anything other than what he was. I think about that conversation often. In our busy lives, we forget that happiness does not come from having more things or being more successful. It comes from simple moments of connection and peace. The old man on the bench had figured out something that most of us spend our whole lives searching for."

CODE = """def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result"""

texts = {
    "Article x1": " ".join(ARTICLE.split()),
    "Article x5": " ".join((" ".join([ARTICLE]*5)).split()),
    "Article x10": " ".join((" ".join([ARTICLE]*10)).split()),
    "Blog post": " ".join(BLOG.split()),
    "Code": CODE,
    "Mixed": " ".join((ARTICLE + " " + BLOG).split()),
}

print("=" * 85)
print("TWO-STAGE COMPRESSION: Our encoding + byte-level compressor on top")
print("=" * 85)
print()

header = "%-14s %5s | %6s %6s %6s | %6s %6s %6s | %s" % (
    "Text", "Raw",
    "brotli", "gzip", "zstd",
    "Ours", "+gzip", "+brot",
    "Winner"
)
print(header)
print("-" * 85)

for name, text in texts.items():
    raw_bytes = text.encode("utf-8")
    raw = len(raw_bytes)

    # Stage 1: Our word-level compression
    c = Compressor(dictionary=d)
    dec = Decompressor(dictionary=d)
    our_blob = c.compress(text)
    our_size = len(our_blob)

    # Verify round-trip
    roundtrip = dec.decompress(our_blob)
    ok = roundtrip == text

    # Standalone compressors (the competition)
    gz_raw = len(gzip.compress(raw_bytes, 9))
    br_raw = len(brotli.compress(raw_bytes, quality=11)) if has_brotli else 0
    zstd_raw = len(zstandard.ZstdCompressor(level=22).compress(raw_bytes)) if has_zstd else 0

    # Two-stage: our blob + gzip
    our_plus_gz = len(gzip.compress(our_blob, 9))

    # Two-stage: our blob + brotli
    our_plus_br = len(brotli.compress(our_blob, quality=11)) if has_brotli else 0

    # Find winner
    all_sizes = {
        "brotli": br_raw,
        "gzip": gz_raw,
        "zstd": zstd_raw,
        "ours+gz": our_plus_gz,
        "ours+br": our_plus_br,
    }
    winner = min(all_sizes, key=lambda k: all_sizes[k] if all_sizes[k] > 0 else 99999)
    winner_size = all_sizes[winner]

    rt = "Y" if ok else "N"
    print("%-14s %5d | %6d %6d %6d | %6d %6d %6d | %s (%d, %.0f:1) %s" % (
        name, raw,
        br_raw, gz_raw, zstd_raw,
        our_size, our_plus_gz, our_plus_br,
        winner, winner_size, raw/winner_size if winner_size > 0 else 0,
        rt
    ))

print()
print("LEFT: standalone compressors (they include their own dictionary)")
print("RIGHT: our word-level encoding + byte-level on top (dictionary on Hive = free)")
print()

print("=" * 85)
print("WHAT THIS MEANS")
print("=" * 85)
print("""
Two-stage approach: Our word-level pre-processing + brotli on our blob.

If our two-stage beats standalone brotli:
  We WIN because our dictionary is on Hive (free).
  brotli includes its dictionary per file (overhead).
  We get brotli-quality compression with ZERO dictionary tax.

If standalone brotli beats our two-stage:
  We need better word-level pre-processing to create a more
  compressible blob. The blob has patterns brotli can exploit.
  Better blank system + less metadata = more compressible blob.
""")

# What would it take to hit 20:1?
print("=" * 85)
print("THE PATH TO 20:1")
print("=" * 85)
for name, text in texts.items():
    raw = len(text.encode("utf-8"))
    target_20 = raw // 20
    c = Compressor(dictionary=d)
    our_blob = c.compress(text)
    our_plus_br = len(brotli.compress(our_blob, quality=11)) if has_brotli else 0
    gap = our_plus_br - target_20
    current_ratio = raw / our_plus_br if our_plus_br > 0 else 0

    print("  %-14s raw=%5d  target(20:1)=%4d  ours+brotli=%4d  gap=%+4d  current=%.1f:1" % (
        name, raw, target_20, our_plus_br, gap, current_ratio
    ))
