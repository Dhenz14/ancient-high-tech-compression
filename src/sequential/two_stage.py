"""
Two-Stage Compressor: Sequential rank stream + byte-level compression.

Stage 1: Text → sequential unified ranks (word-level compression)
Stage 2: Rank stream → brotli/zlib (byte-level compression)

This combines our word-level intelligence with the world's best
byte-level compressors for maximum compression.
"""

import zlib
from typing import Optional
from ..wordid.dictionary import Dictionary
from .encoder import SequentialEncoder
from .decoder import SequentialDecoder

try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False


class TwoStageCompressor:
    """Compress text using word-level + byte-level stages."""

    def __init__(self, dictionary: Optional[Dictionary] = None,
                 method: str = "brotli"):
        """
        Args:
            dictionary: word-rank dictionary
            method: "brotli", "zlib", or "none" (no stage 2)
        """
        self.dictionary = dictionary or Dictionary()
        self.stage1 = SequentialEncoder(self.dictionary)
        self.method = method

    def compress(self, text: str) -> bytes:
        """Compress text through both stages."""
        # Stage 1: word-level encoding
        rank_blob = self.stage1.encode(text)

        # Stage 2: byte-level compression
        if self.method == "brotli" and HAS_BROTLI:
            compressed = brotli.compress(rank_blob, quality=11)
        elif self.method == "zlib":
            compressed = zlib.compress(rank_blob, 9)
        else:
            compressed = rank_blob

        # Wrap with method indicator
        if self.method == "brotli":
            header = b'\x42'  # 'B' for brotli
        elif self.method == "zlib":
            header = b'\x5A'  # 'Z' for zlib
        else:
            header = b'\x4E'  # 'N' for none

        return header + compressed

    def decompress(self, blob: bytes) -> str:
        """Decompress through both stages in reverse."""
        method_byte = blob[0]
        compressed = blob[1:]

        # Stage 2 reverse: byte-level decompression
        if method_byte == 0x42 and HAS_BROTLI:  # brotli
            rank_blob = brotli.decompress(compressed)
        elif method_byte == 0x5A:  # zlib
            rank_blob = zlib.decompress(compressed)
        else:  # none
            rank_blob = compressed

        # Stage 1 reverse: word-level decoding
        decoder = SequentialDecoder(self.dictionary)
        return decoder.decode(rank_blob)
