"""
Dictionary: word <-> frequency rank mapping.

For Phase 1, uses a built-in top-10K frequency list. The full 249K dictionary
will be loaded from PostgreSQL or a local cache file in Phase 5.

Ranks are 1-based: rank 1 = most frequent word ("the").
"""

import json
import os
from pathlib import Path
from typing import Optional, List


# Top 1000 English words by frequency (covers ~85% of typical text).
# This is the bootstrap dictionary for Phase 1. The full 249K dictionary
# from the PostgreSQL database will replace this in Phase 5.
_TOP_WORDS = [
    "the", "of", "and", "to", "a", "in", "is", "it", "you", "that",
    "he", "was", "for", "on", "are", "with", "as", "i", "his", "they",
    "be", "at", "one", "have", "this", "from", "or", "had", "by", "but",
    "not", "what", "all", "were", "we", "when", "your", "can", "said", "there",
    "each", "which", "she", "do", "how", "their", "if", "will", "up", "other",
    "about", "out", "many", "then", "them", "these", "so", "some", "her", "would",
    "make", "like", "him", "into", "time", "has", "look", "two", "more", "go",
    "see", "no", "way", "could", "my", "than", "first", "been", "call", "who",
    "its", "now", "find", "long", "down", "day", "did", "get", "come", "made",
    "after", "back", "only", "me", "our", "under", "may", "just", "also", "use",
    # 101-200
    "very", "well", "know", "should", "still", "any", "much", "through", "over", "such",
    "new", "take", "good", "great", "before", "same", "right", "think", "too", "old",
    "year", "off", "because", "here", "most", "people", "state", "say", "even", "between",
    "own", "tell", "never", "last", "must", "us", "high", "world", "life", "man",
    "hand", "part", "place", "where", "work", "home", "small", "give", "while", "end",
    "show", "every", "head", "large", "turn", "need", "might", "help", "line", "house",
    "point", "number", "change", "try", "move", "few", "live", "set", "thing", "both",
    "keep", "put", "does", "another", "begin", "why", "still", "around", "again", "name",
    "water", "little", "run", "own", "read", "side", "school", "city", "big", "seem",
    "left", "far", "want", "let", "close", "nothing", "night", "real", "open", "enough",
    # 201-300
    "always", "problem", "next", "start", "hear", "kind", "stand", "story", "young", "until",
    "important", "country", "family", "leave", "play", "room", "eye", "woman", "group", "ask",
    "question", "body", "book", "power", "money", "different", "word", "example", "food", "face",
    "four", "children", "without", "second", "government", "boy", "yet", "system", "program", "against",
    "during", "often", "already", "possible", "best", "door", "three", "sure", "car", "among",
    "since", "later", "though", "plan", "area", "fact", "air", "child", "along", "away",
    "mother", "father", "girl", "idea", "age", "class", "case", "land", "write", "field",
    "study", "company", "interest", "war", "able", "service", "early", "hard", "million", "form",
    "light", "look", "together", "ever", "white", "black", "level", "order", "today", "morning",
    "reason", "become", "general", "almost", "american", "member", "local", "above", "report", "public",
    # 301-400
    "center", "table", "street", "meet", "feel", "result", "believe", "office", "provide", "hold",
    "market", "once", "bring", "actually", "less", "social", "include", "perhaps", "half", "action",
    "talk", "national", "experience", "love", "human", "building", "happen", "moment", "political", "strong",
    "minutes", "mind", "certain", "lot", "behind", "full", "clear", "month", "week", "bit",
    "special", "health", "force", "past", "several", "town", "anything", "true", "space", "process",
    "sense", "information", "appear", "figure", "inside", "police", "free", "mean", "community", "nature",
    "type", "cover", "available", "something", "personal", "continue", "care", "low", "support", "ground",
    "common", "simple", "major", "court", "economic", "hour", "break", "rather", "rate", "themselves",
    "whole", "miss", "paper", "view", "law", "industry", "stop", "base", "record", "deal",
    "position", "effect", "recent", "evidence", "whether", "expect", "period", "require", "within", "control",
    # 401-500
    "subject", "history", "development", "section", "sometimes", "stage", "toward", "technology", "usually", "language",
    "president", "size", "according", "director", "produce", "music", "cost", "film", "final", "five",
    "attention", "society", "note", "role", "model", "game", "present", "investment", "material", "decision",
    "research", "range", "sound", "north", "image", "news", "south", "allow", "death", "response",
    "situation", "international", "resource", "million", "rest", "practice", "student", "scene", "west", "involve",
    "individual", "quality", "create", "apply", "likely", "tax", "condition", "per", "drive", "private",
    "management", "rule", "enter", "accept", "performance", "analysis", "draw", "consider", "education", "receive",
    "identify", "article", "similar", "pass", "offer", "oil", "test", "add", "concern", "share",
    "issue", "remain", "describe", "serve", "easy", "list", "themselves", "everything", "opportunity", "challenge",
    "party", "develop", "choose", "wrong", "cause", "data", "activity", "follow", "approach", "lead",
]


class Dictionary:
    """Word <-> rank bidirectional mapping."""

    # Default cache file location (relative to project root)
    _DEFAULT_CACHE = os.path.join(os.path.dirname(__file__), '..', '..', 'dictionary_cache.json')

    def __init__(self, cache_path: Optional[str] = None):
        """
        Initialize dictionary.

        Args:
            cache_path: Path to a JSON dictionary cache file. If None, looks for
                       dictionary_cache.json in project root, then falls back
                       to built-in top-500 list.
        """
        self._word_to_rank: dict = {}
        self._rank_to_word: dict = {}

        if cache_path and os.path.exists(cache_path):
            self._load_from_cache(cache_path)
        elif os.path.exists(self._DEFAULT_CACHE):
            self._load_from_cache(self._DEFAULT_CACHE)
        else:
            self._load_builtin()

    def _load_builtin(self):
        """Load the built-in frequency list."""
        seen = set()
        rank = 1
        for word in _TOP_WORDS:
            w = word.lower().strip()
            if w and w not in seen:
                self._word_to_rank[w] = rank
                self._rank_to_word[rank] = w
                seen.add(w)
                rank += 1

    def _load_from_cache(self, path: str):
        """Load dictionary from a JSON cache file: {"word": rank, ...}"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for word, rank in data.items():
            w = word.lower().strip()
            r = int(rank)
            self._word_to_rank[w] = r
            self._rank_to_word[r] = w

    def word_to_rank(self, word: str) -> Optional[int]:
        """Return frequency rank (1-based) or None if unknown."""
        return self._word_to_rank.get(word.lower().strip())

    def rank_to_word(self, rank: int) -> Optional[str]:
        """Return word for given rank, or None."""
        return self._rank_to_word.get(rank)

    def checksum(self, words: List[str]) -> int:
        """Sum of ranks for all words. Unknown words contribute 0."""
        total = 0
        for w in words:
            rank = self.word_to_rank(w)
            if rank is not None:
                total += rank
        return total

    def has_word(self, word: str) -> bool:
        return word.lower().strip() in self._word_to_rank

    @property
    def size(self) -> int:
        return len(self._word_to_rank)

    def export_cache(self, path: str):
        """Export dictionary to JSON cache file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._word_to_rank, f, ensure_ascii=False)
