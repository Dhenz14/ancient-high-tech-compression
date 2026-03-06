#!/usr/bin/env python3
"""
COORDINATE ENCODER - Main Encoding Engine
==========================================
Coordinate Lookup Encoding System - Phase 2

Main encoding engine that transforms position lists into optimal
tier-based compressed representations

Encoding strategy: Prioritize smallest encoding (0A → 0B → 1 → 2)

Dr. Chen (System Architecture Lead)
"""

from typing import List, Dict, Any, Tuple, Optional
import struct
from .bit_packer import BitPacker
from .pattern_matcher import PatternMatcher
from .template_cache import get_template_cache


class CoordinateEncoder:
    """
    Main coordinate encoding engine
    
    Encodes word position lists using optimal tier selection:
    - Tier 0A: 4 bits (ultra-common single lines)
    - Tier 0B: 1 byte (common patterns)
    - Tier 1: 2 bytes (medium patterns)
    - Tier 2: Delta encoding (rare patterns)
    """
    
    def __init__(self):
        """Initialize coordinate encoder"""
        self.bit_packer = BitPacker()
        self.pattern_matcher = PatternMatcher()
        self.cache = get_template_cache()
        
        # Base-94 character set for Tier 1 encoding
        self.base94_chars = ''.join([chr(i) for i in range(33, 127)])
        
        # Encoding statistics
        self.stats = {
            'words_encoded': 0,
            'total_bytes': 0,
            'tier0a_uses': 0,
            'tier0b_uses': 0,
            'tier1_uses': 0,
            'tier2_uses': 0
        }
        
        print("⚙️ COORDINATE ENCODER INITIALIZED")
        print("   Tier-marker-free encoding: 0A/0B (1-byte) → 1 (2-byte) → 2 (0xFF+delta)")
        print("   Target: 3-byte minimum for common words")
    
    def encode_positions(self, positions: List[int]) -> Dict[str, Any]:
        """
        Encode position list to optimal tier representation
        
        Args:
            positions: List of line positions for a word
        
        Returns:
            Dict containing:
            - tier: Tier name ('tier0a', 'tier0b', 'tier1', 'tier2')
            - encoded_bytes: Encoded data as bytes
            - original_positions: Original position list
            - compression_ratio: Original size / encoded size
        
        Example:
            >>> encoder = CoordinateEncoder()
            >>> result = encoder.encode_positions([1, 5, 10])
            >>> result['tier']
            'tier1'
            >>> len(result['encoded_bytes'])
            2
        """
        if not positions:
            positions = [1]  # Default to line 1
        
        # Match to optimal tier
        tier, code_or_pattern = self.pattern_matcher.match_pattern(positions)
        
        # Validate that pattern matching returned a valid result
        if code_or_pattern is None:
            raise ValueError(f"Pattern matching failed: no code or pattern returned for positions {positions}")
        
        # Encode based on tier
        if tier == 'tier0a':
            encoded_bytes = self._encode_tier0a(code_or_pattern)
            self.stats['tier0a_uses'] += 1
        elif tier == 'tier0b':
            encoded_bytes = self._encode_tier0b(code_or_pattern)
            self.stats['tier0b_uses'] += 1
        elif tier == 'tier1':
            encoded_bytes = self._encode_tier1(code_or_pattern)
            self.stats['tier1_uses'] += 1
        elif tier == 'tier2':
            encoded_bytes = self._encode_tier2(code_or_pattern)
            self.stats['tier2_uses'] += 1
        else:
            raise ValueError(f"Unknown tier: {tier}")
        
        # Calculate compression ratio
        original_size = len(positions)  # 1 byte per position in naive encoding
        encoded_size = len(encoded_bytes)
        compression_ratio = original_size / encoded_size if encoded_size > 0 else 0
        
        # Update statistics
        self.stats['words_encoded'] += 1
        self.stats['total_bytes'] += encoded_size
        
        return {
            'tier': tier,
            'encoded_bytes': encoded_bytes,
            'original_positions': positions,
            'encoded_size': encoded_size,
            'original_size': original_size,
            'compression_ratio': compression_ratio,
            'code_or_pattern': code_or_pattern
        }
    
    def _encode_tier0a(self, code: int) -> bytes:
        """
        Encode Tier 0A (1-byte code) - NO MARKER
        
        Returns direct template code without redundant tier marker.
        Tier is inferred from byte-length during decoding.
        """
        return bytes([code])  # Direct code, no marker
    
    def _encode_tier0b(self, code: str) -> bytes:
        """
        Encode Tier 0B (1-byte ASCII) - NO MARKER
        
        Returns direct ASCII character without redundant tier marker.
        Tier is inferred from byte-length during decoding.
        """
        return code.encode('ascii')  # Direct character, no marker
    
    def _encode_tier1(self, code: int) -> bytes:
        """
        Encode Tier 1 (2-byte base-94) - NO MARKER
        
        Returns direct 2-byte template code without redundant tier marker.
        Tier is inferred from byte-length during decoding.
        """
        # Convert code to base-94 representation
        char1 = self.base94_chars[code // 94]
        char2 = self.base94_chars[code % 94]
        
        # Return direct 2-byte code, no marker
        return (char1 + char2).encode('ascii')
    
    def _encode_tier2(self, positions: List[int]) -> bytes:
        """
        Encode Tier 2/3 (delta encoding with 0xFF format switch)
        
        CRITICAL: 0xFF is NOT a tier marker - it's a format switch indicating
        variable-length delta encoding follows. This is the ONLY marker byte
        in the entire system because delta encoding is variable-length.
        
        Format: [0xFF] [first_pos_2bytes] [delta1_2bytes] [delta2_2bytes] ...
        
        Uses 2-byte signed integers to support large gaps (±32767)
        """
        if not positions:
            return bytes([0xFF, 0, 0])  # Format switch + empty (2 bytes for consistency)
        
        # Encode first position as 2-byte unsigned (0-65535)
        encoded_bytes = bytearray([0xFF])  # 0xFF = variable-length format switch
        encoded_bytes.extend(positions[0].to_bytes(2, byteorder='big', signed=False))
        
        # Encode deltas as 2-byte signed integers (-32768 to +32767)
        for i in range(1, len(positions)):
            delta = positions[i] - positions[i-1]
            # Clamp delta to signed 16-bit range
            if delta < -32768 or delta > 32767:
                raise ValueError(f"Delta {delta} exceeds 16-bit signed range")
            encoded_bytes.extend(delta.to_bytes(2, byteorder='big', signed=True))
        
        return bytes(encoded_bytes)
    
    def encode_batch(self, position_lists: List[List[int]]) -> List[Dict[str, Any]]:
        """
        Encode multiple position lists
        
        Args:
            position_lists: List of position lists to encode
        
        Returns:
            List of encoding results
        """
        return [self.encode_positions(positions) for positions in position_lists]
    
    def encode_word_data(self, word_data: Dict[str, List[int]]) -> Dict[str, Any]:
        """
        Encode complete word → positions mapping
        
        Args:
            word_data: Dict mapping words to position lists
        
        Returns:
            Dict with encoded data and metadata
        """
        encoded_words = {}
        total_original_size = 0
        total_encoded_size = 0
        
        for word, positions in word_data.items():
            result = self.encode_positions(positions)
            encoded_words[word] = result
            total_original_size += result['original_size']
            total_encoded_size += result['encoded_size']
        
        overall_compression = total_original_size / total_encoded_size if total_encoded_size > 0 else 0
        
        return {
            'encoded_words': encoded_words,
            'total_words': len(word_data),
            'total_original_size': total_original_size,
            'total_encoded_size': total_encoded_size,
            'compression_ratio': overall_compression,
            'average_bytes_per_word': total_encoded_size / len(word_data) if word_data else 0
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get encoding statistics"""
        stats = self.stats.copy()
        
        if stats['words_encoded'] > 0:
            stats['average_bytes_per_word'] = int(stats['total_bytes'] / stats['words_encoded'])
            stats['tier0a_rate'] = int(stats['tier0a_uses'] / stats['words_encoded'])
            stats['tier0b_rate'] = int(stats['tier0b_uses'] / stats['words_encoded'])
            stats['tier1_rate'] = int(stats['tier1_uses'] / stats['words_encoded'])
            stats['tier2_rate'] = int(stats['tier2_uses'] / stats['words_encoded'])
        
        return stats
    
    def reset_statistics(self):
        """Reset encoding statistics"""
        self.stats = {
            'words_encoded': 0,
            'total_bytes': 0,
            'tier0a_uses': 0,
            'tier0b_uses': 0,
            'tier1_uses': 0,
            'tier2_uses': 0
        }


if __name__ == "__main__":
    # Self-test
    print("⚙️ COORDINATE ENCODER - Self Test")
    print("=" * 50)
    
    encoder = CoordinateEncoder()
    
    # Test individual encodings
    test_cases = [
        ([1], "Single line (Tier 0A expected)"),
        ([1, 2], "Two lines (Tier 0B expected)"),
        ([1, 2, 3], "Three lines (Tier 1 expected)"),
        ([7, 14, 21, 28, 35, 42, 49], "Seven lines (Tier 2 expected)"),
    ]
    
    print("\nIndividual encoding tests:")
    for positions, description in test_cases:
        result = encoder.encode_positions(positions)
        print(f"\n{description}")
        print(f"  Positions: {positions}")
        print(f"  Tier: {result['tier']}")
        print(f"  Encoded bytes: {result['encoded_bytes'].hex()}")
        print(f"  Size: {result['encoded_size']} bytes")
        print(f"  Compression: {result['compression_ratio']:.2f}x")
    
    # Test batch encoding
    print("\n\nBatch encoding test:")
    word_data = {
        'the': [1, 5, 10, 15, 20],
        'and': [2, 7, 12],
        'to': [3],
        'of': [4, 9]
    }
    
    batch_result = encoder.encode_word_data(word_data)
    print(f"  Total words: {batch_result['total_words']}")
    print(f"  Original size: {batch_result['total_original_size']} bytes")
    print(f"  Encoded size: {batch_result['total_encoded_size']} bytes")
    print(f"  Compression: {batch_result['compression_ratio']:.2f}x")
    print(f"  Avg bytes/word: {batch_result['average_bytes_per_word']:.2f}")
    
    # Statistics
    print("\n\nEncoder statistics:")
    stats = encoder.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n✅ Coordinate encoder tests complete")
