"""Ingestion pipeline: load → embed → upsert to Qdrant."""
import os
import uuid
import logging
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    SparseVectorParams,
    SparseIndexParams,
    PointStruct,
    SparseVector,
)
from .loaders.statpearls_loader import load_chunks
from .embedders.dense_embedder import embed_texts
from .embedders.sparse_embedder import SparseEmbedder

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

COLLECTION = os.getenv("COLLECTION_NAME", "medical_rag")
DENSE_DIM = int(os.getenv("DENSE_DIM", "768"))
BATCH_SIZE = 64
DATA_PATH = Path(os.getenv("DATA_PATH", "data/statpearls_chunks.jsonl"))


def get_client() -> QdrantClient:
    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )


def ensure_collection(client: QdrantClient) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={"dense": VectorParams(size=DENSE_DIM, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams(index=SparseIndexParams())},
        )
        log.info("Created collection %s", COLLECTION)
    else:
        log.info("Collection %s already exists", COLLECTION)


def run(limit: int | None = None) -> int:
    client = get_client()
    ensure_collection(client)

    # Load all chunks first (needed for BM25 fitting)
    log.info("Loading chunks from %s ...", DATA_PATH)
    chunks = list(load_chunks(DATA_PATH, limit=limit))
    log.info("Loaded %d chunks", len(chunks))

    # Fit sparse embedder on corpus
    log.info("Fitting BM25 sparse embedder ...")
    sparse_embedder = SparseEmbedder()
    sparse_embedder.fit([c.get("contents", c.get("content", "")) for c in chunks])

    total = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts_dense = [c.get("content", "") for c in batch]
        texts_sparse = [c.get("contents", c.get("content", "")) for c in batch]

        dense_vecs = embed_texts(texts_dense)
        sparse_vecs = [sparse_embedder.encode(t) for t in texts_sparse]

        points = []
        for chunk, dv, sv in zip(batch, dense_vecs, sparse_vecs):
            doc_id = chunk.get("id", str(uuid.uuid4()))
            points.append(
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id)),
                    vector={
                        "dense": dv,
                        "sparse": SparseVector(
                            indices=sv["indices"], values=sv["values"]
                        ),
                    },
                    payload={
                        "doc_id": doc_id,
                        "title": chunk.get("title", ""),
                        "content": chunk.get("content", ""),
                        "source": "statpearls",
                    },
                )
            )

        client.upsert(collection_name=COLLECTION, points=points)
        total += len(points)
        log.info("Upserted %d / %d", total, len(chunks))

    log.info("Ingestion complete. Total: %d points", total)
    return total


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run(limit=limit)
