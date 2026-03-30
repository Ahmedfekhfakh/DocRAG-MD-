"""Cross-encoder reranker using ms-marco-MiniLM-L-6-v2."""
from sentence_transformers import CrossEncoder

_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _model


def rerank(query: str, docs: list[dict], top_k: int = 5) -> list[dict]:
    """Rerank docs by cross-encoder score, return top_k with scores attached."""
    if not docs:
        return []
    model = _get_model()
    pairs = [(query, doc["content"]) for doc in docs]
    scores = model.predict(pairs)
    for doc, score in zip(docs, scores):
        doc["rerank_score"] = float(score)
    return sorted(docs, key=lambda d: -d["rerank_score"])[:top_k]
