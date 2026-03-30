"""GET /health"""
from fastapi import APIRouter
from api.schemas import HealthResponse
from retrieval.qdrant_client import get_qdrant_client

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    try:
        client = get_qdrant_client()
        client.get_collections()
        qdrant_status = "ok"
    except Exception as e:
        qdrant_status = f"error: {e}"
    return HealthResponse(status="ok", qdrant=qdrant_status)
