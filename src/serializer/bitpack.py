"""
Bit-packing utilities for combined (row, slot) position encoding.

Each grid position = row * MAX_SLOTS + slot = 11 bits (0-1599).
Multiple positions are packed tightly into bytes with zero waste.

This replaces the separate vertical/horizontal encoding with a single
combined dimension, eliminating 4 bytes of length headers per word.
"""

from typing import List, Tuple

MAX_SLOTS = 16   # max word slots per 80-char line
MAX_ROWS = 256   # max lines in document (extended for large docs)
BITS_PER_POS = 12  # ceil(log2(4096)) = 12 bits per position (supports 256 rows x 16 slots)


def combine_position(row: int, slot: int) -> int:
    """Combine (row, slot) into a single 11-bit integer."""
    return row * MAX_SLOTS + slot


def split_position(combined: int) -> Tuple[int, int]:
    """Split a combined integer back into (row, slot)."""
    return (combined // MAX_SLOTS, combined % MAX_SLOTS)


def pack_positions(positions: List[Tuple[int, int]]) -> bytes:
    """
    Pack a list of (row, slot) positions into bit-packed bytes.

    Each position = 11 bits. Packed tightly, no padding between values.
    Final byte is padded with zero bits on the right.

    Returns: packed bytes.
    """
    if not positions:
        return b''

    # Convert to combined integers
    values = [combine_position(row, slot) for row, slot in positions]

    # Pack into bit stream
    total_bits = len(values) * BITS_PER_POS
    total_bytes = (total_bits + 7) // 8
    buf = bytearray(total_bytes)

    bit_offset = 0
    for val in values:
        # Write 11 bits of val starting at bit_offset
        for i in range(BITS_PER_POS):
            bit = (val >> (BITS_PER_POS - 1 - i)) & 1
            byte_idx = (bit_offset + i) // 8
            bit_idx = 7 - ((bit_offset + i) % 8)
            if bit:
                buf[byte_idx] |= (1 << bit_idx)
        bit_offset += BITS_PER_POS

    return bytes(buf)


def unpack_positions(data: bytes, count: int) -> List[Tuple[int, int]]:
    """
    Unpack bit-packed bytes into a list of (row, slot) positions.

    Args:
        data: packed bytes
        count: number of positions to unpack

    Returns: list of (row, slot) tuples.
    """
    if not data or count == 0:
        return []

    positions = []
    bit_offset = 0

    for _ in range(count):
        # Read 11 bits starting at bit_offset
        val = 0
        for i in range(BITS_PER_POS):
            byte_idx = (bit_offset + i) // 8
            bit_idx = 7 - ((bit_offset + i) % 8)
            if byte_idx < len(data):
                bit = (data[byte_idx] >> bit_idx) & 1
                val = (val << 1) | bit
            else:
                val = val << 1
        bit_offset += BITS_PER_POS

        positions.append(split_position(val))

    return positions


def packed_size(count: int) -> int:
    """Calculate packed byte size for N positions."""
    return (count * BITS_PER_POS + 7) // 8
