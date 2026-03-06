#!/usr/bin/env python3
"""
BUG FIX VALIDATION TESTS
========================
Validates that specific bug fixes are working correctly

Tests for:
1. Migration validator correctly handles dual-dimension format
2. Batch encoding skips empty position lists
3. Compression improvement is calculated correctly
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from coordinate_encoding.scanner_integration import ScannerCoordinateIntegration
from coordinate_encoding.migration_utils import DataMigrator


def test_migration_validator_dual_dimension():
    """Test that migration validator correctly handles dual-dimension format"""
    migrator = DataMigrator()
    
    # Create old format dataset (20 words with 5 positions each)
    old_data = {}
    for i in range(20):
        word = f"word_{i}"
        old_data[word] = {
            'internal_lines': [
                {'line_position': j * 10}
                for j in range(1, 6)  # 5 positions per word
            ]
        }
    
    # Migrate
    new_data, validation = migrator.migrate_scanner_output(old_data)
    
    # Validate migration success
    assert validation['total_words'] == 20, \
        f"Expected 20 words, got {validation['total_words']}"
    
    assert validation['passed'] == 20, \
        f"Expected 20 passed validations, got {validation['passed']}"
    
    assert validation['failed'] == 0, \
        f"Expected 0 failed validations, got {validation['failed']}"
    
    assert validation['pass_rate'] == 1.0, \
        f"Expected 100% pass rate, got {validation['pass_rate'] * 100}%"
    
    # TWO-TIER VALIDATION for dual-dimension migration:
    # Guard #1: Ratio-based cap (prevents blow-ups like 20 → 60 bytes)
    assert validation['total_new_size'] <= validation['total_old_size'] * 1.25, \
        f"Migration size blow-up: {validation['total_new_size']} > 125% of {validation['total_old_size']} bytes"
    
    # Guard #2: Bounded compression range (allows expected expansion)
    assert validation['compression_improvement'] >= -25, \
        f"Compression too negative: {validation['compression_improvement']}% (expected: -25% to +50%)"
    
    print(f"✅ Migration validation: {validation['passed']}/{validation['total_words']} passed")
    print(f"✅ Compression improvement: {validation['compression_improvement']:.1f}%")


def test_batch_encoding_skips_empty():
    """Test that batch encoding correctly skips empty position lists"""
    integrator = ScannerCoordinateIntegration()
    
    # Create dataset with mix of empty and non-empty positions
    test_data = {
        'word1': [],  # Empty - should be skipped
        'word2': [{'line': 1, 'horizontal': 10}],  # Has positions
        'word3': [],  # Empty - should be skipped
        'word4': [{'line': 5, 'horizontal': 25}],  # Has positions
        'word5': []   # Empty - should be skipped
    }
    
    result = integrator.batch_encode_scanner_data(test_data)
    
    # Should only count non-empty words
    assert result['total_words'] == 2, \
        f"Expected 2 non-empty words, got {result['total_words']}"
    
    assert result['total_positions'] == 2, \
        f"Expected 2 total positions, got {result['total_positions']}"
    
    # Verify only non-empty words were encoded
    assert 'word1' not in result['encoded_words'], "Empty word1 should not be encoded"
    assert 'word2' in result['encoded_words'], "Non-empty word2 should be encoded"
    assert 'word3' not in result['encoded_words'], "Empty word3 should not be encoded"
    assert 'word4' in result['encoded_words'], "Non-empty word4 should be encoded"
    assert 'word5' not in result['encoded_words'], "Empty word5 should not be encoded"
    
    print(f"✅ Batch encoding correctly skipped empty positions")
    print(f"✅ Processed {result['total_words']} non-empty words")


def test_compression_calculation_bytes_to_bytes():
    """Test that compression is calculated as bytes-to-bytes (not positions-to-bytes)"""
    migrator = DataMigrator()
    
    # Single word with 5 positions
    old_data = {
        'testword': {
            'internal_lines': [
                {'line_position': i * 10}
                for i in range(1, 6)
            ]
        }
    }
    
    new_data, validation = migrator.migrate_scanner_output(old_data)
    
    # Old size should be 5 positions × 4 bytes = 20 bytes (single-dimension legacy format)
    assert validation['total_old_size'] == 20, \
        f"Expected 20 bytes old size (single-dimension), got {validation['total_old_size']}"
    
    # New size includes both dimensions (vertical + horizontal with default 0)
    # For 5 positions: vertical ~11 bytes (Tier 2) + horizontal ~3 bytes (all zeros, template) = ~14 bytes
    # May vary slightly, but should still show improvement or be close
    assert validation['total_new_size'] <= 25, \
        f"Expected new size <= 25 bytes, got {validation['total_new_size']}"
    
    # TWO-TIER VALIDATION for compression metrics:
    # Guard #1: Ratio cap prevents true regressions
    ratio = validation['total_new_size'] / validation['total_old_size']
    assert ratio <= 1.25, \
        f"Size ratio {ratio:.2f}x exceeds 1.25x limit (prevents blow-ups)"
    
    # Guard #2: Bounded compression allows expected dual-dimension expansion
    assert validation['compression_improvement'] >= -25, \
        f"Compression {validation['compression_improvement']}% below -25% limit"
    
    # Calculate expected improvement
    expected_improvement = ((validation['total_old_size'] - validation['total_new_size']) / 
                           validation['total_old_size'] * 100)
    
    assert abs(validation['compression_improvement'] - expected_improvement) < 0.1, \
        f"Compression calculation mismatch: {validation['compression_improvement']}% vs {expected_improvement}%"
    
    print(f"✅ Compression calculated correctly:")
    print(f"   Old size: {validation['total_old_size']} bytes")
    print(f"   New size: {validation['total_new_size']} bytes")
    print(f"   Improvement: {validation['compression_improvement']:.1f}%")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
