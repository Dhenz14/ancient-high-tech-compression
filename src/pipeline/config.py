"""
Pipeline configuration constants.
"""

VERSION = 1
MAX_LINE_WIDTH = 80
MAX_TOKENS = 65535
MAX_UNIQUE_WORDS = 65535
MAX_LINES = 65535
HIVE_TARGET_BYTES = 5000

# Word ID encoding boundaries
RANK_1BYTE_MAX = 127         # ranks 1-127 → 1 byte
RANK_2BYTE_MAX = 16_511      # ranks 128-16511 → 2 bytes
RANK_3BYTE_MAX = 249_777     # ranks 16512-249777 → 3 bytes

# Unknown word escape byte
UNKNOWN_WORD_MARKER = 0x00

# Flags bitfield
FLAG_HAS_BLANKS = 0x01
FLAG_HAS_MORPHOLOGY = 0x02
FLAG_HAS_UNKNOWN_WORDS = 0x04
FLAG_BITPACKED_POSITIONS = 0x08  # combined (row,slot) 11-bit bitpacking
