import json

from convert_dictionary import convert_dictionary


def test_convert_dictionary_uses_cli_paths(tmp_path):
    source = tmp_path / "export.json"
    output = tmp_path / "dictionary_cache.json"
    source.write_text(
        json.dumps(
            [
                {"template_text": "Beta", "compression_ratio": 5, "template_category": "word"},
                {"template_text": "alpha", "compression_ratio": 10, "template_category": "word"},
                {"template_text": "ALPHA", "compression_ratio": 1, "template_category": "duplicate"},
                {"template_text": "  gamma  ", "compression_ratio": 4, "template_category": "word"},
            ]
        ),
        encoding="utf-8",
    )

    result = convert_dictionary(source, output)

    assert result == {"alpha": 1, "beta": 2, "gamma": 3}
    assert json.loads(output.read_text(encoding="utf-8")) == result
