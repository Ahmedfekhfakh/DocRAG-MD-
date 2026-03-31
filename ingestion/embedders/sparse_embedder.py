"""BM25 sparse embedder — produces SparseVector-compatible dicts."""
from __future__ import annotations

import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


class SparseEmbedder:
    """Fit BM25 on a corpus, then encode individual documents."""

    def __init__(self):
        self._vocab: dict[str, int] = {}
        self._idf: dict[int, float] = {}

    def fit(self, texts: list[str]) -> "SparseEmbedder":
        tokenized = [tokenize(text) for text in texts]
        bm25 = BM25Okapi(tokenized)
        for tokens in tokenized:
            for token in tokens:
                if token not in self._vocab:
                    self._vocab[token] = len(self._vocab)
        for term, idx in self._vocab.items():
            self._idf[idx] = float(bm25.idf.get(term, 0.0))
        return self

    def to_state(self) -> dict:
        return {
            "vocab": self._vocab,
            "idf": {str(idx): value for idx, value in self._idf.items()},
        }

    @classmethod
    def from_state(cls, state: dict) -> "SparseEmbedder":
        inst = cls()
        inst._vocab = {str(term): int(idx) for term, idx in state.get("vocab", {}).items()}
        inst._idf = {int(idx): float(value) for idx, value in state.get("idf", {}).items()}
        return inst

    def dump(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_state()), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> "SparseEmbedder":
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_state(state)

    def encode(self, text: str) -> dict:
        """Return {'indices': [...], 'values': [...]} for Qdrant SparseVector."""
        tf: dict[int, float] = {}
        for token in tokenize(text):
            if token in self._vocab:
                idx = self._vocab[token]
                tf[idx] = tf.get(idx, 0.0) + 1.0
        if not tf:
            return {"indices": [], "values": []}
        indices = list(tf.keys())
        values = [tf[idx] * self._idf.get(idx, 1.0) for idx in indices]
        return {"indices": indices, "values": values}

    def encode_query(self, text: str) -> dict:
        return self.encode(text)
