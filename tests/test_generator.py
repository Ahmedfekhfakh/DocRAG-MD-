"""Tests for generation layer."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from generation.llm_router import get_llm
from generation.generator import build_chain


def test_llm_router_returns_gemini(monkeypatch):
    from langchain_google_genai import ChatGoogleGenerativeAI
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert isinstance(get_llm("gemini"), ChatGoogleGenerativeAI)


def test_llm_router_unknown_raises(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with pytest.raises(ValueError, match="Unknown model"):
        get_llm("nonexistent")


def test_build_chain_returns_runnable(monkeypatch):
    from langchain_core.runnables import Runnable
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    chain = build_chain("gemini", use_cot=False)
    assert hasattr(chain, "invoke") or hasattr(chain, "ainvoke")


def test_build_chain_cot_vs_standard(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    chain_std = build_chain("gemini", use_cot=False)
    chain_cot = build_chain("gemini", use_cot=True)
    assert chain_std is not None
    assert chain_cot is not None


@pytest.mark.asyncio
async def test_generate_answer_calls_chain():
    from generation.generator import generate_answer
    mock_chain = AsyncMock(return_value="Mocked answer [1].")
    with patch("generation.generator.build_chain", return_value=MagicMock(ainvoke=mock_chain)):
        result = await generate_answer("What is diabetes?", "[1] Content here", "gemini")
    assert result == "Mocked answer [1]."
    mock_chain.assert_called_once()


def test_clinical_qa_prompt_has_required_vars():
    from pathlib import Path
    prompt_text = (Path("generation/prompts/clinical_qa.txt")).read_text()
    assert "{context}" in prompt_text
    assert "{question}" in prompt_text


def test_cot_prompt_has_required_vars():
    from pathlib import Path
    prompt_text = (Path("generation/prompts/cot_medical.txt")).read_text()
    assert "{context}" in prompt_text
    assert "{question}" in prompt_text
