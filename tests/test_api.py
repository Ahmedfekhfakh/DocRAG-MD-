"""Tests for FastAPI endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_endpoint():
    with patch("api.routers.health.get_qdrant_client") as mock_client:
        mock_client.return_value.get_collections.return_value = MagicMock()
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "qdrant" in data


@pytest.mark.asyncio
async def test_query_endpoint():
    mock_result = {
        "answer": "Diabetes is a metabolic disease [1].",
        "sources": [{"doc_id": "1", "title": "Diabetes", "content": "test", "source": "statpearls", "rerank_score": 5.0}],
        "search_mode": "standard",
        "is_confident": True,
        "intent": "GENERAL",
    }
    with patch("api.routers.query.run_orchestrator", new_callable=AsyncMock, return_value=mock_result):
        resp = client.post(
            "/query",
            json={"question": "What is diabetes?", "model": "gemini", "mode": "rag", "search_mode": "standard"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["model"] == "gemini"
    assert data["intent"] == "GENERAL"


def test_query_validation():
    resp = client.post("/query", json={"question": "", "model": "gemini"})
    assert resp.status_code == 422  # Pydantic min_length=1


def test_ingest_endpoint():
    with patch("api.routers.ingest.run_pipeline") as mock_run:
        resp = client.post("/ingest", json={"limit": 100})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"
