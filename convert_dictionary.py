"""Convert a template dictionary export to rank-based JSON.

The input is the exported list of template entries. The output is a
``{word: rank}`` mapping where rank 1 is the highest compression-ratio entry.
Paths are explicit CLI arguments so the script is portable across operators and
CI checkouts.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = Path(__file__).resolve().parent / "dictionary_cache.json"


def convert_dictionary(input_path: Path, output_path: Path = DEFAULT_OUTPUT) -> dict[str, int]:
    with input_path.open("r", encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)

    print(f"Total entries: {len(data)}")

    cats = Counter(entry.get("template_category", "unknown") for entry in data)
    print(f"Categories: {dict(cats)}")

    data_sorted = sorted(data, key=lambda x: x.get("compression_ratio", 0), reverse=True)

    print("\nTop 20 (highest frequency):")
    for entry in data_sorted[:20]:
        word = entry["template_text"]
        ratio = entry["compression_ratio"]
        category = entry["template_category"]
        print(f"  {word:15s}  ratio={ratio}  cat={category}")

    word_to_rank: dict[str, int] = {}
    seen: set[str] = set()
    for entry in data_sorted:
        word = entry["template_text"].lower().strip()
        if word and word not in seen:
            word_to_rank[word] = len(word_to_rank) + 1
            seen.add(word)

    print(f"\nUnique words: {len(word_to_rank)}")
    for rank in range(1, 4):
        print(f"Rank {rank}: {[word for word, value in word_to_rank.items() if value == rank]}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_text = json.dumps(word_to_rank, ensure_ascii=False)
    output_path.write_text(output_text, encoding="utf-8")

    print(f"\nSaved to {output_path}")
    print(f"File size: {len(output_text)} bytes")
    return word_to_rank


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to the template dictionary export JSON.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output rank dictionary path. Default: {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    convert_dictionary(args.input, args.output)


if __name__ == "__main__":
    main()
