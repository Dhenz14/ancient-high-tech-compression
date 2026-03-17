"""Convert the Replit dictionary export to our rank-based format."""
import json
import sys

INPUT = "/mnt/c/Users/theyc/OneDrive/Desktop/compression_dictionary.json"
OUTPUT = "/mnt/c/Users/theyc/compressor/ancient-high-tech-compression/dictionary_cache.json"

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total entries: {len(data)}")

# Check categories
cats = {}
for entry in data:
    c = entry.get("template_category", "unknown")
    cats[c] = cats.get(c, 0) + 1
print(f"Categories: {cats}")

# Sort by compression_ratio descending (higher = more frequent)
data_sorted = sorted(data, key=lambda x: x.get("compression_ratio", 0), reverse=True)

print(f"\nTop 20 (highest frequency):")
for e in data_sorted[:20]:
    w = e["template_text"]
    r = e["compression_ratio"]
    c = e["template_category"]
    print(f"  {w:15s}  ratio={r}  cat={c}")

# Build word -> rank mapping (rank 1 = most frequent)
word_to_rank = {}
rank = 1
seen = set()
for entry in data_sorted:
    w = entry["template_text"].lower().strip()
    if w and w not in seen:
        word_to_rank[w] = rank
        seen.add(w)
        rank += 1

print(f"\nUnique words: {len(word_to_rank)}")
print(f"Rank 1: {[w for w,r in word_to_rank.items() if r==1]}")
print(f"Rank 2: {[w for w,r in word_to_rank.items() if r==2]}")
print(f"Rank 3: {[w for w,r in word_to_rank.items() if r==3]}")

# Save
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(word_to_rank, f)

print(f"\nSaved to {OUTPUT}")
print(f"File size: {len(json.dumps(word_to_rank))} bytes")
