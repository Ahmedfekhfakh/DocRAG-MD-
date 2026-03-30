"""BM25 sparse embedder — produces SparseVector-compatible dicts."""
from rank_bm25 import BM25Okapi
import re


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


class SparseEmbedder:
    """Fit BM25 on a corpus, then encode individual documents."""

    def __init__(self):
        self._vocab: dict[str, int] = {}
        self._idf: dict[int, float] = {}

    def fit(self, texts: list[str]) -> "SparseEmbedder":
        tokenized = [tokenize(t) for t in texts]
        bm25 = BM25Okapi(tokenized)
        # Build vocab from all terms
        for tokens in tokenized:
            for tok in tokens:
                if tok not in self._vocab:
                    self._vocab[tok] = len(self._vocab)
        # Store IDF per token id
        for term, idx in self._vocab.items():
            self._idf[idx] = float(bm25.idf.get(term, 0.0))
        return self

    def encode(self, text: str) -> dict:
        """Return {'indices': [...], 'values': [...]} for Qdrant SparseVector."""
        tokens = tokenize(text)
        tf: dict[int, float] = {}
        for tok in tokens:
            if tok in self._vocab:
                idx = self._vocab[tok]
                tf[idx] = tf.get(idx, 0.0) + 1.0
        if not tf:
            return {"indices": [], "values": []}
        indices = list(tf.keys())
        values = [tf[i] * self._idf.get(i, 1.0) for i in indices]
        return {"indices": indices, "values": values}

    def encode_query(self, text: str) -> dict:
        return self.encode(text)
