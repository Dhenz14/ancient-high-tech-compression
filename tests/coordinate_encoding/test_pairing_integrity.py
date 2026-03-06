#!/usr/bin/env python3
"""
PAIRING INTEGRITY TEST
======================
Comprehensive test to find any scenario where vertical/horizontal pairing gets corrupted
This addresses the architect's concern about Tier 1 template ordering
"""

import sys
sys.path.insert(0, 'src')

from coordinate_encoding.scanner_integration import ScannerCoordinateIntegration


def test_pairing_scenarios():
    """Test various pairing scenarios to find potential corruption"""
    print("=" * 70)
    print("PAIRING INTEGRITY TEST - Multiple Scenarios")
    print("=" * 70)
    
    integrator = ScannerCoordinateIntegration()
    
    scenarios = [
        {
            'name': 'Both dimensions sorted (same order)',
            'positions': [
                {'line': 1, 'horizontal': 1},
                {'line': 5, 'horizontal': 5},
                {'line': 10, 'horizontal': 10}
            ]
        },
        {
            'name': 'Vertical sorted, horizontal not sorted',
            'positions': [
                {'line': 1, 'horizontal': 10},
                {'line': 5, 'horizontal': 5},
                {'line': 10, 'horizontal': 15}
            ]
        },
        {
            'name': 'Vertical not sorted, horizontal sorted',
            'positions': [
                {'line': 10, 'horizontal': 1},
                {'line': 1, 'horizontal': 5},
                {'line': 5, 'horizontal': 10}
            ]
        },
        {
            'name': 'Both dimensions sorted (different permutations - CRITICAL TEST)',
            'positions': [
                {'line': 1, 'horizontal': 5},
                {'line': 5, 'horizontal': 10},
                {'line': 10, 'horizontal': 15}
            ]
        },
        {
            'name': 'Complex interleaving',
            'positions': [
                {'line': 5, 'horizontal': 15},
                {'line': 1, 'horizontal': 5},
                {'line': 10, 'horizontal': 10},
                {'line': 3, 'horizontal': 20}
            ]
        }
    ]
    
    all_passed = True
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*70}")
        print(f"SCENARIO {i}: {scenario['name']}")
        print(f"{'='*70}")
        
        positions = scenario['positions']
        
        # Show original
        print(f"\n📥 ORIGINAL POSITIONS:")
        for j, pos in enumerate(positions):
            print(f"   Position {j}: Line {pos['line']:2d}, Horizontal {pos['horizontal']:2d}")
        
        # Analyze dimensions
        vertical = [p['line'] for p in positions]
        horizontal = [p['horizontal'] for p in positions]
        v_sorted = (vertical == sorted(vertical))
        h_sorted = (horizontal == sorted(horizontal))
        print(f"\n📊 DIMENSION ANALYSIS:")
        print(f"   Vertical sequence: {vertical} - {'sorted' if v_sorted else 'NOT sorted'}")
        print(f"   Horizontal sequence: {horizontal} - {'sorted' if h_sorted else 'NOT sorted'}")
        
        # Encode
        encoded = integrator.encode_word_positions('test', positions)
        print(f"\n🔄 ENCODED:")
        print(f"   Vertical: {encoded['vertical_tier']}")
        print(f"   Horizontal: {encoded['horizontal_tier']}")
        
        # Decode
        decoded = integrator.decode_word_positions(encoded)
        
        print(f"\n📤 DECODED POSITIONS:")
        for j, pos in enumerate(decoded):
            print(f"   Position {j}: Line {pos['line']:2d}, Horizontal {pos['horizontal']:2d}")
        
        # Verify exact order
        print(f"\n✅ VERIFICATION:")
        
        assert len(decoded) == len(positions), \
            f"Scenario {i} COUNT MISMATCH: {len(decoded)} vs {len(positions)}"
        
        for j, (orig, dec) in enumerate(zip(positions, decoded)):
            assert orig['line'] == dec['line'] and orig['horizontal'] == dec['horizontal'], \
                f"Scenario {i} Position {j}: Original ({orig['line']}, {orig['horizontal']}) != Decoded ({dec['line']}, {dec['horizontal']}) - PAIRING CORRUPTED!"
            
            print(f"   ✓ Position {j}: ({orig['line']}, {orig['horizontal']}) matches")
        
        print(f"\n✅ Scenario {i} PASSED")
    
    print(f"\n{'='*70}")
    print("🎉 ALL PAIRING INTEGRITY TESTS PASSED!")
    print("✅ No pairing corruption detected in any scenario")
    


if __name__ == "__main__":
    test_pairing_scenarios()
    sys.exit(0)
