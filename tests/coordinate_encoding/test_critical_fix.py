#!/usr/bin/env python3
"""
CRITICAL FIX VERIFICATION TEST
==============================
Verifies that BOTH vertical and horizontal coordinates are properly preserved

Tests the fix for the data loss bug found by architect review
"""

import sys
sys.path.insert(0, 'src')

from coordinate_encoding.scanner_integration import ScannerCoordinateIntegration


def test_both_dimensions_preserved():
    """Test that both line and horizontal coordinates are preserved"""
    print("=" * 70)
    print("CRITICAL FIX TEST: Both Dimensions Preservation")
    print("=" * 70)
    
    integrator = ScannerCoordinateIntegration()
    
    # Test data with both dimensions
    test_positions = [
        {'line': 1, 'horizontal': 10},
        {'line': 5, 'horizontal': 25},
        {'line': 10, 'horizontal': 42},
        {'line': 15, 'horizontal': 8},
        {'line': 20, 'horizontal': 33}
    ]
    
    print(f"\n📥 ORIGINAL POSITIONS:")
    for pos in test_positions:
        print(f"   Line {pos['line']}, Horizontal {pos['horizontal']}")
    
    # Encode
    print(f"\n🔄 ENCODING...")
    encoded = integrator.encode_word_positions('test', test_positions)
    
    print(f"\n📊 ENCODED RESULT:")
    print(f"   Vertical: {encoded['vertical_tier']} ({encoded['vertical_encoded_size']} bytes)")
    print(f"   Horizontal: {encoded['horizontal_tier']} ({encoded['horizontal_encoded_size']} bytes)")
    print(f"   Total: {encoded['encoded_size']} bytes")
    print(f"   Compression: {encoded['compression_ratio']:.2f}:1")
    
    # Decode
    print(f"\n🔄 DECODING...")
    decoded = integrator.decode_word_positions(encoded)
    
    print(f"\n📤 DECODED POSITIONS:")
    for pos in decoded:
        print(f"   Line {pos['line']}, Horizontal {pos['horizontal']}")
    
    # Verify
    print(f"\n✅ VERIFICATION:")
    
    # Check count with assertion
    assert len(decoded) == len(test_positions), f"COUNT MISMATCH: {len(decoded)} vs {len(test_positions)}"
    
    # Check exact match IN ORDER (do NOT sort - must preserve order!)
    # CRITICAL: Sorting would hide pairing bugs, so compare in original order
    
    for i, (orig, dec) in enumerate(zip(test_positions, decoded)):
        line_match = orig['line'] == dec['line']
        horiz_match = orig['horizontal'] == dec['horizontal']
        
        # Use assertion to fail on mismatch
        assert line_match and horiz_match, \
            f"Position {i}: Original ({orig['line']}, {orig['horizontal']}) != Decoded ({dec['line']}, {dec['horizontal']})"
        
        print(f"   ✓ Position {i}: ({orig['line']}, {orig['horizontal']}) matches")
    
    # Use roundtrip verification with assertion
    roundtrip_pass = integrator.verify_roundtrip('test', test_positions)
    assert roundtrip_pass, "Roundtrip verification failed"
    
    print(f"\n{'='*70}")
    print("🎉 CRITICAL FIX VERIFIED: Both dimensions preserved correctly!")
    print("✅ TEST PASSED")


if __name__ == "__main__":
    test_both_dimensions_preserved()
    sys.exit(0)
