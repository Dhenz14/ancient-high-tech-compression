#!/usr/bin/env python3
"""
DUPLICATE POSITION TEST
=======================
Verifies that duplicate positions are preserved (e.g., same word twice on same line)
"""

import sys
sys.path.insert(0, 'src')

from coordinate_encoding.scanner_integration import ScannerCoordinateIntegration


def test_duplicate_positions():
    """Test that duplicate line positions are preserved"""
    print("=" * 70)
    print("DUPLICATE POSITION TEST: Multiple words on same line")
    print("=" * 70)
    
    integrator = ScannerCoordinateIntegration()
    
    # Test data: Word "the" appears 3 times on line 1 (positions 1, 5, 8)
    test_positions = [
        {'line': 1, 'horizontal': 1},
        {'line': 1, 'horizontal': 5},
        {'line': 1, 'horizontal': 8}
    ]
    
    print(f"\n📥 ORIGINAL POSITIONS:")
    for i, pos in enumerate(test_positions):
        print(f"   Position {i}: Line {pos['line']}, Horizontal {pos['horizontal']}")
    print(f"   Note: All 3 occurrences on same line (duplicates in vertical dimension)")
    
    # Encode
    print(f"\n🔄 ENCODING...")
    encoded = integrator.encode_word_positions('the', test_positions)
    
    print(f"\n📊 ENCODED RESULT:")
    print(f"   Vertical: {encoded['vertical_tier']} ({encoded['vertical_encoded_size']} bytes)")
    print(f"   Horizontal: {encoded['horizontal_tier']} ({encoded['horizontal_encoded_size']} bytes)")
    print(f"   Total: {encoded['encoded_size']} bytes")
    
    # Decode
    print(f"\n🔄 DECODING...")
    decoded = integrator.decode_word_positions(encoded)
    
    print(f"\n📤 DECODED POSITIONS:")
    for i, pos in enumerate(decoded):
        print(f"   Position {i}: Line {pos['line']}, Horizontal {pos['horizontal']}")
    
    # Verify
    print(f"\n✅ VERIFICATION:")
    
    assert len(decoded) == len(test_positions), \
        f"COUNT MISMATCH: {len(decoded)} vs {len(test_positions)} - Duplicates may have been lost!"
    
    for i, (orig, dec) in enumerate(zip(test_positions, decoded)):
        line_match = orig['line'] == dec['line']
        horiz_match = orig['horizontal'] == dec['horizontal']
        
        assert line_match and horiz_match, \
            f"Position {i}: Original ({orig['line']}, {orig['horizontal']}) != Decoded ({dec['line']}, {dec['horizontal']})"
        
        print(f"   ✓ Position {i}: ({orig['line']}, {orig['horizontal']}) matches")
    
    print(f"\n{'='*70}")
    print("🎉 DUPLICATE POSITIONS PRESERVED!")
    print("✅ TEST PASSED")
    


if __name__ == "__main__":
    test_duplicate_positions()
    sys.exit(0)
