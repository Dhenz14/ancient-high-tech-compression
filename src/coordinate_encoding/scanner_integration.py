#!/usr/bin/env python3
"""
SCANNER INTEGRATION - Coordinate Encoding for Production Scanner
================================================================
Coordinate Lookup Encoding System - Phase 4

Integration layer for production_scanner.py to use coordinate encoding
Replaces microscopic line position storage with optimized coordinate encoding

Dr. Chen (System Architecture Lead)
"""

from typing import List, Dict, Any
from .coordinate_encoder import CoordinateEncoder
from .coordinate_decoder import CoordinateDecoder


class ScannerCoordinateIntegration:
    """
    Integration layer for coordinate encoding in production scanner
    
    Provides drop-in replacement for microscopic line position storage
    Maintains API compatibility while using optimized encoding
    """
    
    def __init__(self):
        """Initialize scanner integration"""
        self.encoder = CoordinateEncoder()
        self.decoder = CoordinateDecoder()
        
        # Integration statistics
        self.stats = {
            'words_processed': 0,
            'total_positions': 0,
            'total_encoded_bytes': 0,
            'compression_ratio': 0.0
        }
        
        print("🔗 SCANNER COORDINATE INTEGRATION INITIALIZED")
    
    def encode_word_positions(self, word: str, positions: List[Dict[str, int]]) -> Dict[str, Any]:
        """
        Encode word positions using coordinate encoding
        
        Replaces microscopic line architecture with coordinate encoding
        
        Args:
            word: The word being encoded
            positions: List of position dicts with 'line' and 'horizontal' keys
        
        Returns:
            Dict with encoded position data compatible with scanner format
        
        Example:
            >>> integrator = ScannerCoordinateIntegration()
            >>> positions = [
            ...     {'line': 1, 'horizontal': 10},
            ...     {'line': 5, 'horizontal': 25},
            ...     {'line': 10, 'horizontal': 42}
            ... ]
            >>> result = integrator.encode_word_positions('the', positions)
            >>> result['encoding_method']
            'coordinate_lookup'
        """
        # CRITICAL FIX: Extract BOTH line and horizontal positions
        line_positions = [pos['line'] for pos in positions]
        horizontal_positions = [pos['horizontal'] for pos in positions]
        
        # Encode BOTH dimensions using coordinate encoding
        vertical_encoding = self.encoder.encode_positions(line_positions)
        horizontal_encoding = self.encoder.encode_positions(horizontal_positions)
        
        # Calculate total encoded size (vertical + horizontal)
        total_encoded_size = vertical_encoding['encoded_size'] + horizontal_encoding['encoded_size']
        
        # Update statistics
        self.stats['words_processed'] += 1
        self.stats['total_positions'] += len(positions)
        self.stats['total_encoded_bytes'] += total_encoded_size
        
        if self.stats['total_positions'] > 0:
            self.stats['compression_ratio'] = (
                self.stats['total_positions'] * 2 / self.stats['total_encoded_bytes']  # *2 for both dimensions
            )
        
        # Return scanner-compatible format with BOTH dimensions
        return {
            'word': word,
            'frequency': len(positions),
            'encoding_method': 'coordinate_lookup',
            
            # Vertical (line) encoding
            'vertical_tier': vertical_encoding['tier'],
            'vertical_encoded_bytes': vertical_encoding['encoded_bytes'],
            'vertical_encoded_size': vertical_encoding['encoded_size'],
            
            # Horizontal encoding
            'horizontal_tier': horizontal_encoding['tier'],
            'horizontal_encoded_bytes': horizontal_encoding['encoded_bytes'],
            'horizontal_encoded_size': horizontal_encoding['encoded_size'],
            
            # Combined metrics
            'encoded_size': total_encoded_size,
            'original_positions': positions,  # Store full {line, horizontal} dicts
            'compression_ratio': (len(positions) * 2) / total_encoded_size if total_encoded_size > 0 else 0,
            
            # Metadata for reconstruction
            'reconstruction_data': {
                'vertical_tier': vertical_encoding['tier'],
                'vertical_data': vertical_encoding['encoded_bytes'].hex(),
                'horizontal_tier': horizontal_encoding['tier'],
                'horizontal_data': horizontal_encoding['encoded_bytes'].hex(),
                'position_count': len(positions)
            },
            
            # Backward compatibility flags
            'has_coordinate_encoding': True,
            'exact_positioning': True,
            'template_dependent': True
        }
    
    def decode_word_positions(self, encoded_data: Dict[str, Any]) -> List[Dict[str, int]]:
        """
        Decode word positions from coordinate encoding
        
        CRITICAL FIX: Returns full position dicts with BOTH 'line' and 'horizontal'
        
        Args:
            encoded_data: Encoded position data from encode_word_positions
        
        Returns:
            List of position dicts with 'line' and 'horizontal' keys
        
        Example:
            >>> encoded = integrator.encode_word_positions('the', positions)
            >>> decoded = integrator.decode_word_positions(encoded)
            >>> decoded
            [{'line': 1, 'horizontal': 10}, {'line': 5, 'horizontal': 25}]
        """
        # Decode BOTH vertical and horizontal dimensions
        if 'reconstruction_data' in encoded_data:
            # Decode from reconstruction metadata
            recon_data = encoded_data['reconstruction_data']
            
            # Decode vertical (line) positions
            vertical_bytes = bytes.fromhex(recon_data['vertical_data'])
            vertical_tier = recon_data['vertical_tier']
            line_positions = self.decoder.decode(vertical_bytes, vertical_tier)
            
            # Decode horizontal positions
            horizontal_bytes = bytes.fromhex(recon_data['horizontal_data'])
            horizontal_tier = recon_data['horizontal_tier']
            horizontal_positions = self.decoder.decode(horizontal_bytes, horizontal_tier)
            
        elif 'vertical_encoded_bytes' in encoded_data and 'horizontal_encoded_bytes' in encoded_data:
            # Decode from direct byte fields
            line_positions = self.decoder.decode(
                encoded_data['vertical_encoded_bytes'],
                encoded_data['vertical_tier']
            )
            horizontal_positions = self.decoder.decode(
                encoded_data['horizontal_encoded_bytes'],
                encoded_data['horizontal_tier']
            )
        else:
            raise ValueError("No encoded data found - missing both reconstruction_data and encoded_bytes")
        
        # Combine into position dicts
        if len(line_positions) != len(horizontal_positions):
            raise ValueError(
                f"Dimension mismatch: {len(line_positions)} lines vs {len(horizontal_positions)} horizontals"
            )
        
        positions = [
            {'line': line, 'horizontal': horiz}
            for line, horiz in zip(line_positions, horizontal_positions)
        ]
        
        return positions
    
    def batch_encode_scanner_data(self, word_data: Dict[str, List[Dict[str, int]]]) -> Dict[str, Any]:
        """
        Batch encode all words from scanner
        
        Args:
            word_data: Dict mapping words to position lists
        
        Returns:
            Dict with all encoded words and statistics
        """
        encoded_words = {}
        
        for word, positions in word_data.items():
            # Skip words with empty position lists
            if not positions:
                continue
            encoded_words[word] = self.encode_word_positions(word, positions)
        
        return {
            'encoded_words': encoded_words,
            'total_words': len(encoded_words),  # Count only non-empty words
            'total_positions': sum(len(data['original_positions']) for data in encoded_words.values()),
            'total_encoded_bytes': sum(data['encoded_size'] for data in encoded_words.values()),
            'statistics': self.get_statistics()
        }
    
    def verify_roundtrip(self, word: str, positions: List[Dict[str, int]]) -> bool:
        """
        Verify encoding/decoding roundtrip accuracy
        
        CRITICAL FIX: Verifies BOTH line and horizontal coordinates
        
        Args:
            word: Word to test
            positions: Original position list
        
        Returns:
            True if roundtrip is accurate, False otherwise
        """
        # Encode
        encoded = self.encode_word_positions(word, positions)
        
        # Decode
        decoded_positions = self.decode_word_positions(encoded)
        
        # Verify BOTH dimensions
        original_sorted = sorted(positions, key=lambda p: (p['line'], p['horizontal']))
        decoded_sorted = sorted(decoded_positions, key=lambda p: (p['line'], p['horizontal']))
        
        # Check exact match
        if len(original_sorted) != len(decoded_sorted):
            return False
        
        for orig, decoded in zip(original_sorted, decoded_sorted):
            if orig['line'] != decoded['line'] or orig['horizontal'] != decoded['horizontal']:
                return False
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics"""
        stats = self.stats.copy()
        
        # Add encoder/decoder stats
        stats['encoder_stats'] = self.encoder.get_statistics()
        stats['decoder_stats'] = self.decoder.get_statistics()
        
        # Calculate average bytes per word
        if stats['words_processed'] > 0:
            stats['avg_bytes_per_word'] = stats['total_encoded_bytes'] / stats['words_processed']
        else:
            stats['avg_bytes_per_word'] = 0.0
        
        return stats
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.stats = {
            'words_processed': 0,
            'total_positions': 0,
            'total_encoded_bytes': 0,
            'compression_ratio': 0.0
        }
        self.encoder.reset_statistics()
        self.decoder.reset_statistics()


if __name__ == "__main__":
    # Self-test
    print("🔗 SCANNER COORDINATE INTEGRATION - Self Test")
    print("=" * 50)
    
    integrator = ScannerCoordinateIntegration()
    
    # Test data (simulating scanner output)
    test_data = {
        'the': [
            {'line': 1, 'horizontal': 10},
            {'line': 5, 'horizontal': 25},
            {'line': 10, 'horizontal': 42}
        ],
        'and': [
            {'line': 2, 'horizontal': 15},
            {'line': 7, 'horizontal': 30}
        ],
        'to': [
            {'line': 3, 'horizontal': 20}
        ]
    }
    
    print("\nIndividual word tests:")
    for word, positions in test_data.items():
        # Encode
        encoded = integrator.encode_word_positions(word, positions)
        
        print(f"\n  Word: '{word}'")
        print(f"    Positions: {[p['line'] for p in positions]}")
        print(f"    Tier: {encoded['tier']}")
        print(f"    Encoded size: {encoded['encoded_size']} bytes")
        print(f"    Compression: {encoded['compression_ratio']:.2f}x")
        
        # Decode and verify
        decoded = integrator.decode_word_positions(encoded)
        original_lines = sorted([p['line'] for p in positions])
        decoded_lines = sorted([p['line'] for p in decoded])
        match = original_lines == decoded_lines
        
        print(f"    Roundtrip: {'✅ PASS' if match else '❌ FAIL'}")
        print(f"    Decoded: {decoded}")
    
    # Batch test
    print("\n\nBatch encoding test:")
    batch_result = integrator.batch_encode_scanner_data(test_data)
    print(f"  Total words: {batch_result['total_words']}")
    print(f"  Avg bytes/word: {batch_result['statistics']['avg_bytes_per_word']:.2f}")
    print(f"  Compression ratio: {batch_result['statistics']['compression_ratio']:.2f}x")
    
    # Statistics
    print("\n\nIntegration statistics:")
    stats = integrator.get_statistics()
    print(f"  Words processed: {stats['words_processed']}")
    print(f"  Total positions: {stats['total_positions']}")
    print(f"  Total bytes: {stats['total_encoded_bytes']}")
    print(f"  Avg bytes/word: {stats['avg_bytes_per_word']:.2f}")
    
    print("\n✅ Scanner integration tests complete")
