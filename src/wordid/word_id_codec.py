"""
Variable-length word ID encoding.

Prefix-free coding (like UTF-8) for frequency ranks:
  Rank 1-127:          1 byte   0xxxxxxx
  Rank 128-16,511:     2 bytes  10xxxxxx xxxxxxxx
  Rank 16,512-249,777: 3 bytes  11xxxxxx xxxxxxxx xxxxxxxx
  Unknown (rank 0):    0x00 + length(1 byte) + UTF-8 bytes
"""

from typing import Tuple


class WordIdCodec:

    def encode_rank(self, rank: int) -> bytes:
        """Encode a frequency rank (1-249777) to 1-3 bytes."""
        if rank <= 0 or rank > 249_777:
            raise ValueError(f"Rank {rank} out of range [1, 249777]")

        if rank <= 127:
            return bytes([rank])

        if rank <= 16_511:
            adjusted = rank - 128
            byte1 = 0x80 | (adjusted >> 8)
            byte2 = adjusted & 0xFF
            return bytes([byte1, byte2])

        adjusted = rank - 16_512
        byte1 = 0xC0 | (adjusted >> 16)
        byte2 = (adjusted >> 8) & 0xFF
        byte3 = adjusted & 0xFF
        return bytes([byte1, byte2, byte3])

    def decode_rank(self, data: bytes, offset: int = 0) -> Tuple[int, int]:
        """Decode rank from bytes at offset. Returns (rank, bytes_consumed)."""
        if offset >= len(data):
            raise ValueError(f"Offset {offset} beyond data length {len(data)}")

        first = data[offset]

        if first == 0x00:
            # Unknown word marker - not a rank
            raise ValueError("Encountered unknown word marker (0x00), use decode_unknown()")

        if first & 0x80 == 0:
            # 1-byte: 0xxxxxxx
            return (first, 1)

        if first & 0xC0 == 0x80:
            # 2-byte: 10xxxxxx xxxxxxxx
            if offset + 1 >= len(data):
                raise ValueError("Incomplete 2-byte rank encoding")
            val = ((first & 0x3F) << 8) | data[offset + 1]
            return (val + 128, 2)

        # 3-byte: 11xxxxxx xxxxxxxx xxxxxxxx
        if offset + 2 >= len(data):
            raise ValueError("Incomplete 3-byte rank encoding")
        val = ((first & 0x3F) << 16) | (data[offset + 1] << 8) | data[offset + 2]
        return (val + 16_512, 3)

    def encode_unknown(self, word: str) -> bytes:
        """Encode an unknown word (not in dictionary) as 0x00 + length + UTF-8."""
        word_bytes = word.encode('utf-8')
        if len(word_bytes) > 255:
            raise ValueError(f"Unknown word too long: {len(word_bytes)} bytes")
        return bytes([0x00, len(word_bytes)]) + word_bytes

    def decode_unknown(self, data: bytes, offset: int = 0) -> Tuple[str, int]:
        """Decode an unknown word. Returns (word, bytes_consumed)."""
        if data[offset] != 0x00:
            raise ValueError("Not an unknown word marker")
        length = data[offset + 1]
        word_bytes = data[offset + 2: offset + 2 + length]
        return (word_bytes.decode('utf-8'), 2 + length)

    def is_unknown_marker(self, data: bytes, offset: int = 0) -> bool:
        """Check if byte at offset is the unknown word marker."""
        return offset < len(data) and data[offset] == 0x00
