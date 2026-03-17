"""Quick benchmark with bitpacked positions."""
import gzip
from src.pipeline.compressor import Compressor
from src.pipeline.decompressor import Decompressor
from src.wordid.dictionary import Dictionary

d = Dictionary()

ARTICLE = "The history of science is a story of human curiosity and determination. From the ancient Greeks who first asked questions about the nature of the world to the modern researchers who probe the depths of space and the structure of atoms, people have always been driven to understand the universe around them. In the beginning, science was not separate from philosophy. Thinkers like Aristotle and Plato tried to explain the world through reason alone, without the benefit of experiments or measurements. It was not until the Renaissance that the scientific method began to take shape. Francis Bacon argued that knowledge should be built on observation and experiment, not just logic and tradition. Galileo turned his telescope to the sky and discovered that the earth was not the center of the universe. Newton showed that the same force that makes an apple fall from a tree also keeps the moon in orbit around the earth. These discoveries changed the way people thought about the world and their place in it. The industrial revolution brought science into everyday life. Steam engines, railways, and factories transformed society. Medicine advanced as doctors began to understand the causes of disease. In the twentieth century, science gave us computers, space travel, and the ability to split the atom. Today, science continues to push the boundaries of what we know and what we can do. From artificial intelligence to gene therapy, the frontiers of knowledge are expanding faster than ever before."

tests = [
    ("Article x1", " ".join(ARTICLE.split())),
    ("Article x2", " ".join((ARTICLE + " " + ARTICLE).split())),
    ("Article x5", " ".join((" ".join([ARTICLE]*5)).split())),
    ("Article x10", " ".join((" ".join([ARTICLE]*10)).split())),
]

header = "%-15s %5s %5s %5s %7s %3s" % ("Text", "Raw", "Ours", "gzip", "Ratio", "OK")
print(header)
print("-" * 45)

for name, text in tests:
    c = Compressor(dictionary=d)
    dec = Decompressor(dictionary=d)
    blob = c.compress(text)
    gz = len(gzip.compress(text.encode("utf-8"), 9))
    raw = len(text.encode("utf-8"))
    ok = "Y" if dec.decompress(blob) == text else "N"
    ratio = "%.1f%%" % (len(blob) / raw * 100)
    print("%-15s %5d %5d %5d %7s  %s" % (name, raw, len(blob), gz, ratio, ok))
