"""Hybrid retrieval: Qdrant-first with local lexical fallback."""
from __future__ import annotations

import os
from pathlib import Path

from qdrant_client.models import SparseVector
from rank_bm25 import BM25Okapi

from ingestion.embedders.dense_embedder import embed_query
from ingestion.embedders.sparse_embedder import SparseEmbedder, tokenize
from ingestion.loaders.statpearls_loader import load_chunks
from retrieval.qdrant_client import get_qdrant_client

COLLECTION = os.getenv("COLLECTION_NAME", "medical_rag")
DATA_PATH = Path(os.getenv("DATA_PATH", "data/statpearls_chunks.jsonl"))
SPARSE_STATE_PATH = Path(os.getenv("SPARSE_STATE_PATH", "data/sparse_embedder_state.json"))

_sparse_embedder: SparseEmbedder | None = None
_local_docs: list[dict] | None = None
_local_bm25: BM25Okapi | None = None


def _load_local_index() -> tuple[list[dict], BM25Okapi | None]:
    global _local_docs, _local_bm25
    if _local_docs is None:
        if not DATA_PATH.exists():
            _local_docs = []
            _local_bm25 = None
            return _local_docs, _local_bm25
        _local_docs = list(load_chunks(DATA_PATH))
        tokenized = [tokenize(doc.get("contents", doc.get("content", ""))) for doc in _local_docs]
        _local_bm25 = BM25Okapi(tokenized) if tokenized else None
    return _local_docs, _local_bm25


def _get_sparse_embedder() -> SparseEmbedder:
    global _sparse_embedder
    if _sparse_embedder is None:
        if SPARSE_STATE_PATH.exists():
            _sparse_embedder = SparseEmbedder.load(SPARSE_STATE_PATH)
        else:
            docs, _ = _load_local_index()
            texts = [doc.get("contents", doc.get("content", "")) for doc in docs]
            _sparse_embedder = SparseEmbedder().fit(texts or ["medical clinical"])
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
    return [docs[doc_id] for doc_id in sorted(scores, key=lambda item: -scores[item])]


def _to_hit_dict(hit) -> dict:
    payload = hit.payload or {}
    return {
        "doc_id": payload.get("doc_id", str(hit.id)),
        "title": payload.get("title", ""),
        "content": payload.get("content", ""),
        "source": payload.get("source", "statpearls"),
        "score": float(getattr(hit, "score", 0.0) or 0.0),
    }


def _local_result(doc: dict, score: float) -> dict:
    return {
        "doc_id": doc.get("id", doc.get("doc_id", "")),
        "title": doc.get("title", ""),
        "content": doc.get("content", doc.get("contents", "")),
        "source": doc.get("source", "statpearls"),
        "score": float(score),
    }


def _local_lexical_search(query: str, top_k: int = 10) -> list[dict]:
    docs, bm25 = _load_local_index()
    if not docs or bm25 is None:
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)
    ranked = sorted(enumerate(scores), key=lambda item: float(item[1]), reverse=True)
    results: list[dict] = []
    for idx, score in ranked[:top_k]:
        if score <= 0 and results:
            continue
        results.append(_local_result(docs[idx], float(score)))
    return results


def _qdrant_hybrid_search(query: str, top_k: int) -> list[dict]:
    client = get_qdrant_client()
    collection = client.get_collection(COLLECTION)
    if (collection.points_count or 0) <= 0:
        return []

    dense_results = client.query_points(
        collection_name=COLLECTION,
        query=embed_query(query),
        using="dense",
        limit=top_k,
        with_payload=True,
    ).points

    sparse_results = []
    sparse_vector = _get_sparse_embedder().encode_query(query)
    if sparse_vector["indices"]:
        sparse_results = client.query_points(
            collection_name=COLLECTION,
            query=SparseVector(
                indices=sparse_vector["indices"],
                values=sparse_vector["values"],
            ),
            using="sparse",
            limit=top_k,
            with_payload=True,
        ).points

    fused = rrf_fuse(
        [
            [_to_hit_dict(hit) for hit in dense_results],
            [_to_hit_dict(hit) for hit in sparse_results],
        ]
    )
    return fused[:top_k]


def hybrid_search(query: str, top_k: int = 10) -> list[dict]:
    """Dense+sparse Qdrant search, with local lexical fallback if needed."""
    try:
        results = _qdrant_hybrid_search(query, top_k=top_k)
        if results:
            return results
    except Exception:
        pass
    return _local_lexical_search(query, top_k=top_k)
