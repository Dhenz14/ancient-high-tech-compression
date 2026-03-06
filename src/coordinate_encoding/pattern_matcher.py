#!/usr/bin/env python3
"""
PATTERN MATCHER - Fast Hash-Based Template Lookup
==================================================
Coordinate Lookup Encoding System - Phase 2

Fast pattern matching using hash-based lookups
Determines optimal tier for coordinate pattern encoding

Dr. Rodriguez (Pattern Recognition Lead)
"""

from typing import List, Optional, Tuple, Any, Dict
import hashlib
from .template_cache import TemplateCache, get_template_cache


class PatternMatcher:
    """
    Fast hash-based pattern matching for coordinate templates
    
    Matches coordinate patterns to optimal encoding tier using
    hash lookups and template indices
    """
    
    def __init__(self, template_cache: Optional[TemplateCache] = None):
        """
        Initialize pattern matcher
        
        Args:
            template_cache: Template cache instance (uses global if None)
        """
        self.cache = template_cache or get_template_cache()
        
        # Ensure templates are loaded
        if not self.cache.stats['templates_loaded']:
            self.cache.load_templates()
        
        # Performance statistics
        self.stats = {
            'lookups': 0,
            'tier0a_hits': 0,
            'tier0b_hits': 0,
            'tier1_hits': 0,
            'tier2_required': 0
        }
        
        print("🔍 PATTERN MATCHER INITIALIZED")
        print(f"   Templates loaded: {self.cache.stats['total_patterns']:,} patterns")
    
    def match_pattern(self, positions: List[int]) -> Tuple[str, Optional[Any]]:
        """
        Match position list to optimal encoding tier
        
        Args:
            positions: List of line positions for a word
        
        Returns:
            Tuple of (tier_name, code_or_pattern)
            - tier_name: 'tier0a', 'tier0b', 'tier1', or 'tier2'
            - code_or_pattern: Code value for tiers 0A/0B/1, position list for tier 2
        
        Example:
            >>> matcher = PatternMatcher()
            >>> matcher.match_pattern([1])
            ('tier0a', 0)
            >>> matcher.match_pattern([5, 17, 23, 45, 67, 89])
            ('tier2', [5, 17, 23, 45, 67, 89])
        """
        self.stats['lookups'] += 1
        
        if not positions:
            # Empty pattern - use Tier 0A code 0 (represents line 1)
            return ('tier0a', 0)
        
        # CRITICAL FIX: Detect duplicates and non-sorted sequences
        # Template tiers (0A/0B/1) only work for SORTED patterns
        # Force Tier 2 for any pattern that doesn't match natural sorting
        
        has_duplicates = len(positions) != len(set(positions))
        normalized_positions = sorted(set(positions))
        is_already_sorted = (list(positions) == normalized_positions)
        
        if has_duplicates or not is_already_sorted:
            # Force Tier 2 (delta encoding) to preserve:
            # 1. Duplicates (e.g., [1,1,1])
            # 2. Non-sorted sequences (e.g., [10,5,1])
            self.stats['tier2_required'] += 1
            return ('tier2', positions)  # Return ORIGINAL list unchanged!
        
        # Pattern is already sorted and has no duplicates - safe for template lookup
        # Try template lookup with the (already sorted) positions
        result = self.cache.lookup_pattern(positions)
        
        if result is not None:
            tier_name, code = result
            
            # Update statistics
            if tier_name == 'tier0a':
                self.stats['tier0a_hits'] += 1
            elif tier_name.startswith('tier0b'):
                self.stats['tier0b_hits'] += 1
                tier_name = 'tier0b'  # Normalize tier0b_single/double to tier0b
            elif tier_name == 'tier1':
                self.stats['tier1_hits'] += 1
            
            return (tier_name, code)
        
        # No template match - requires Tier 2 (delta encoding)
        # CRITICAL: Return ORIGINAL positions (in original order)
        self.stats['tier2_required'] += 1
        return ('tier2', positions)  # Return ORIGINAL list unchanged!
    
    def batch_match(self, position_lists: List[List[int]]) -> List[Tuple[str, Any]]:
        """
        Match multiple position lists efficiently
        
        Args:
            position_lists: List of position lists to match
        
        Returns:
            List of (tier_name, code_or_pattern) tuples
        """
        return [self.match_pattern(positions) for positions in position_lists]
    
    def get_pattern_hash(self, positions: List[int]) -> str:
        """
        Generate consistent hash for position pattern
        
        Args:
            positions: List of line positions
        
        Returns:
            Hexadecimal hash string
        """
        positions = sorted(set(positions))
        pattern_str = ','.join(map(str, positions))
        return hashlib.sha256(pattern_str.encode()).hexdigest()[:16]
    
    def estimate_encoding_size(self, tier: str, code_or_pattern: Any) -> int:
        """
        Estimate encoded size in bytes for given tier
        
        Args:
            tier: Tier name
            code_or_pattern: Code or pattern data
        
        Returns:
            Estimated size in bytes
        """
        if tier == 'tier0a':
            # 4 bits, but packed 2 per byte
            return 0.5  # Half byte per code
        elif tier == 'tier0b':
            # 1 ASCII character
            return 1
        elif tier == 'tier1':
            # 2 ASCII characters (base-94 encoding)
            return 2
        elif tier == 'tier2':
            # Delta encoding: 1 byte per position
            if isinstance(code_or_pattern, list):
                return len(code_or_pattern)
            return 0
        
        return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pattern matching statistics"""
        stats = self.stats.copy()
        
        if stats['lookups'] > 0:
            stats['tier0a_rate'] = stats['tier0a_hits'] / stats['lookups']
            stats['tier0b_rate'] = stats['tier0b_hits'] / stats['lookups']
            stats['tier1_rate'] = stats['tier1_hits'] / stats['lookups']
            stats['tier2_rate'] = stats['tier2_required'] / stats['lookups']
            
            # Calculate average compression (assuming avg 3 positions per word)
            avg_positions = 3
            tier0a_savings = stats['tier0a_hits'] * (avg_positions - 0.5)
            tier0b_savings = stats['tier0b_hits'] * (avg_positions - 1)
            tier1_savings = stats['tier1_hits'] * (avg_positions - 2)
            tier2_cost = stats['tier2_required'] * (avg_positions - avg_positions)
            
            total_savings = tier0a_savings + tier0b_savings + tier1_savings + tier2_cost
            stats['estimated_compression_ratio'] = total_savings / (stats['lookups'] * avg_positions) if stats['lookups'] > 0 else 0
        
        return stats
    
    def reset_statistics(self):
        """Reset statistics counters"""
        self.stats = {
            'lookups': 0,
            'tier0a_hits': 0,
            'tier0b_hits': 0,
            'tier1_hits': 0,
            'tier2_required': 0
        }


if __name__ == "__main__":
    # Self-test
    print("🔍 PATTERN MATCHER - Self Test")
    print("=" * 50)
    
    matcher = PatternMatcher()
    
    # Test patterns
    test_patterns = [
        ([1], "Single line - should be Tier 0A"),
        ([5], "Another single line - should be Tier 0A"),
        ([1, 2], "Two lines - should be Tier 0B"),
        ([10, 20], "Common pair - should be Tier 0B"),
        ([1, 2, 3], "Three lines - should be Tier 1"),
        ([5, 15, 25, 35, 45], "Five lines - should be Tier 1 or 2"),
        ([7, 13, 19, 23, 29, 31, 37], "Seven lines - likely Tier 2"),
    ]
    
    print("\nPattern matching tests:")
    for positions, description in test_patterns:
        tier, code = matcher.match_pattern(positions)
        size = matcher.estimate_encoding_size(tier, code)
        print(f"  {positions}")
        print(f"    {description}")
        print(f"    → {tier}, code/pattern: {code}, size: {size} bytes")
    
    # Test statistics
    print("\nMatcher statistics:")
    stats = matcher.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n✅ Pattern matcher tests complete")
