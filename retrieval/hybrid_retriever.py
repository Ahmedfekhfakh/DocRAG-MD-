"""Hybrid retrieval: dense + sparse vectors with RRF fusion."""
import os
from qdrant_client.models import SparseVector, NamedVector, NamedSparseVector, Query, FusionQuery, Fusion
from qdrant_client import models as qmodels
from .qdrant_client import get_qdrant_client
from ingestion.embedders.dense_embedder import embed_query
from ingestion.embedders.sparse_embedder import SparseEmbedder

COLLECTION = os.getenv("COLLECTION_NAME", "medical_rag")
_sparse_embedder: SparseEmbedder | None = None


def _get_sparse_embedder() -> SparseEmbedder:
    global _sparse_embedder
    if _sparse_embedder is None:
        _sparse_embedder = SparseEmbedder()
        _sparse_embedder.fit(["medical clinical"])
    return _sparse_embedder


def rrf_fuse(ranked_lists: list[list[dict]], k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion. score = sum(1 / (rank + k))."""
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}
    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked, start=1):
            doc_id = doc["doc_id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rank + k)
            docs[doc_id] = doc
    return [docs[did] for did in sorted(scores, key=lambda d: -scores[d])]


def hybrid_search(query: str, top_k: int = 10) -> list[dict]:
    """Dense + sparse search, fused with RRF using query_points API."""
    client = get_qdrant_client()

    # Dense search
    dense_vec = embed_query(query)
    dense_results = client.query_points(
        collection_name=COLLECTION,
        query=dense_vec,
        using="dense",
        limit=top_k,
        with_payload=True,
    ).points

    # Sparse search
    sparse_emb = _get_sparse_embedder()
    sv = sparse_emb.encode_query(query)
    sparse_results = []
    if sv["indices"]:
        sparse_results = client.query_points(
            collection_name=COLLECTION,
            query=SparseVector(indices=sv["indices"], values=sv["values"]),
            using="sparse",
            limit=top_k,
            with_payload=True,
        ).points

    def to_dict(hit) -> dict:
        return {
            "doc_id": hit.payload.get("doc_id", str(hit.id)),
            "title": hit.payload.get("title", ""),
            "content": hit.payload.get("content", ""),
            "source": hit.payload.get("source", "statpearls"),
            "score": hit.score,
        }

    dense_list = [to_dict(h) for h in dense_results]
    sparse_list = [to_dict(h) for h in sparse_results]
    return rrf_fuse([dense_list, sparse_list])[:top_k]
