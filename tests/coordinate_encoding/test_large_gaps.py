#!/usr/bin/env python3
"""
LARGE GAP TEST
==============
Verifies that large position gaps (>127) encode and decode correctly
"""

import sys
sys.path.insert(0, 'src')

from coordinate_encoding.scanner_integration import ScannerCoordinateIntegration


def test_large_gaps():
    """Test encoding/decoding with large position gaps"""
    print("=" * 70)
    print("LARGE GAP TEST: Positions with gaps >127")
    print("=" * 70)
    
    integrator = ScannerCoordinateIntegration()
    
    # Test data: Large gaps in both dimensions
    test_positions = [
        {'line': 1, 'horizontal': 1},
        {'line': 150, 'horizontal': 200},  # Large gap: +149 lines, +199 horizontal
        {'line': 300, 'horizontal': 50},   # Large gap: +150 lines, -150 horizontal
        {'line': 10, 'horizontal': 400}    # Large gap: -290 lines, +350 horizontal
    ]
    
    print(f"\n📥 ORIGINAL POSITIONS:")
    for i, pos in enumerate(test_positions):
        if i > 0:
            prev = test_positions[i-1]
            line_delta = pos['line'] - prev['line']
            horiz_delta = pos['horizontal'] - prev['horizontal']
            print(f"   Position {i}: Line {pos['line']:3d} (Δ{line_delta:+4d}), Horizontal {pos['horizontal']:3d} (Δ{horiz_delta:+4d})")
        else:
            print(f"   Position {i}: Line {pos['line']:3d}, Horizontal {pos['horizontal']:3d}")
    
    # Encode
    print(f"\n🔄 ENCODING...")
    encoded = integrator.encode_word_positions('test', test_positions)
    
    print(f"\n📊 ENCODED RESULT:")
    print(f"   Vertical: {encoded['vertical_tier']} ({encoded['vertical_encoded_size']} bytes)")
    print(f"   Horizontal: {encoded['horizontal_tier']} ({encoded['horizontal_encoded_size']} bytes)")
    print(f"   Total: {encoded['encoded_size']} bytes")
    
    # Decode
    print(f"\n🔄 DECODING...")
    decoded = integrator.decode_word_positions(encoded)
    
    print(f"\n📤 DECODED POSITIONS:")
    for i, pos in enumerate(decoded):
        if i > 0:
            prev = decoded[i-1]
            line_delta = pos['line'] - prev['line']
            horiz_delta = pos['horizontal'] - prev['horizontal']
            print(f"   Position {i}: Line {pos['line']:3d} (Δ{line_delta:+4d}), Horizontal {pos['horizontal']:3d} (Δ{horiz_delta:+4d})")
        else:
            print(f"   Position {i}: Line {pos['line']:3d}, Horizontal {pos['horizontal']:3d}")
    
    # Verify
    print(f"\n✅ VERIFICATION:")
    
    assert len(decoded) == len(test_positions), \
        f"COUNT MISMATCH: {len(decoded)} vs {len(test_positions)}"
    
    for i, (orig, dec) in enumerate(zip(test_positions, decoded)):
        line_match = orig['line'] == dec['line']
        horiz_match = orig['horizontal'] == dec['horizontal']
        
        assert line_match and horiz_match, \
            f"Position {i}: Original ({orig['line']}, {orig['horizontal']}) != Decoded ({dec['line']}, {dec['horizontal']})"
        
        print(f"   ✓ Position {i}: ({orig['line']}, {orig['horizontal']}) matches")
    
    print(f"\n{'='*70}")
    print("🎉 LARGE GAPS PRESERVED CORRECTLY!")
    print("✅ TEST PASSED")
    


if __name__ == "__main__":
    test_large_gaps()
    sys.exit(0)
