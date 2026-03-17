"""Full benchmark with 249K dictionary - find the crossover point."""
import gzip
import sys
sys.path.insert(0, '.')

from src.pipeline.compressor import Compressor
from src.pipeline.decompressor import Decompressor
from src.wordid.dictionary import Dictionary

d = Dictionary()
print(f"Dictionary: {d.size:,} words")
print(f"  'the' = rank {d.word_to_rank('the')}")
print(f"  'fox' = rank {d.word_to_rank('fox')}")
print(f"  'computer' = rank {d.word_to_rank('computer')}")
print()

# Realistic long text
ARTICLE = """The history of science is a story of human curiosity and determination. From the ancient
Greeks who first asked questions about the nature of the world to the modern researchers who
probe the depths of space and the structure of atoms, people have always been driven to
understand the universe around them. In the beginning, science was not separate from
philosophy. Thinkers like Aristotle and Plato tried to explain the world through reason
alone, without the benefit of experiments or measurements. It was not until the Renaissance
that the scientific method began to take shape. Francis Bacon argued that knowledge should
be built on observation and experiment, not just logic and tradition. Galileo turned his
telescope to the sky and discovered that the earth was not the center of the universe. Newton
showed that the same force that makes an apple fall from a tree also keeps the moon in orbit
around the earth. These discoveries changed the way people thought about the world and their
place in it. The industrial revolution brought science into everyday life. Steam engines,
railways, and factories transformed society. Medicine advanced as doctors began to understand
the causes of disease. In the twentieth century, science gave us computers, space travel,
and the ability to split the atom. Today, science continues to push the boundaries of what
we know and what we can do. From artificial intelligence to gene therapy, the frontiers of
knowledge are expanding faster than ever before."""

c = Compressor(dictionary=d)
dec = Decompressor(dictionary=d)

# Test different text lengths
print(f"{'Description':<30s} {'Raw':>5s} {'Ours':>5s} {'gzip':>5s} {'Ratio':>7s} {'OK':>3s}")
print("-" * 60)

tests = [
    ("1 sentence", "The quick brown fox jumped over the lazy dog."),
    ("3 sentences", "The quick brown fox jumped over the lazy dog. He was very fast and could not be caught. The dog tried his best but it was not enough."),
    ("Article (1 para)", ARTICLE),
    ("Article x2", ARTICLE + " " + ARTICLE),
    ("Article x5", " ".join([ARTICLE] * 5)),
    ("Article x10", " ".join([ARTICLE] * 10)),
]

for name, text in tests:
    text = " ".join(text.split())  # normalize whitespace
    blob = c.compress(text)
    result = dec.decompress(blob)
    raw = len(text.encode("utf-8"))
    gz = len(gzip.compress(text.encode("utf-8"), 9))
    ok = "Y" if result == text else "N"
    ratio = f"{len(blob)/raw:.1%}"
    print(f"{name:<30s} {raw:5d} {len(blob):5d} {gz:5d} {ratio:>7s}  {ok}")

print()

# Break down where bytes go for the article
blob = c.compress(" ".join(ARTICLE.split()))
print("Article byte breakdown:")
print(f"  Header: 16 bytes (fixed)")
# Rough breakdown from the blob structure
print(f"  Total blob: {len(blob)} bytes")
print(f"  Raw text: {len(ARTICLE.encode('utf-8'))} bytes")

# Show unique vs total words
from src.tokenizer.tokenizer import Tokenizer
from src.inverted_index.index_builder import IndexBuilder
tok = Tokenizer()
doc = tok.tokenize(" ".join(ARTICLE.split()))
idx = IndexBuilder().build(doc.tokens)
total = len(doc.tokens)
unique = len(idx.word_order)
known = sum(1 for w in idx.word_order if d.has_word(w))
print(f"  Total tokens: {total}")
print(f"  Unique words: {unique}")
print(f"  In dictionary: {known}/{unique} ({known/unique:.0%})")
avg_occurrences = total / unique
print(f"  Avg occurrences per word: {avg_occurrences:.1f}")
