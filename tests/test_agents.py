"""Tests for LangGraph agents."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_rag_agent_standard_pipeline():
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
        result = await run_rag("What is diabetes?", model_name="gemini", search_mode="standard")

    assert "answer" in result
    assert "sources" in result
    assert result["search_mode"] == "standard"
    assert len(result["answer"]) > 0


@pytest.mark.asyncio
async def test_rag_agent_routes_to_deep_search():
    with (
        patch("agents.rag_agent.run_standard_rag", new_callable=AsyncMock) as standard_mock,
        patch(
            "agents.rag_agent.run_deep_search",
            new_callable=AsyncMock,
            return_value={"answer": "deep", "sources": [], "is_confident": True, "search_mode": "deep"},
        ) as deep_mock,
    ):
        from agents.rag_agent import run_rag

        result = await run_rag("complex question", model_name="gemini", search_mode="deep")

    standard_mock.assert_not_awaited()
    deep_mock.assert_awaited_once()
    assert result["search_mode"] == "deep"
