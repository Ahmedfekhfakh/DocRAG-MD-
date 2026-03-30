"""Shared Qdrant client singleton."""
import os
from qdrant_client import QdrantClient as _QdrantClient

_client: _QdrantClient | None = None


def get_qdrant_client() -> _QdrantClient:
    global _client
    if _client is None:
        _client = _QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
        )
    return _client
