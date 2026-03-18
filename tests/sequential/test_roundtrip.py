"""
Comprehensive round-trip tests for the sequential encoder/decoder.

Tests cover:
  - Basic prose
  - Contractions (don't, can't, they're, it's, won't, I'd, we've)
  - Punctuation (all trailing codes, leading quotes/parens)
  - Multi-char trailing punct (.", ,")
  - ALL CAPS words (NASA, FBI)
  - Mixed case words (iPhone, LaTeX, McDonald's)
  - Single capital letter words (I, A)
  - Dialogue with open/close quotes
  - Numbers and unknown words
  - Empty / single word
  - Long repetitive text (Article x10)
  - Code-like text
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from src.sequential.encoder import SequentialEncoder, _encode_varint
from src.sequential.decoder import SequentialDecoder, _decode_varint
from src.sequential.two_stage import TwoStageCompressor
from src.wordid.dictionary import Dictionary


@pytest.fixture(scope="module")
def d():
    return Dictionary()

@pytest.fixture(scope="module")
def enc(d):
    return SequentialEncoder(d)

@pytest.fixture(scope="module")
def dec(d):
    return SequentialDecoder(d)

@pytest.fixture(scope="module")
def ts(d):
    return TwoStageCompressor(d, method="zlib")  # use zlib (no optional dep)


def roundtrip(enc, dec, text):
    blob = enc.encode(text)
    result = dec.decode(blob)
    return result


# --- Basic sanity ---

class TestBasic:
    def test_empty_string(self, enc, dec):
        assert roundtrip(enc, dec, "") == ""

    def test_whitespace_only(self, enc, dec):
        assert roundtrip(enc, dec, "   ") == ""

    def test_single_word_lower(self, enc, dec):
        assert roundtrip(enc, dec, "hello") == "hello"

    def test_single_word_title(self, enc, dec):
        assert roundtrip(enc, dec, "Hello") == "Hello"

    def test_single_word_upper(self, enc, dec):
        assert roundtrip(enc, dec, "NASA") == "NASA"

    def test_two_words(self, enc, dec):
        assert roundtrip(enc, dec, "hello world") == "hello world"

    def test_known_word(self, enc, dec):
        # "the" is rank 1 — single byte in rank stream
        assert roundtrip(enc, dec, "the") == "the"

    def test_known_word_capitalized(self, enc, dec):
        assert roundtrip(enc, dec, "The") == "The"

    def test_sentence(self, enc, dec):
        text = "The quick brown fox jumps over the lazy dog"
        assert roundtrip(enc, dec, text) == text


# --- Contractions ---

class TestContractions:
    def test_dont(self, enc, dec):
        assert roundtrip(enc, dec, "don't") == "don't"

    def test_cant(self, enc, dec):
        assert roundtrip(enc, dec, "can't") == "can't"

    def test_wont(self, enc, dec):
        assert roundtrip(enc, dec, "won't") == "won't"

    def test_theyre(self, enc, dec):
        assert roundtrip(enc, dec, "they're") == "they're"

    def test_its(self, enc, dec):
        assert roundtrip(enc, dec, "it's") == "it's"

    def test_ive(self, enc, dec):
        assert roundtrip(enc, dec, "I've") == "I've"

    def test_id(self, enc, dec):
        assert roundtrip(enc, dec, "I'd") == "I'd"

    def test_ill(self, enc, dec):
        assert roundtrip(enc, dec, "I'll") == "I'll"

    def test_contraction_with_comma(self, enc, dec):
        assert roundtrip(enc, dec, "don't, can't") == "don't, can't"

    def test_contraction_sentence(self, enc, dec):
        text = "I don't think they're going to make it"
        assert roundtrip(enc, dec, text) == text


# --- Trailing punctuation ---

class TestTrailingPunct:
    def test_period(self, enc, dec):
        assert roundtrip(enc, dec, "Hello.") == "Hello."

    def test_comma(self, enc, dec):
        assert roundtrip(enc, dec, "Hello,") == "Hello,"

    def test_exclamation(self, enc, dec):
        assert roundtrip(enc, dec, "Hello!") == "Hello!"

    def test_question(self, enc, dec):
        assert roundtrip(enc, dec, "Hello?") == "Hello?"

    def test_semicolon(self, enc, dec):
        assert roundtrip(enc, dec, "Hello;") == "Hello;"

    def test_colon(self, enc, dec):
        assert roundtrip(enc, dec, "Hello:") == "Hello:"

    def test_close_dquote(self, enc, dec):
        assert roundtrip(enc, dec, 'Hello"') == 'Hello"'

    def test_close_paren(self, enc, dec):
        assert roundtrip(enc, dec, "Hello)") == "Hello)"

    def test_close_bracket(self, enc, dec):
        assert roundtrip(enc, dec, "Hello]") == "Hello]"

    def test_hyphen(self, enc, dec):
        assert roundtrip(enc, dec, "Hello-") == "Hello-"

    def test_ellipsis(self, enc, dec):
        assert roundtrip(enc, dec, "Hello...") == "Hello..."

    def test_period_dquote(self, enc, dec):
        # Very common in dialogue: He said "hello."
        assert roundtrip(enc, dec, 'hello."') == 'hello."'

    def test_comma_dquote(self, enc, dec):
        assert roundtrip(enc, dec, 'hello,"') == 'hello,"'

    def test_sentence_with_period(self, enc, dec):
        text = "The cat sat. The dog ran."
        assert roundtrip(enc, dec, text) == text


# --- Leading punctuation ---

class TestLeadingPunct:
    def test_open_dquote(self, enc, dec):
        assert roundtrip(enc, dec, '"hello') == '"hello'

    def test_open_paren(self, enc, dec):
        assert roundtrip(enc, dec, '(hello') == '(hello'

    def test_open_bracket(self, enc, dec):
        assert roundtrip(enc, dec, '[hello') == '[hello'

    def test_leading_and_trailing(self, enc, dec):
        # "(hello)" — leading paren + trailing paren
        assert roundtrip(enc, dec, "(hello)") == "(hello)"

    def test_quoted_word(self, enc, dec):
        # "hello" — leading dquote + trailing dquote
        text = '"hello"'
        assert roundtrip(enc, dec, text) == text

    def test_quoted_sentence(self, enc, dec):
        # Note: spaces split the string. "Hello world" → ["Hello, "world"]
        # The closing " attaches to the last token
        text = '"Hello world"'
        assert roundtrip(enc, dec, text) == text


# --- Capitalization ---

class TestCaps:
    def test_lower(self, enc, dec):
        assert roundtrip(enc, dec, "apple") == "apple"

    def test_title(self, enc, dec):
        assert roundtrip(enc, dec, "Apple") == "Apple"

    def test_all_caps(self, enc, dec):
        assert roundtrip(enc, dec, "NASA") == "NASA"

    def test_all_caps_known_word(self, enc, dec):
        # "THE" — all caps version of known word "the"
        assert roundtrip(enc, dec, "THE") == "THE"

    def test_all_caps_sentence(self, enc, dec):
        assert roundtrip(enc, dec, "FBI CIA NSA") == "FBI CIA NSA"

    def test_mixed_case(self, enc, dec):
        # These go through extra section
        assert roundtrip(enc, dec, "iPhone") == "iPhone"

    def test_mixed_case_mcdonalds(self, enc, dec):
        assert roundtrip(enc, dec, "McDonald's") == "McDonald's"

    def test_caps_in_sentence(self, enc, dec):
        text = "The FBI and CIA work together"
        assert roundtrip(enc, dec, text) == text

    def test_single_capital_i(self, enc, dec):
        assert roundtrip(enc, dec, "I") == "I"

    def test_single_capital_a(self, enc, dec):
        assert roundtrip(enc, dec, "A") == "A"


# --- Possessives ---

class TestPossessives:
    def test_possessive_s(self, enc, dec):
        # "dog's" — apostrophe + s is a contraction pattern, keeps intact
        assert roundtrip(enc, dec, "dog's") == "dog's"

    def test_possessive_trailing(self, enc, dec):
        # "James'" — apostrophe at end = close squote
        assert roundtrip(enc, dec, "James'") == "James'"

    def test_possessive_sentence(self, enc, dec):
        text = "the dog's bone was James' favorite"
        assert roundtrip(enc, dec, text) == text


# --- Numbers and unknown words ---

class TestUnknownWords:
    def test_number(self, enc, dec):
        assert roundtrip(enc, dec, "42") == "42"

    def test_dollar_number(self, enc, dec):
        # "$100" — $ not in leading RE, goes as unknown word
        assert roundtrip(enc, dec, "$100") == "$100"

    def test_large_number(self, enc, dec):
        assert roundtrip(enc, dec, "1000000") == "1000000"

    def test_mixed_alphanum(self, enc, dec):
        assert roundtrip(enc, dec, "abc123") == "abc123"

    def test_unknown_with_punct(self, enc, dec):
        assert roundtrip(enc, dec, "42.") == "42."

    def test_sentence_with_numbers(self, enc, dec):
        text = "There were 42 people and 100 cars"
        assert roundtrip(enc, dec, text) == text


# --- Prose tests ---

class TestProse:
    def test_article_paragraph(self, enc, dec):
        text = ("The history of science is a story of human curiosity and determination. "
                "From the ancient Greeks who first asked questions about the nature of the world "
                "to the modern researchers who probe the depths of space and the structure of atoms, "
                "people have always been driven to understand the universe around them.")
        assert roundtrip(enc, dec, text) == text

    def test_blog_with_contractions(self, enc, dec):
        text = ("I was walking down the street yesterday when I saw something that completely "
                "changed my perspective on life. I don't think about it often. He said the "
                "pigeons were his friends now, and they never judged him.")
        assert roundtrip(enc, dec, text) == text

    def test_dialogue(self, enc, dec):
        text = 'She said "Hello." He replied "How are you?"'
        assert roundtrip(enc, dec, text) == text

    def test_repetitive_article_x5(self, enc, dec):
        article = ("The history of science is a story of human curiosity and determination. "
                   "People have always been driven to understand the universe around them.")
        text = " ".join([article] * 5)
        assert roundtrip(enc, dec, text) == text


# --- Varint encoding ---

class TestVarint:
    def test_varint_zero(self):
        assert _encode_varint(0) == b'\x00'

    def test_varint_small(self):
        assert _encode_varint(1) == b'\x01'
        assert _encode_varint(127) == b'\x7f'

    def test_varint_two_bytes(self):
        encoded = _encode_varint(128)
        assert len(encoded) == 2
        assert encoded[0] == 0x80  # continuation bit
        assert encoded[1] == 0x01

    def test_varint_round_trip(self):
        for val in [0, 1, 63, 64, 127, 128, 255, 256, 16383, 16384, 2097151, 2097152]:
            encoded = _encode_varint(val)
            decoded, consumed = _decode_varint(encoded, 0)
            assert decoded == val, f"varint round-trip failed for {val}"
            assert consumed == len(encoded)

    def test_varint_stream(self):
        """Multiple varints packed together decode correctly."""
        buf = bytearray()
        vals = [1, 128, 0, 16384, 255, 65535]
        for v in vals:
            buf.extend(_encode_varint(v))

        offset = 0
        decoded = []
        for _ in range(len(vals)):
            v, c = _decode_varint(bytes(buf), offset)
            decoded.append(v)
            offset += c

        assert decoded == vals


# --- Blob format integrity ---

class TestBlobFormat:
    def test_version_byte(self, enc):
        blob = enc.encode("hello")
        assert blob[0] == 0x04  # version 3

    def test_token_count(self, enc):
        blob = enc.encode("hello world foo")
        count = (blob[1] << 16) | (blob[2] << 8) | blob[3]
        assert count == 3

    def test_empty_blob(self, enc):
        blob = enc.encode("")
        assert blob[0] == 0x04
        count = (blob[1] << 16) | (blob[2] << 8) | blob[3]
        assert count == 0

    def test_rank_len_integrity(self, enc):
        # v3 merged format: [version:1][count:3][main_stream][extra_section]
        # No separate rank_len header — main_stream is parsed by reading count varints
        blob = enc.encode("the of and to a")
        count = (blob[1] << 16) | (blob[2] << 8) | blob[3]
        assert count == 5
        # Blob must be at least version(1) + count(3) + count varints (>=count bytes)
        assert len(blob) >= 4 + count


# --- Two-stage round-trip ---

class TestTwoStage:
    def test_zlib_roundtrip(self, ts):
        texts = [
            "hello world",
            "The quick brown fox jumps over the lazy dog.",
            "don't won't can't they're",
            "NASA and FBI work together.",
            'She said "Hello." He replied "How are you?"',
        ]
        for text in texts:
            blob = ts.compress(text)
            result = ts.decompress(blob)
            assert result == text, f"Two-stage round-trip failed for: {text!r}"

    def test_zlib_repetitive(self, ts):
        article = "The history of science is a story of human curiosity and determination."
        text = " ".join([article] * 10)
        blob = ts.compress(text)
        result = ts.decompress(blob)
        assert result == text


# --- Edge cases ---

class TestEdgeCases:
    def test_multiple_spaces_collapsed(self, enc, dec):
        # split() collapses multiple spaces — that's expected behavior
        result = roundtrip(enc, dec, "hello  world")
        assert result == "hello world"

    def test_leading_space_stripped(self, enc, dec):
        result = roundtrip(enc, dec, "  hello")
        assert result == "hello"

    def test_all_punct_word(self, enc, dec):
        # A chunk that's entirely punct (e.g. "---") should not crash
        result = roundtrip(enc, dec, "--- hello")
        assert "hello" in result  # hello must survive

    def test_long_unknown_word(self, enc, dec):
        word = "supercalifragilisticexpialidocious"
        assert roundtrip(enc, dec, word) == word

    def test_unicode(self, enc, dec):
        # café — unicode word, stored as unknown
        assert roundtrip(enc, dec, "café") == "café"

    def test_unicode_sentence(self, enc, dec):
        text = "the café was naïve about résumés"
        assert roundtrip(enc, dec, text) == text

    def test_hyphenated_word(self, enc, dec):
        # "well-known" — hyphen is in the middle, not at end
        # trailing RE only matches hyphen at END of string
        # So "well-known" should pass through as a word
        result = roundtrip(enc, dec, "well-known")
        assert result == "well-known"

    def test_abbreviation_with_period(self, enc, dec):
        # "Dr." — period at end → T_PERIOD, word = "dr"
        assert roundtrip(enc, dec, "Dr.") == "Dr."

    def test_us_abbreviation(self, enc, dec):
        # "U.S." — ends with period, internal periods stay
        # trailing RE matches "." at end
        # chunk becomes "U.S" — stored as unknown
        result = roundtrip(enc, dec, "U.S.")
        assert result == "U.S."
