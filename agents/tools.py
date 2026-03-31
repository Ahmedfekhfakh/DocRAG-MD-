"""LangChain @tool wrappers for retrieval, rerank, and generation."""
import asyncio
from langchain_core.tools import tool
from retrieval.hybrid_retriever import hybrid_search
from retrieval.reranker import rerank
from retrieval.crag import crag_gate
from retrieval.context_assembler import assemble_context
from generation.generator import generate_answer


@tool
def search_qdrant(query: str, top_k: int = 10) -> list[dict]:
    """Search the medical knowledge base using hybrid dense+sparse retrieval."""
    return hybrid_search(query, top_k=top_k)


@tool
def rerank_results(query: str, docs: list[dict], top_k: int = 5) -> dict:
    """Rerank retrieved documents using cross-encoder and apply CRAG gate."""
    reranked = rerank(query, docs, top_k=top_k)
    filtered, is_confident = crag_gate(reranked)
    return {"docs": filtered, "is_confident": is_confident}


@tool
def generate_answer_tool(question: str, context: str, model_name: str = "gemini") -> str:
    """Generate a cited answer from context using the specified LLM."""
    return asyncio.get_event_loop().run_until_complete(
        generate_answer(question, context, model_name)
    )
