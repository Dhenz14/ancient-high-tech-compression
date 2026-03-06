#!/usr/bin/env python3
"""
BIT PACKER - Tier 0A 4-bit Code Packing Utilities
==================================================
Coordinate Lookup Encoding System - Phase 2

Efficient packing/unpacking of 4-bit codes for Tier 0A patterns
Packs 2 codes per byte for maximum density

Dr. Thompson (Mathematical Optimization Lead)
"""

from typing import List, Tuple


class BitPacker:
    """
    Utilities for packing/unpacking 4-bit Tier 0A coordinate codes
    
    Tier 0A uses 4-bit codes (0-15) for ultra-common single-line patterns
    Packs 2 codes per byte: [high nibble][low nibble]
    """
    
    def __init__(self):
        """Initialize bit packer"""
        self.bits_per_code = 4
        self.codes_per_byte = 2
        self.max_code_value = 15  # 2^4 - 1
    
    def pack_codes(self, codes: List[int]) -> bytes:
        """
        Pack list of 4-bit codes into bytes
        
        Args:
            codes: List of code values (0-15)
        
        Returns:
            Packed bytes (2 codes per byte)
        
        Raises:
            ValueError: If code value exceeds 4-bit range
        
        Example:
            >>> packer = BitPacker()
            >>> packer.pack_codes([3, 7, 15, 0])
            b'7\\xf0'  # 0x37, 0xf0
        """
        if not codes:
            return b''
        
        # Validate all codes are in 4-bit range
        for i, code in enumerate(codes):
            if not isinstance(code, int) or code < 0 or code > self.max_code_value:
                raise ValueError(
                    f"Code at index {i} ({code}) exceeds 4-bit range (0-{self.max_code_value})"
                )
        
        packed_bytes = []
        
        # Process codes in pairs
        for i in range(0, len(codes), 2):
            high_nibble = codes[i]
            
            # If odd number of codes, pad last byte with 0
            low_nibble = codes[i + 1] if i + 1 < len(codes) else 0
            
            # Pack into single byte: [high 4 bits][low 4 bits]
            packed_byte = (high_nibble << 4) | low_nibble
            packed_bytes.append(packed_byte)
        
        return bytes(packed_bytes)
    
    def unpack_codes(self, packed_data: bytes, count: int = None) -> List[int]:
        """
        Unpack bytes into list of 4-bit codes
        
        Args:
            packed_data: Packed bytes to unpack
            count: Number of codes to extract (if None, extract all including padding)
        
        Returns:
            List of code values (0-15)
        
        Example:
            >>> packer = BitPacker()
            >>> packer.unpack_codes(b'7\\xf0', count=4)
            [3, 7, 15, 0]
        """
        if not packed_data:
            return []
        
        codes = []
        
        for byte_val in packed_data:
            # Extract high nibble (bits 4-7)
            high_nibble = (byte_val >> 4) & 0x0F
            codes.append(high_nibble)
            
            # Extract low nibble (bits 0-3)
            low_nibble = byte_val & 0x0F
            codes.append(low_nibble)
        
        # Trim to requested count if specified
        if count is not None:
            codes = codes[:count]
        
        return codes
    
    def calculate_packed_size(self, num_codes: int) -> int:
        """
        Calculate size in bytes needed to pack given number of codes
        
        Args:
            num_codes: Number of 4-bit codes
        
        Returns:
            Size in bytes (rounded up for odd counts)
        
        Example:
            >>> packer = BitPacker()
            >>> packer.calculate_packed_size(7)
            4  # 7 codes need 4 bytes (7/2 rounded up)
        """
        return (num_codes + 1) // 2  # Ceiling division
    
    def pack_single_code(self, code: int) -> int:
        """
        Validate and return single 4-bit code value
        
        Args:
            code: Code value (0-15)
        
        Returns:
            Validated code value
        
        Raises:
            ValueError: If code exceeds 4-bit range
        """
        if not isinstance(code, int) or code < 0 or code > self.max_code_value:
            raise ValueError(
                f"Code {code} exceeds 4-bit range (0-{self.max_code_value})"
            )
        return code


# Convenience functions for direct use
def pack_tier0a_codes(codes: List[int]) -> bytes:
    """Pack list of Tier 0A codes into bytes"""
    packer = BitPacker()
    return packer.pack_codes(codes)


def unpack_tier0a_codes(packed_data: bytes, count: int = None) -> List[int]:
    """Unpack bytes into list of Tier 0A codes"""
    packer = BitPacker()
    return packer.unpack_codes(packed_data, count)


if __name__ == "__main__":
    # Self-test
    print("🔧 BIT PACKER - Self Test")
    print("=" * 50)
    
    packer = BitPacker()
    
    # Test 1: Even number of codes
    test_codes_1 = [3, 7, 15, 0, 12, 8]
    packed_1 = packer.pack_codes(test_codes_1)
    unpacked_1 = packer.unpack_codes(packed_1, len(test_codes_1))
    
    print(f"Test 1 - Even codes: {test_codes_1}")
    print(f"  Packed: {packed_1.hex()}")
    print(f"  Unpacked: {unpacked_1}")
    print(f"  Match: {test_codes_1 == unpacked_1}")
    
    # Test 2: Odd number of codes
    test_codes_2 = [1, 2, 3, 4, 5]
    packed_2 = packer.pack_codes(test_codes_2)
    unpacked_2 = packer.unpack_codes(packed_2, len(test_codes_2))
    
    print(f"\nTest 2 - Odd codes: {test_codes_2}")
    print(f"  Packed: {packed_2.hex()}")
    print(f"  Unpacked: {unpacked_2}")
    print(f"  Match: {test_codes_2 == unpacked_2}")
    
    # Test 3: Size calculation
    for num in [1, 2, 3, 7, 10, 16]:
        size = packer.calculate_packed_size(num)
        print(f"\nCodes: {num} → Bytes: {size} (ratio: {num/size:.2f} codes/byte)")
    
    print("\n✅ Bit packer tests complete")
