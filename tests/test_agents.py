"""Tests for LangGraph agents."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_rag_agent_pipeline():
    """Test the full RAG agent pipeline with mocked retrieval and LLM."""
    mock_docs = [
        {"doc_id": "1", "title": "Diabetes", "content": "Diabetes is a metabolic disease.", "source": "statpearls", "score": 0.9},
        {"doc_id": "2", "title": "Insulin", "content": "Insulin is a hormone.", "source": "statpearls", "score": 0.8},
    ]
    with (
        patch("agents.rag_agent.generate_hypothetical_doc", new_callable=AsyncMock, return_value="A hypothetical passage about diabetes"),
        patch("agents.rag_agent.hybrid_search", return_value=mock_docs),
        patch("agents.rag_agent.rerank", return_value=mock_docs),
        patch("agents.rag_agent.crag_gate", return_value=(mock_docs, True)),
        patch("agents.rag_agent.generate_answer", new_callable=AsyncMock, return_value="Diabetes is a metabolic disease [1]."),
    ):
        from agents.rag_agent import run_rag
        result = await run_rag("What is diabetes?", model_name="gemini")

    assert "answer" in result
    assert "sources" in result
    assert len(result["answer"]) > 0


@pytest.mark.asyncio
async def test_rag_agent_low_confidence():
    """Test that low-confidence CRAG gate returns refusal message."""
    mock_docs = [{"doc_id": "1", "title": "T", "content": "C", "source": "statpearls", "score": 0.1}]
    with (
        patch("agents.rag_agent.generate_hypothetical_doc", new_callable=AsyncMock, return_value="hypo"),
        patch("agents.rag_agent.hybrid_search", return_value=mock_docs),
        patch("agents.rag_agent.rerank", return_value=mock_docs),
        patch("agents.rag_agent.crag_gate", return_value=(mock_docs, False)),
    ):
        from agents.rag_agent import run_rag
        result = await run_rag("nonsense question xyz", model_name="gemini")

    assert "not find" in result["answer"].lower() or "not" in result["answer"].lower()
