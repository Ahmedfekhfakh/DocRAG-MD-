"""Cross-encoder reranker using ms-marco-MiniLM-L-6-v2."""
import asyncio
from sentence_transformers import CrossEncoder

_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _model


def preload_model():
    """Eagerly load the cross-encoder model (call at startup)."""
    _get_model()


def _rerank_sync(query: str, docs: list[dict], top_k: int) -> list[dict]:
    """Synchronous rerank — runs in thread pool."""
    model = _get_model()
    pairs = [(query, doc["content"]) for doc in docs]
    scores = model.predict(pairs)
    for doc, score in zip(docs, scores):
        doc["rerank_score"] = float(score)
    return sorted(docs, key=lambda d: -d["rerank_score"])[:top_k]


def rerank(query: str, docs: list[dict], top_k: int = 5) -> list[dict]:
    """Rerank docs by cross-encoder score (sync, for backward compat)."""
    if not docs:
        return []
    return _rerank_sync(query, docs, top_k)


async def rerank_async(query: str, docs: list[dict], top_k: int = 5) -> list[dict]:
    """Rerank without blocking the async event loop."""
    if not docs:
        return []
    return await asyncio.to_thread(_rerank_sync, query, docs, top_k)
