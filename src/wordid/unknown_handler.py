"""
Unknown word handler: encode/decode words not in the dictionary.

Format: 0x00 + length(1 byte) + UTF-8 bytes
"""

from typing import Tuple


class UnknownHandler:

    @staticmethod
    def encode(word: str) -> bytes:
        """Encode an unknown word as 0x00 + length + UTF-8."""
        word_bytes = word.encode('utf-8')
        if len(word_bytes) > 255:
            raise ValueError(f"Word too long for inline encoding: {len(word_bytes)} bytes")
        return bytes([0x00, len(word_bytes)]) + word_bytes

    @staticmethod
    def decode(data: bytes, offset: int = 0) -> Tuple[str, int]:
        """Decode an unknown word. Returns (word, bytes_consumed)."""
        if data[offset] != 0x00:
            raise ValueError("Not an unknown word marker")
        length = data[offset + 1]
        word_bytes = data[offset + 2: offset + 2 + length]
        return (word_bytes.decode('utf-8'), 2 + length)
