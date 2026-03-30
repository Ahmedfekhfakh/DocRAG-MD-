"""Agent 1 — RAG Orchestrator (LangGraph ReAct).

query_transform → hybrid_search → rerank → crag_gate → generate
"""
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from generation.llm_router import get_llm
from retrieval.hybrid_retriever import hybrid_search
from retrieval.reranker import rerank
from retrieval.crag import crag_gate
from retrieval.context_assembler import assemble_context
from retrieval.query_transform.hyde import generate_hypothetical_doc
from generation.generator import generate_answer
from .tools import search_qdrant, rerank_results, generate_answer_tool

import operator


class RAGState(TypedDict):
    question: str
    model_name: str
    queries: list[str]
    raw_docs: list[dict]
    reranked_docs: list[dict]
    is_confident: bool
    context: str
    answer: str
    sources: list[dict]
    messages: Annotated[list, operator.add]


async def query_transform_node(state: RAGState) -> dict:
    """Generate HyDE hypothetical doc and use as search query."""
    question = state["question"]
    model_name = state.get("model_name", "gemini")
    try:
        hypo = await generate_hypothetical_doc(question, model_name)
        queries = [question, hypo]
    except Exception:
        queries = [question]
    return {"queries": queries}


async def search_node(state: RAGState) -> dict:
    """Hybrid search for all queries, merge results."""
    all_docs: list[dict] = []
    seen_ids: set[str] = set()
    for q in state.get("queries", [state["question"]]):
        docs = hybrid_search(q, top_k=10)
        for d in docs:
            did = d.get("doc_id", d.get("content", "")[:50])
            if did not in seen_ids:
                seen_ids.add(did)
                all_docs.append(d)
    return {"raw_docs": all_docs}


def rerank_node(state: RAGState) -> dict:
    """Rerank + CRAG gate."""
    docs = rerank(state["question"], state["raw_docs"], top_k=5)
    filtered, is_confident = crag_gate(docs)
    return {"reranked_docs": filtered, "is_confident": is_confident}


def assemble_node(state: RAGState) -> dict:
    """Assemble context with lost-in-middle ordering and citations."""
    context, ordered = assemble_context(state["reranked_docs"])
    return {"context": context, "sources": ordered}


async def generate_node(state: RAGState) -> dict:
    """Generate final answer."""
    if not state.get("is_confident", True):
        answer = (
            "I could not find sufficiently relevant information in the medical knowledge base "
            "to answer this question confidently. Please consult a medical professional."
        )
    else:
        answer = await generate_answer(
            state["question"], state["context"], state.get("model_name", "gemini")
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


async def run_rag(question: str, model_name: str = "gemini") -> dict:
    """Run the full RAG pipeline. Returns {'answer': str, 'sources': list}."""
    from generation.observability import get_langfuse_handler
    graph = get_rag_graph()
    config = {}
    handler = get_langfuse_handler()
    if handler:
        config["callbacks"] = [handler]
    result = await graph.ainvoke({
        "question": question,
        "model_name": model_name,
        "queries": [],
        "raw_docs": [],
        "reranked_docs": [],
        "is_confident": True,
        "context": "",
        "answer": "",
        "sources": [],
        "messages": [HumanMessage(content=question)],
    }, config=config)
    return {"answer": result["answer"], "sources": result["sources"]}
