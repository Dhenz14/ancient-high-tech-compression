#!/usr/bin/env python3
"""
ISOLATION TEST
==============
Tests encoder and decoder directly without going through scanner_integration
to verify no shared-state bugs
"""

import sys
sys.path.insert(0, 'src')

from coordinate_encoding.coordinate_encoder import CoordinateEncoder
from coordinate_encoding.coordinate_decoder import CoordinateDecoder


def test_direct_encoding_decoding():
    """Test encoder→decoder directly"""
    print("=" * 70)
    print("ISOLATION TEST: Direct Encoder→Decoder")
    print("=" * 70)
    
    encoder = CoordinateEncoder()
    decoder = CoordinateDecoder()
    
    # Test 1: Simple positions
    print("\n🔬 TEST 1: Simple positions [1, 5, 10]")
    original1 = [1, 5, 10]
    encoded1 = encoder.encode_positions(original1)
    print(f"   Original: {original1}")
    print(f"   Tier: {encoded1['tier']}")
    print(f"   Bytes: {encoded1['encoded_bytes'].hex()}")
    
    decoded1 = decoder.decode(encoded1['encoded_bytes'], encoded1['tier'])
    print(f"   Decoded: {decoded1}")
    assert original1 == decoded1, f"Test 1 failed: {original1} != {decoded1}"
    print(f"   ✓ Match: True")
    
    # Test 2: Duplicates
    print("\n🔬 TEST 2: Duplicates [1, 1, 1]")
    original2 = [1, 1, 1]
    encoded2 = encoder.encode_positions(original2)
    print(f"   Original: {original2}")
    print(f"   Tier: {encoded2['tier']}")
    print(f"   Bytes: {encoded2['encoded_bytes'].hex()}")
    
    decoded2 = decoder.decode(encoded2['encoded_bytes'], encoded2['tier'])
    print(f"   Decoded: {decoded2}")
    assert original2 == decoded2, f"Test 2 failed: {original2} != {decoded2}"
    print(f"   ✓ Match: True")
    
    # Test 3: Large gaps
    print("\n🔬 TEST 3: Large gaps [1, 150, 300, 10]")
    original3 = [1, 150, 300, 10]
    encoded3 = encoder.encode_positions(original3)
    print(f"   Original: {original3}")
    print(f"   Tier: {encoded3['tier']}")
    print(f"   Bytes: {encoded3['encoded_bytes'].hex()}")
    print(f"   Bytes detail: {' '.join(f'{b:02x}' for b in encoded3['encoded_bytes'])}")
    
    decoded3 = decoder.decode(encoded3['encoded_bytes'], encoded3['tier'])
    print(f"   Decoded: {decoded3}")
    assert original3 == decoded3, f"Test 3 failed: {original3} != {decoded3}"
    print(f"   ✓ Match: True")
    
    # Test 4: Negative deltas
    print("\n🔬 TEST 4: Negative deltas [10, 5, 1]")
    original4 = [10, 5, 1]
    encoded4 = encoder.encode_positions(original4)
    print(f"   Original: {original4}")
    print(f"   Tier: {encoded4['tier']}")
    print(f"   Bytes: {encoded4['encoded_bytes'].hex()}")
    print(f"   Bytes detail: {' '.join(f'{b:02x}' for b in encoded4['encoded_bytes'])}")
    
    decoded4 = decoder.decode(encoded4['encoded_bytes'], encoded4['tier'])
    print(f"   Decoded: {decoded4}")
    assert original4 == decoded4, f"Test 4 failed: {original4} != {decoded4}"
    print(f"   ✓ Match: True")
    
    print(f"\n{'='*70}")
    print("🎉 ALL ISOLATION TESTS PASSED!")
    print("✅ Encoder/Decoder work correctly in isolation")
    


if __name__ == "__main__":
    test_direct_encoding_decoding()
    sys.exit(0)
