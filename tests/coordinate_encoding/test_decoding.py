#!/usr/bin/env python3
"""
TEST DECODING - 100% Reconstruction Verification
================================================
Coordinate Lookup Encoding System - Phase 5

Tests decoding accuracy across all tiers:
- Verifies 100% reconstruction accuracy
- Tests all tier decoders individually
- Validates roundtrip encode/decode
- Tests error handling

CRITICAL: All tests must pass for production use
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))

import unittest
from coordinate_encoding import CoordinateEncoder, CoordinateDecoder
from coordinate_encoding.template_cache import get_template_cache


class TestCoordinateDecoder(unittest.TestCase):
    """Test coordinate decoding for all tiers"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize encoder and decoder"""
        cls.encoder = CoordinateEncoder()
        cls.decoder = CoordinateDecoder()
        cls.cache = get_template_cache()
    
    def test_decode_tier0a(self):
        """Test Tier 0A decoding"""
        # Encode a single-line pattern
        encoded = self.encoder.encode_positions([1])
        
        if encoded['tier'] == 'tier0a':
            # Decode
            decoded = self.decoder.decode(encoded['encoded_bytes'], 'tier0a')
            
            # Verify
            self.assertEqual(sorted(decoded), sorted([1]))
    
    def test_decode_tier0b(self):
        """Test Tier 0B decoding"""
        # Try a common two-line pattern
        encoded = self.encoder.encode_positions([1, 2])
        
        if encoded['tier'] == 'tier0b':
            # Decode
            decoded = self.decoder.decode(encoded['encoded_bytes'], 'tier0b')
            
            # Verify
            self.assertEqual(sorted(decoded), sorted([1, 2]))
    
    def test_decode_tier1(self):
        """Test Tier 1 decoding"""
        # Three-line pattern should be Tier 1
        encoded = self.encoder.encode_positions([1, 2, 3])
        
        # Decode
        decoded = self.decoder.decode(encoded['encoded_bytes'], encoded['tier'])
        
        # Verify
        self.assertEqual(sorted(decoded), sorted([1, 2, 3]))
    
    def test_decode_tier2(self):
        """Test Tier 2 delta decoding"""
        # Complex pattern likely to be Tier 2
        positions = [7, 14, 21, 28, 35, 42, 49]
        encoded = self.encoder.encode_positions(positions)
        
        # Decode
        decoded = self.decoder.decode(encoded['encoded_bytes'], encoded['tier'])
        
        # Verify
        self.assertEqual(sorted(decoded), sorted(positions))
    
    def test_auto_detect_tier(self):
        """Test automatic tier detection from marker byte"""
        test_positions = [[1], [1, 2], [1, 2, 3], [5, 10, 15, 20, 25]]
        
        for positions in test_positions:
            # Encode
            encoded = self.encoder.encode_positions(positions)
            
            # Decode without specifying tier (auto-detect)
            decoded = self.decoder.decode(encoded['encoded_bytes'])
            
            # Verify
            self.assertEqual(sorted(decoded), sorted(positions))
    
    def test_decode_batch(self):
        """Test batch decoding"""
        position_lists = [
            [1],
            [2, 3],
            [1, 5, 10],
            [7, 14, 21, 28]
        ]
        
        # Encode all
        encoded_list = [(
            self.encoder.encode_positions(positions)['encoded_bytes'],
            self.encoder.encode_positions(positions)['tier']
        ) for positions in position_lists]
        
        # Decode all
        decoded_list = self.decoder.decode_batch(encoded_list)
        
        # Verify all
        for original, decoded in zip(position_lists, decoded_list):
            self.assertEqual(sorted(original), sorted(decoded))
    
    def test_invalid_tier_marker(self):
        """Test handling of invalid tier marker"""
        # Create invalid encoded data
        invalid_data = bytes([0xFF, 0x00])
        
        with self.assertRaises(ValueError):
            self.decoder.decode(invalid_data)
    
    def test_statistics_tracking(self):
        """Test decoder statistics tracking"""
        self.decoder.reset_statistics()
        
        # Decode various patterns
        for positions in [[1], [1, 2], [1, 2, 3]]:
            encoded = self.encoder.encode_positions(positions)
            self.decoder.decode(encoded['encoded_bytes'])
        
        stats = self.decoder.get_statistics()
        
        self.assertEqual(stats['words_decoded'], 3)
        self.assertEqual(stats['accuracy'], 1.0)  # 100% accuracy


