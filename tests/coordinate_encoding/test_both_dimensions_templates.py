#!/usr/bin/env python3
"""
BOTH DIMENSIONS TEMPLATE TEST
==============================
Verifies ordering when BOTH vertical and horizontal match Tier 0/1 templates
This catches the regression where template-based tiers might return normalized order
"""

import sys
sys.path.insert(0, 'src')

from coordinate_encoding.scanner_integration import ScannerCoordinateIntegration


def test_both_dimensions_use_templates():
    """Test when both dimensions independently match templates"""
    print("=" * 70)
    print("BOTH DIMENSIONS TEMPLATE TEST")
    print("=" * 70)
    
    integrator = ScannerCoordinateIntegration()
    
    # Test case: Both dimensions independently sorted
    # Vertical: [1, 5, 10] (sorted, matches Tier 1)
    # Horizontal: [2, 7, 12] (sorted, matches Tier 1)
    test_positions = [
        {'line': 1, 'horizontal': 2},
        {'line': 5, 'horizontal': 7},
        {'line': 10, 'horizontal': 12}
    ]
    
    print(f"\n📥 ORIGINAL POSITIONS:")
    for i, pos in enumerate(test_positions):
        print(f"   Position {i}: Line {pos['line']:2d}, Horizontal {pos['horizontal']:2d}")
    print(f"   Vertical sequence: [1, 5, 10] (sorted)")
    print(f"   Horizontal sequence: [2, 7, 12] (sorted)")
    print(f"   Note: Both dimensions independently sorted → likely both use templates")
    
    # Encode
    print(f"\n🔄 ENCODING...")
    encoded = integrator.encode_word_positions('test', test_positions)
    
    print(f"\n📊 ENCODED RESULT:")
    print(f"   Vertical: {encoded['vertical_tier']} ({encoded['vertical_encoded_size']} bytes)")
    print(f"   Horizontal: {encoded['horizontal_tier']} ({encoded['horizontal_encoded_size']} bytes)")
    print(f"   Total: {encoded['encoded_size']} bytes")
    
    # Check if both used templates
    both_templates = (encoded['vertical_tier'] in ['tier0a', 'tier0b', 'tier1'] and 
                     encoded['horizontal_tier'] in ['tier0a', 'tier0b', 'tier1'])
    if both_templates:
        print(f"   ✓ Both dimensions used templates (Tier 0A/0B/1)")
    else:
        print(f"   ⚠ At least one dimension used Tier 2 (delta encoding)")
    
    # Decode
    print(f"\n🔄 DECODING...")
    decoded = integrator.decode_word_positions(encoded)
    
    print(f"\n📤 DECODED POSITIONS:")
    for i, pos in enumerate(decoded):
        print(f"   Position {i}: Line {pos['line']:2d}, Horizontal {pos['horizontal']:2d}")
    
    # Verify EXACT ORDER (not sorted comparison!)
    print(f"\n✅ VERIFICATION (EXACT ORDER):")
    
    assert len(decoded) == len(test_positions), \
        f"COUNT MISMATCH: {len(decoded)} vs {len(test_positions)}"
    
    for i, (orig, dec) in enumerate(zip(test_positions, decoded)):
        line_match = orig['line'] == dec['line']
        horiz_match = orig['horizontal'] == dec['horizontal']
        
        assert line_match and horiz_match, \
            f"Position {i}: Original ({orig['line']}, {orig['horizontal']}) != Decoded ({dec['line']}, {dec['horizontal']}) - Template-based tiers corrupted pairing"
        
        print(f"   ✓ Position {i}: ({orig['line']}, {orig['horizontal']}) matches")
    
    print(f"\n{'='*70}")
    print("🎉 BOTH-DIMENSIONS-TEMPLATE TEST PASSED!")
    if both_templates:
        print("✅ Template-based tiers preserve order correctly")
    


if __name__ == "__main__":
    test_both_dimensions_use_templates()
    sys.exit(0)
