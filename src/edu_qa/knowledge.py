from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from .models import Evidence

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for",
    "from", "how", "i", "in", "is", "it", "of", "on", "or", "that", "the",
    "this", "to", "what", "when", "where", "which", "why", "with",
}


def tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOP]


class KnowledgeBase:
    """Small transparent BM25-like retriever suitable for offline demonstrations."""

    def __init__(self, documents: list[dict[str, str]]) -> None:
        self.documents = documents
        self._tokens = [tokens(f"{d['title']} {d['content']}") for d in documents]
        self._df = Counter(term for row in map(set, self._tokens) for term in row)

    @classmethod
    def from_json(cls, path: str | Path) -> "KnowledgeBase":
        with Path(path).open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list) or not payload:
            raise ValueError("Knowledge file must contain a non-empty JSON list")
        for item in payload:
            if not isinstance(item, dict) or not {"title", "content"} <= item.keys():
                raise ValueError("Every knowledge item requires title and content")
        return cls(payload)

    def search(self, query: str, limit: int = 3) -> list[Evidence]:
        query_terms = tokens(query)
        if not query_terms:
            return []
        scored: list[tuple[float, int]] = []
        count = len(self.documents)
        for index, doc_terms in enumerate(self._tokens):
            frequencies = Counter(doc_terms)
            score = 0.0
            for term in query_terms:
                if term not in frequencies:
                    continue
                idf = math.log(1 + (count - self._df[term] + 0.5) / (self._df[term] + 0.5))
                score += idf * (1 + math.log(frequencies[term]))
                if term in tokens(self.documents[index]["title"]):
                    score += 1.25
            if score:
                scored.append((score, index))
        scored.sort(reverse=True)
        return [
            Evidence(
                title=self.documents[i]["title"],
                excerpt=self.documents[i]["content"],
                source=self.documents[i].get("source", "Built-in learning library"),
                score=round(score, 3),
            )
            for score, i in scored[: max(1, limit)]
        ]