class TestRoundtripAccuracy(unittest.TestCase):
    """Test roundtrip encode/decode accuracy - CRITICAL TESTS"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize encoder and decoder"""
        cls.encoder = CoordinateEncoder()
        cls.decoder = CoordinateDecoder()
    
    def verify_roundtrip(self, positions):
        """Helper to verify roundtrip accuracy"""
        # Encode
        encoded = self.encoder.encode_positions(positions)
        
        # Decode
        decoded = self.decoder.decode(encoded['encoded_bytes'], encoded['tier'])
        
        # Verify exact match
        return sorted(positions) == sorted(decoded)
    
    def test_roundtrip_single_lines(self):
        """Test roundtrip for single-line patterns"""
        for line in [1, 2, 3, 5, 10, 20, 50, 100]:
            with self.subTest(line=line):
                self.assertTrue(self.verify_roundtrip([line]))
    
    def test_roundtrip_two_lines(self):
        """Test roundtrip for two-line patterns"""
        test_cases = [
            [1, 2], [1, 5], [1, 10], [5, 10],
            [10, 20], [20, 50], [50, 100]
        ]
        
        for positions in test_cases:
            with self.subTest(positions=positions):
                self.assertTrue(self.verify_roundtrip(positions))
    
    def test_roundtrip_three_lines(self):
        """Test roundtrip for three-line patterns"""
        test_cases = [
            [1, 2, 3], [1, 5, 10], [2, 7, 15],
            [10, 20, 30], [25, 50, 75]
        ]
        
        for positions in test_cases:
            with self.subTest(positions=positions):
                self.assertTrue(self.verify_roundtrip(positions))
    
    def test_roundtrip_multiple_lines(self):
        """Test roundtrip for 4+ line patterns"""
        test_cases = [
            [1, 5, 10, 15],
            [2, 4, 6, 8, 10],
            [1, 10, 20, 30, 40, 50],
            [7, 14, 21, 28, 35, 42, 49]
        ]
        
        for positions in test_cases:
            with self.subTest(positions=positions):
                self.assertTrue(self.verify_roundtrip(positions))
    
    def test_roundtrip_100_random_patterns(self):
        """Test roundtrip with 100 random patterns - CRITICAL TEST"""
        import random
        
        random.seed(42)  # Reproducible results
        success_count = 0
        
        for i in range(100):
            # Generate random pattern
            num_positions = random.randint(1, 10)
            positions = sorted(random.sample(range(1, 101), num_positions))
            
            # Test roundtrip
            if self.verify_roundtrip(positions):
                success_count += 1
        
        # Require 100% accuracy
        self.assertEqual(success_count, 100, 
                        f"Only {success_count}/100 roundtrips succeeded")
    
    def test_verify_reconstruction_method(self):
        """Test the verify_reconstruction utility method"""
        positions = [1, 5, 10, 15, 20]
        encoded = self.encoder.encode_positions(positions)
        
        # Should return True for correct reconstruction
        self.assertTrue(
            self.decoder.verify_reconstruction(
                positions,
                encoded['encoded_bytes'],
                encoded['tier']
            )
        )


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize encoder and decoder"""
        cls.encoder = CoordinateEncoder()
        cls.decoder = CoordinateDecoder()
    
    def test_max_line_number(self):
        """Test encoding/decoding maximum line number (100)"""
        positions = [100]
        encoded = self.encoder.encode_positions(positions)
        decoded = self.decoder.decode(encoded['encoded_bytes'], encoded['tier'])
        
        self.assertEqual(sorted(decoded), sorted(positions))
    
    def test_min_line_number(self):
        """Test encoding/decoding minimum line number (1)"""
        positions = [1]
        encoded = self.encoder.encode_positions(positions)
        decoded = self.decoder.decode(encoded['encoded_bytes'], encoded['tier'])
        
        self.assertEqual(sorted(decoded), sorted(positions))
    
    def test_consecutive_lines(self):
        """Test consecutive line numbers"""
        positions = list(range(1, 11))  # [1, 2, 3, ..., 10]
        encoded = self.encoder.encode_positions(positions)
        decoded = self.decoder.decode(encoded['encoded_bytes'], encoded['tier'])
        
        self.assertEqual(sorted(decoded), sorted(positions))
    
    def test_scattered_lines(self):
        """Test widely scattered line numbers"""
        positions = [1, 25, 50, 75, 100]
        encoded = self.encoder.encode_positions(positions)
        decoded = self.decoder.decode(encoded['encoded_bytes'], encoded['tier'])
        
        self.assertEqual(sorted(decoded), sorted(positions))


def run_decoding_tests():
    """Run all decoding tests"""
    print("🧪 COORDINATE DECODING TESTS - 100% ACCURACY VERIFICATION")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestCoordinateDecoder))
    suite.addTests(loader.loadTestsFromTestCase(TestRoundtripAccuracy))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ 100% RECONSTRUCTION ACCURACY VERIFIED")
    else:
        print("❌ RECONSTRUCTION ACCURACY FAILURES DETECTED")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_decoding_tests()
    sys.exit(0 if success else 1)
