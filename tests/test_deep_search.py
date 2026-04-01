"""Tests for Deep Search workflow."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_run_deep_search_pipeline():
    mock_docs = [
        {
            "doc_id": "1",
            "title": "Diabetes",
            "content": "Diabetes is a chronic metabolic disease.",
            "source": "statpearls",
            "score": 0.9,
        },
        {
            "doc_id": "2",
            "title": "Insulin",
            "content": "Insulin regulates glucose metabolism.",
            "source": "statpearls",
            "score": 0.8,
        },
    ]

    with (
        patch("agents.deep_search_agent.decompose_question", new_callable=AsyncMock, return_value=["What causes diabetes?"]),
        patch("agents.deep_search_agent.expand_query", new_callable=AsyncMock, return_value=["What is diabetes?"]),
        patch("agents.deep_search_agent.generate_hypothetical_doc", new_callable=AsyncMock, return_value="A short passage about diabetes."),
        patch("agents.deep_search_agent.hybrid_search", return_value=mock_docs),
        patch("agents.deep_search_agent.drill_down_sources", return_value=[]),
        patch("agents.deep_search_agent.rerank", return_value=mock_docs),
        patch("agents.deep_search_agent.crag_gate", return_value=(mock_docs, True)),
        patch("agents.deep_search_agent.generate_answer", new_callable=AsyncMock, return_value="Diabetes is a chronic metabolic disease [1]."),
    ):
        from agents.deep_search_agent import run_deep_search

        result = await run_deep_search("What is diabetes?", model_name="gemini")

    assert result["search_mode"] == "deep"
    assert "answer" in result
    assert len(result["sources"]) == 2
