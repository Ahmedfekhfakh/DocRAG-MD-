"""RAG entrypoint — routes between standard and Deep Search modes."""
from __future__ import annotations

import inspect
import operator
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from generation.generator import generate_answer
from retrieval.context_assembler import assemble_context
from retrieval.crag import crag_gate
from retrieval.hybrid_retriever import hybrid_search
from retrieval.query_transform.hyde import generate_hypothetical_doc
from retrieval.reranker import rerank

from .deep_search_agent import run_deep_search


class RAGState(TypedDict):
    question: str
    model_name: str
    role: str
    search_mode: str
    queries: list[str]
    raw_docs: list[dict]
    reranked_docs: list[dict]
    is_confident: bool
    context: str
    answer: str
    sources: list[dict]
    messages: Annotated[list, operator.add]
    progress_callback: object | None


async def _emit_progress(state: RAGState, step: str, status: str, **payload) -> None:
    callback = state.get("progress_callback")
    if not callback:
        return
    event = {"type": "trace", "step": step, "status": status, **payload}
    result = callback(event)
    if inspect.isawaitable(result):
        await result


async def _stream_answer_chunks(answer: str, progress_callback) -> None:
    if not progress_callback or not answer:
        return
    chunk_size = 140
    for idx in range(0, len(answer), chunk_size):
        result = progress_callback({"type": "delta", "text": answer[idx : idx + chunk_size]})
        if inspect.isawaitable(result):
            await result


async def query_transform_node(state: RAGState, config: RunnableConfig) -> dict:
    """Generate HyDE hypothetical doc and use as search query."""
    await _emit_progress(state, "planning", "running")
    question = state["question"]
    model_name = state.get("model_name", "gemini")
    try:
        hypo = await generate_hypothetical_doc(question, model_name, config=config)
        queries = [question, hypo]
    except Exception:
        queries = [question]
    await _emit_progress(state, "planning", "done", queries=queries[:3])
    return {"queries": queries}


async def search_node(state: RAGState) -> dict:
    """Hybrid search for all queries, merge results."""
    await _emit_progress(state, "retrieval", "running", query_count=len(state.get("queries", [])))
    all_docs: list[dict] = []
    seen_ids: set[str] = set()
    for q in state.get("queries", [state["question"]]):
        docs = hybrid_search(q, top_k=10)
        for d in docs:
            did = d.get("doc_id", d.get("content", "")[:50])
            if did not in seen_ids:
                seen_ids.add(did)
                all_docs.append(d)
    await _emit_progress(
        state,
        "retrieval",
        "done",
        evidence_count=len(all_docs),
        top_sources=[doc.get("title", "Untitled") for doc in all_docs[:3]],
    )
    return {"raw_docs": all_docs}


async def rerank_node(state: RAGState) -> dict:
    """Rerank + CRAG gate."""
    await _emit_progress(state, "assessment", "running", evidence_count=len(state.get("raw_docs", [])))
    docs = rerank(state["question"], state["raw_docs"], top_k=5)
    filtered, is_confident = crag_gate(docs)
    await _emit_progress(
        state,
        "assessment",
        "done",
        evidence_count=len(filtered),
        is_confident=is_confident,
    )
    return {"reranked_docs": filtered, "is_confident": is_confident}


def assemble_node(state: RAGState) -> dict:
    """Assemble context with lost-in-middle ordering and citations."""
    context, ordered = assemble_context(state["reranked_docs"])
    return {"context": context, "sources": ordered}


async def generate_node(state: RAGState, config: RunnableConfig) -> dict:
    """Generate final answer."""
    await _emit_progress(state, "generation", "running", source_count=len(state.get("sources", [])))
    if not state.get("is_confident", True):
        answer = (
            "I could not find sufficiently relevant information in the medical knowledge base "
            "to answer this question confidently. Please consult a medical professional."
        )
    else:
        answer = await generate_answer(
            state["question"],
            state["context"],
            state.get("model_name", "gemini"),
            config=config,
        )
    await _emit_progress(
        state,
        "generation",
        "done",
        is_confident=state.get("is_confident", True),
        source_count=len(state.get("sources", [])),
    )
    return {"answer": answer}


def build_rag_graph() -> StateGraph:
    graph = StateGraph(RAGState)
    graph.add_node("query_transform", query_transform_node)
    graph.add_node("search", search_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("assemble", assemble_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("query_transform")
    graph.add_edge("query_transform", "search")
    graph.add_edge("search", "rerank")
    graph.add_edge("rerank", "assemble")
    graph.add_edge("assemble", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# Singleton compiled graph
_rag_graph = None


def get_rag_graph():
    global _rag_graph
    if _rag_graph is None:
        _rag_graph = build_rag_graph()
    return _rag_graph


async def run_standard_rag(
    question: str,
    model_name: str = "gemini",
    role: str = "doctor",
    progress_callback=None,
    config: dict | None = None,
) -> dict:
    """Run the standard RAG pipeline."""
    graph = get_rag_graph()
    runtime_config = dict(config or {})
    if not runtime_config:
        from generation.observability import create_langfuse_handler

        handler = create_langfuse_handler()
        if handler:
            runtime_config["callbacks"] = [handler]
    result = await graph.ainvoke({
        "question": question,
        "model_name": model_name,
        "role": role,
        "search_mode": "standard",
        "queries": [],
        "raw_docs": [],
        "reranked_docs": [],
        "is_confident": True,
        "context": "",
        "answer": "",
        "sources": [],
        "messages": [HumanMessage(content=question)],
        "progress_callback": progress_callback,
    }, config=runtime_config)
    await _stream_answer_chunks(result["answer"], progress_callback)
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "is_confident": result["is_confident"],
        "search_mode": "standard",
    }


async def run_rag(
    question: str,
    model_name: str = "gemini",
    role: str = "doctor",
    search_mode: str = "standard",
    progress_callback=None,
) -> dict:
    """Route between standard and Deep Search modes."""
    runtime_config: dict = {}
    from generation.observability import create_langfuse_handler

    handler = create_langfuse_handler()
    if handler:
        runtime_config["callbacks"] = [handler]

    if search_mode == "deep":
        result = await run_deep_search(
            question,
            model_name=model_name,
            role=role,
            progress_callback=progress_callback,
            config=runtime_config,
        )
        await _stream_answer_chunks(result["answer"], progress_callback)
        return result

    return await run_standard_rag(
        question,
        model_name=model_name,
        role=role,
        progress_callback=progress_callback,
        config=runtime_config,
    )
