#!/usr/bin/env python3
"""
TEMPLATE CACHE - Efficient Template Loading and Caching
========================================================
Coordinate Lookup Encoding System - Phase 3

Loads and caches coordinate pattern templates for fast lookup
Optimizes memory usage and provides efficient lookup methods

Dr. Kim (Template System Architect)
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache


class TemplateCache:
    """
    Efficient template loading and caching system
    
    Loads coordinate pattern templates from JSON files and provides
    fast lookup methods with memory optimization
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize template cache
        
        Args:
            template_dir: Directory containing template JSON files
                         (defaults to src/coordinate_encoding/templates/coordinate_patterns/)
        """
        if template_dir is None:
            # Default to templates directory in coordinate_encoding
            self.template_dir = Path(__file__).parent / 'templates' / 'coordinate_patterns'
        else:
            self.template_dir = Path(template_dir)
        
        # Template storage
        self.templates = {
            'tier0a': {},
            'tier0b_single': {},
            'tier0b_double': {},
            'tier1': {},
            'metadata': {}
        }
        
        # Reverse lookup indices for fast pattern matching
        self.reverse_indices = {
            'tier0a': {},
            'tier0b_single': {},
            'tier0b_double': {},
            'tier1': {}
        }
        
        # Cache statistics
        self.stats = {
            'templates_loaded': False,
            'total_patterns': 0,
            'tier0a_count': 0,
            'tier0b_count': 0,
            'tier1_count': 0,
            'load_time_ms': 0
        }
        
        print(f"📦 TEMPLATE CACHE INITIALIZED")
        print(f"   Template directory: {self.template_dir}")
    
    def load_templates(self, force_reload: bool = False) -> bool:
        """
        Load all coordinate pattern templates from JSON files
        
        Args:
            force_reload: Force reload even if already loaded
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if self.stats['templates_loaded'] and not force_reload:
            print("⚡ Templates already loaded (use force_reload=True to reload)")
            return True
        
        import time
        start_time = time.time()
        
        print(f"📂 Loading templates from: {self.template_dir}")
        
        try:
            # Load horizontal templates (has all tiers)
            horiz_file = self.template_dir / 'horizontal_coordinate_templates.json'
            
            if not horiz_file.exists():
                print(f"❌ Template file not found: {horiz_file}")
                return False
            
            with open(horiz_file, 'r') as f:
                template_data = json.load(f)
            
            # Load each tier
            self.templates['tier0a'] = self._convert_keys(template_data.get('tier0a', {}), int)
            self.templates['tier0b_single'] = template_data.get('tier0b_single', {})
            self.templates['tier0b_double'] = template_data.get('tier0b_double', {})
            self.templates['tier1'] = self._convert_keys(template_data.get('tier1', {}), int)
            self.templates['metadata'] = template_data.get('metadata', {})
            
            # Build reverse indices for fast lookup
            self._build_reverse_indices()
            
            # Update statistics
            self.stats['tier0a_count'] = len(self.templates['tier0a'])
            self.stats['tier0b_count'] = (
                len(self.templates['tier0b_single']) +
                len(self.templates['tier0b_double'])
            )
            self.stats['tier1_count'] = len(self.templates['tier1'])
            self.stats['total_patterns'] = (
                self.stats['tier0a_count'] +
                self.stats['tier0b_count'] +
                self.stats['tier1_count']
            )
            self.stats['load_time_ms'] = (time.time() - start_time) * 1000
            self.stats['templates_loaded'] = True
            
            print(f"✅ Templates loaded successfully")
            print(f"   Tier 0A patterns: {self.stats['tier0a_count']}")
            print(f"   Tier 0B patterns: {self.stats['tier0b_count']}")
            print(f"   Tier 1 patterns: {self.stats['tier1_count']}")
            print(f"   Total patterns: {self.stats['total_patterns']:,}")
            print(f"   Load time: {self.stats['load_time_ms']:.2f} ms")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading templates: {e}")
            return False
    
    def _convert_keys(self, d: Dict, key_type: type) -> Dict:
        """Convert string keys to specified type"""
        return {key_type(k): v for k, v in d.items()}
    
    def _build_reverse_indices(self):
        """Build reverse lookup indices: position_list → code"""
        print("🔍 Building reverse lookup indices...")
        
        # Tier 0A: single-element lists
        for code, positions in self.templates['tier0a'].items():
            key = tuple(positions)
            self.reverse_indices['tier0a'][key] = code
        
        # Tier 0B single: single-element lists
        for char, positions in self.templates['tier0b_single'].items():
            key = tuple(positions)
            self.reverse_indices['tier0b_single'][key] = char
        
        # Tier 0B double: two-element lists
        for char, positions in self.templates['tier0b_double'].items():
            key = tuple(positions)
            self.reverse_indices['tier0b_double'][key] = char
        
        # Tier 1: variable-length lists
        for code, positions in self.templates['tier1'].items():
            key = tuple(positions)
            self.reverse_indices['tier1'][key] = code
        
        print(f"   Built {len(self.reverse_indices['tier0a'])} Tier 0A reverse entries")
        print(f"   Built {len(self.reverse_indices['tier0b_single']) + len(self.reverse_indices['tier0b_double'])} Tier 0B reverse entries")
        print(f"   Built {len(self.reverse_indices['tier1'])} Tier 1 reverse entries")
    
    def lookup_pattern(self, positions: List[int]) -> Optional[Tuple[str, Any]]:
        """
        Look up coordinate pattern and return tier + code
        
        Args:
            positions: List of line positions to match
        
        Returns:
            Tuple of (tier_name, code) if found, None otherwise
            
        Example:
            >>> cache = TemplateCache()
            >>> cache.load_templates()
            >>> cache.lookup_pattern([1])
            ('tier0a', 0)
        """
        if not self.stats['templates_loaded']:
            self.load_templates()
        
        key = tuple(sorted(positions))
        
        # Try Tier 0A first (smallest encoding)
        if key in self.reverse_indices['tier0a']:
            return ('tier0a', self.reverse_indices['tier0a'][key])
        
        # Try Tier 0B
        if key in self.reverse_indices['tier0b_single']:
            return ('tier0b_single', self.reverse_indices['tier0b_single'][key])
        
        if key in self.reverse_indices['tier0b_double']:
            return ('tier0b_double', self.reverse_indices['tier0b_double'][key])
        
        # Try Tier 1
        if key in self.reverse_indices['tier1']:
            return ('tier1', self.reverse_indices['tier1'][key])
        
        # No match found - will need Tier 2 (delta encoding)
        return None
    
    def get_pattern(self, tier: str, code: Any) -> Optional[List[int]]:
        """
        Get position list for given tier and code
        
        Args:
            tier: Tier name ('tier0a', 'tier0b_single', 'tier0b_double', 'tier1')
            code: Code value (int for tier0a/tier1, str for tier0b)
        
        Returns:
            List of positions if found, None otherwise
        """
        if not self.stats['templates_loaded']:
            self.load_templates()
        
        template_dict = self.templates.get(tier, {})
        return template_dict.get(code)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get template metadata"""
        if not self.stats['templates_loaded']:
            self.load_templates()
        
        return self.templates['metadata']
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.stats.copy()
    
    @lru_cache(maxsize=1024)
    def hash_pattern(self, positions: Tuple[int, ...]) -> str:
        """
        Generate hash for position pattern (cached for performance)
        
        Args:
            positions: Tuple of positions
        
        Returns:
            SHA256 hash of pattern
        """
        pattern_str = ','.join(map(str, sorted(positions)))
        return hashlib.sha256(pattern_str.encode()).hexdigest()[:16]


# Global template cache instance (singleton pattern)
_global_cache = None


def get_template_cache() -> TemplateCache:
    """Get global template cache instance (singleton)"""
    global _global_cache
    if _global_cache is None:
        _global_cache = TemplateCache()
        _global_cache.load_templates()
    return _global_cache


if __name__ == "__main__":
    # Self-test
    print("📦 TEMPLATE CACHE - Self Test")
    print("=" * 50)
    
    cache = TemplateCache()
    
    # Test 1: Load templates
    success = cache.load_templates()
    print(f"\nLoad success: {success}")
    
    if success:
        # Test 2: Lookup patterns
        test_patterns = [
            [1],
            [1, 2],
            [5, 10],
            [1, 2, 3]
        ]
        
        print("\nPattern lookup tests:")
        for pattern in test_patterns:
            result = cache.lookup_pattern(pattern)
            print(f"  {pattern} → {result}")
        
        # Test 3: Reverse lookup
        print("\nReverse lookup tests:")
        print(f"  Tier 0A code 0 → {cache.get_pattern('tier0a', 0)}")
        print(f"  Tier 0B '0' → {cache.get_pattern('tier0b_single', '0')}")
        
        # Test 4: Stats
        print("\nCache statistics:")
        stats = cache.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    print("\n✅ Template cache tests complete")
