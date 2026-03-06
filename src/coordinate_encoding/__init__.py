"""
COORDINATE LOOKUP ENCODING SYSTEM
==================================
Dual-dimension coordinate encoding for Hive blockchain deployment

Implements 4-tier encoding strategy:
- Tier 0A: 4-bit codes for ultra-common patterns (16 patterns)
- Tier 0B: 1-byte ASCII for common patterns (94 patterns)
- Tier 1: 2-byte base-94 for medium patterns (8,836 patterns)
- Tier 2: 2-byte signed delta encoding (±32K range, unlimited patterns)

DUAL-DIMENSION STORAGE (vertical + horizontal coordinates):
- Template tier (0A/0B/1): 2-6 bytes per word (both dimensions combined)
- Delta tier (2): 6-10 bytes per word (both dimensions with 2-byte deltas)
- Average: 2-10 bytes per word depending on pattern complexity

GUARANTEES:
- 100% reconstruction accuracy (verified across all test cases)
- No data loss (duplicates, order, large gaps all preserved)
- Deterministic encoding/decoding
- Independent dimension encoding with order-preserved pairing

Dr. Chen (System Architecture Lead)
"""

from .bit_packer import BitPacker, pack_tier0a_codes, unpack_tier0a_codes
from .template_cache import TemplateCache, get_template_cache
from .pattern_matcher import PatternMatcher
from .coordinate_encoder import CoordinateEncoder
from .coordinate_decoder import CoordinateDecoder

__all__ = [
    'BitPacker',
    'pack_tier0a_codes',
    'unpack_tier0a_codes',
    'TemplateCache',
    'get_template_cache',
    'PatternMatcher',
    'CoordinateEncoder',
    'CoordinateDecoder',
]

__version__ = '2.0.0'
