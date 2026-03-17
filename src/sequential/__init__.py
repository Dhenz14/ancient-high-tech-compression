"""
Sequential Rank Stream compressor — experimental approach.
Stores words as a sequential stream of unified ranks (word + caps + punct in one number).
Designed to be fed into brotli/zlib for byte-level compression on top.
Exists alongside the inverted index pipeline (src/pipeline/).
"""
from .encoder import SequentialEncoder
from .decoder import SequentialDecoder
