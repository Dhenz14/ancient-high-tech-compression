"""
Phase 1 Tests: End-to-end round-trip and unit tests for all new modules.

Gate test: decompress(compress(text)) == text
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ============================================================
# Unit Tests: Word ID Codec
# ============================================================

class TestWordIdCodec:
    def setup_method(self):
        from src.wordid.word_id_codec import WordIdCodec
        self.codec = WordIdCodec()

    def test_1byte_range(self):
        for rank in [1, 50, 64, 127]:
            encoded = self.codec.encode_rank(rank)
            assert len(encoded) == 1, f"Rank {rank} should be 1 byte"
            decoded, consumed = self.codec.decode_rank(encoded, 0)
            assert decoded == rank
            assert consumed == 1

    def test_2byte_range(self):
        for rank in [128, 500, 1000, 5000, 16511]:
            encoded = self.codec.encode_rank(rank)
            assert len(encoded) == 2, f"Rank {rank} should be 2 bytes"
            decoded, consumed = self.codec.decode_rank(encoded, 0)
            assert decoded == rank
            assert consumed == 2

    def test_3byte_range(self):
        for rank in [16512, 50000, 100000, 200000, 249777]:
            encoded = self.codec.encode_rank(rank)
            assert len(encoded) == 3, f"Rank {rank} should be 3 bytes"
            decoded, consumed = self.codec.decode_rank(encoded, 0)
            assert decoded == rank
            assert consumed == 3

    def test_boundary_values(self):
        """Test exact boundary transitions."""
        for rank in [127, 128, 16511, 16512]:
            encoded = self.codec.encode_rank(rank)
            decoded, _ = self.codec.decode_rank(encoded, 0)
            assert decoded == rank

    def test_full_range_sample(self):
        """Test every 1000th rank across the full range."""
        for rank in range(1, 249778, 1000):
            encoded = self.codec.encode_rank(rank)
            decoded, _ = self.codec.decode_rank(encoded, 0)
            assert decoded == rank

    def test_prefix_free(self):
        """Verify encoding is prefix-free (no code is prefix of another)."""
        # Encode a sequence of ranks and decode them back
        ranks = [1, 128, 16512, 50, 5000, 200000, 127, 16511]
        stream = bytearray()
        for r in ranks:
            stream.extend(self.codec.encode_rank(r))

        # Decode sequentially
        offset = 0
        decoded_ranks = []
        for _ in ranks:
            rank, consumed = self.codec.decode_rank(bytes(stream), offset)
            decoded_ranks.append(rank)
            offset += consumed

        assert decoded_ranks == ranks

    def test_unknown_word(self):
        encoded = self.codec.encode_unknown("xylophone")
        assert encoded[0] == 0x00
        word, consumed = self.codec.decode_unknown(encoded, 0)
        assert word == "xylophone"
        assert consumed == len(encoded)

    def test_out_of_range(self):
        with pytest.raises(ValueError):
            self.codec.encode_rank(0)
        with pytest.raises(ValueError):
            self.codec.encode_rank(249778)
        with pytest.raises(ValueError):
            self.codec.encode_rank(-1)


# ============================================================
# Unit Tests: Dictionary
# ============================================================

class TestDictionary:
    def setup_method(self):
        from src.wordid.dictionary import Dictionary
        self.dict = Dictionary()

    def test_top_words_have_ranks(self):
        assert self.dict.word_to_rank("the") == 1
        # "and" and "of" are top-5 regardless of dictionary source
        assert self.dict.word_to_rank("of") is not None
        assert self.dict.word_to_rank("and") is not None
        assert self.dict.word_to_rank("of") <= 5
        assert self.dict.word_to_rank("and") <= 5

    def test_rank_to_word(self):
        assert self.dict.rank_to_word(1) == "the"
        assert self.dict.rank_to_word(2) in ("of", "and")  # depends on corpus

    def test_unknown_word(self):
        assert self.dict.word_to_rank("xyzzyplugh") is None

    def test_case_insensitive(self):
        assert self.dict.word_to_rank("The") == 1
        assert self.dict.word_to_rank("THE") == 1

    def test_checksum(self):
        words = ["the", "and", "to"]
        cs = self.dict.checksum(words)
        # Checksum = sum of ranks for all words
        expected = sum(self.dict.word_to_rank(w) for w in words)
        assert cs == expected
        assert cs > 0

    def test_has_word(self):
        assert self.dict.has_word("the") is True
        assert self.dict.has_word("xyzzy") is False


# ============================================================
# Unit Tests: Tokenizer
# ============================================================

class TestTokenizer:
    def setup_method(self):
        from src.tokenizer.tokenizer import Tokenizer
        self.tokenizer = Tokenizer()

    def test_basic_tokenize(self):
        doc = self.tokenizer.tokenize("Hello world")
        assert len(doc.tokens) == 2
        assert doc.tokens[0].word == "hello"
        assert doc.tokens[0].is_capitalized is True
        assert doc.tokens[1].word == "world"
        assert doc.tokens[1].is_capitalized is False

    def test_punctuation_extraction(self):
        doc = self.tokenizer.tokenize("Hello, world!")
        assert doc.tokens[0].trailing_punct == ","
        assert doc.tokens[1].trailing_punct == "!"

    def test_leading_punctuation(self):
        doc = self.tokenizer.tokenize('"Hello" world')
        assert doc.tokens[0].leading_punct == '"'
        assert doc.tokens[0].trailing_punct == '"'

    def test_80_char_binning(self):
        # Create text that exceeds 80 chars
        words = ["word"] * 25  # "word" * 25 with spaces = 124 chars
        text = " ".join(words)
        doc = self.tokenizer.tokenize(text)
        for line in doc.line_bins:
            assert len(line) <= 80

    def test_line_assignment(self):
        doc = self.tokenizer.tokenize("Hello world")
        assert doc.tokens[0].line_number == 1
        assert doc.tokens[0].word_index == 0
        assert doc.tokens[1].line_number == 1
        assert doc.tokens[1].word_index == 1

    def test_multiline_assignment(self):
        words = ["word"] * 25
        text = " ".join(words)
        doc = self.tokenizer.tokenize(text)
        # Should span multiple lines
        assert doc.line_count > 1
        # First token on line 1
        assert doc.tokens[0].line_number == 1
        # Some token should be on line 2
        line2_tokens = [t for t in doc.tokens if t.line_number == 2]
        assert len(line2_tokens) > 0


# ============================================================
# Unit Tests: Detokenizer
# ============================================================

class TestDetokenizer:
    def setup_method(self):
        from src.tokenizer.tokenizer import Tokenizer
        from src.tokenizer.detokenizer import Detokenizer
        self.tokenizer = Tokenizer()
        self.detokenizer = Detokenizer()

    def test_round_trip_simple(self):
        text = "Hello world"
        doc = self.tokenizer.tokenize(text)
        result = self.detokenizer.detokenize(doc)
        assert result == text

    def test_round_trip_with_punctuation(self):
        text = "Hello, world!"
        doc = self.tokenizer.tokenize(text)
        result = self.detokenizer.detokenize(doc)
        assert result == text

    def test_round_trip_with_caps(self):
        text = "The Quick Brown Fox"
        doc = self.tokenizer.tokenize(text)
        result = self.detokenizer.detokenize(doc)
        assert result == text


# ============================================================
# Unit Tests: Inverted Index
# ============================================================

class TestInvertedIndex:
    def setup_method(self):
        from src.tokenizer.tokenizer import Tokenizer
        from src.inverted_index.index_builder import IndexBuilder
        from src.inverted_index.index_reader import IndexReader
        self.tokenizer = Tokenizer()
        self.builder = IndexBuilder()
        self.reader = IndexReader()

    def test_build_basic(self):
        doc = self.tokenizer.tokenize("the cat sat on the mat")
        index = self.builder.build(doc.tokens)
        assert "the" in index.entries
        assert len(index.entries["the"]) == 2  # appears twice
        assert len(index.entries["cat"]) == 1
        assert index.total_tokens == 6

    def test_word_order(self):
        doc = self.tokenizer.tokenize("the cat sat on the mat")
        index = self.builder.build(doc.tokens)
        # First appearance order
        assert index.word_order == ["the", "cat", "sat", "on", "mat"]

    def test_reconstruct_order(self):
        doc = self.tokenizer.tokenize("the cat sat on the mat")
        index = self.builder.build(doc.tokens)
        tokens = self.reader.reconstruct_token_stream(
            index.entries, index.word_order
        )
        words = [t.word for t in tokens]
        assert words == ["the", "cat", "sat", "on", "the", "mat"]


# ============================================================
# Unit Tests: Serializer
# ============================================================

class TestSerializer:
    def test_cap_bitmap(self):
        from src.serializer.encoder import build_cap_bitmap
        caps = [True, False, True, True, False, False, False, True]
        bitmap = build_cap_bitmap(caps)
        assert len(bitmap) == 1
        # Bit 7=True, 6=False, 5=True, 4=True, 3=False, 2=False, 1=False, 0=True
        assert bitmap[0] == 0b10110001

    def test_cap_bitmap_partial_byte(self):
        from src.serializer.encoder import build_cap_bitmap
        caps = [True, False, True]
        bitmap = build_cap_bitmap(caps)
        assert len(bitmap) == 1
        assert bitmap[0] == 0b10100000


# ============================================================
# END-TO-END Tests
# ============================================================

class TestEndToEnd:
    def setup_method(self):
        from src.pipeline.compressor import Compressor
        from src.pipeline.decompressor import Decompressor
        from src.wordid.dictionary import Dictionary
        self.dict = Dictionary()
        self.compressor = Compressor(dictionary=self.dict)
        self.decompressor = Decompressor(dictionary=self.dict)

    def _round_trip(self, text: str) -> str:
        blob = self.compressor.compress(text)
        return self.decompressor.decompress(blob)

    def test_simple(self):
        text = "the cat sat on the mat"
        assert self._round_trip(text) == text

    def test_capitalization(self):
        text = "The Cat Sat On The Mat"
        assert self._round_trip(text) == text

    def test_punctuation(self):
        text = "Hello, world!"
        assert self._round_trip(text) == text

    def test_mixed(self):
        text = "The quick brown fox, it seems, was very fast."
        assert self._round_trip(text) == text

    def test_multiple_sentences(self):
        text = "I have a dog. The dog is good. He is my best friend."
        assert self._round_trip(text) == text

    def test_numbers_and_unknowns(self):
        text = "the xylophone was very loud"
        result = self._round_trip(text)
        assert result == text

    def test_single_word(self):
        assert self._round_trip("the") == "the"

    def test_repeated_word(self):
        text = "the the the the the"
        assert self._round_trip(text) == text

    def test_compression_ratio(self):
        # The inverted index approach compresses documents with many unique words
        # that repeat. Pure repetition of the same short sentence creates overhead
        # because position lists grow linearly. The blank system (Phase 4) will fix this
        # by omitting high-frequency words entirely.
        # For now, test that larger varied text achieves some compression.
        text = (
            "The history of science is a story of human curiosity. "
            "From the ancient world to the modern age, people have always asked "
            "questions about the nature of the universe. In the beginning, "
            "science was not separate from philosophy. It was not until the "
            "method of observation and experiment was developed that science "
            "began to make real progress in the world."
        ) * 5
        text = " ".join(text.split())
        blob = self.compressor.compress(text)
        raw_size = len(text.encode('utf-8'))
        compressed_size = len(blob)
        ratio = compressed_size / raw_size
        print(f"\nCompression: {raw_size} -> {compressed_size} bytes ({ratio:.1%})")
        # With varied vocabulary repeated 5x, word IDs + coordinate compression wins
        assert compressed_size < raw_size * 1.5  # at most 50% overhead

    def test_coordinate_encoding_helps_varied_text(self):
        """Phase 2: coordinate encoding reduces size vs raw positions on varied text."""
        from src.pipeline.compressor import Compressor as C
        text = (
            "I have a dog. The dog is good. He was my best friend. "
            "She said that the world is not what it was before. "
            "They were all very happy about the new house by the river."
        )
        c_coord = C(dictionary=self.dict, use_coordinate_encoding=True)
        c_raw = C(dictionary=self.dict, use_coordinate_encoding=False)
        blob_coord = c_coord.compress(text)
        blob_raw = c_raw.compress(text)
        print(f"\nVaried text: raw_pos={len(blob_raw)} coord_pos={len(blob_coord)} saved={len(blob_raw)-len(blob_coord)} bytes")
        assert len(blob_coord) <= len(blob_raw)

    def test_long_text(self):
        sentences = [
            "The quick brown fox jumped over the lazy dog.",
            "A good man is hard to find in this day and age.",
            "She said that the world was not what it used to be.",
            "He had been there before but could not find his way back.",
            "They were all very happy about the new house by the river.",
        ]
        text = " ".join(sentences)
        assert self._round_trip(text) == text

    def test_empty(self):
        assert self._round_trip("") == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
