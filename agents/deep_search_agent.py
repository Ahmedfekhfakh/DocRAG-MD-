"""Deep Search agent — bounded LangGraph workflow for multi-step retrieval."""
from __future__ import annotations

import inspect
from typing import TypedDict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from generation.generator import generate_answer
from generation.llm_router import get_llm
from retrieval.context_assembler import assemble_context, deduplicate
from retrieval.crag import crag_gate
from retrieval.hybrid_retriever import hybrid_search
from retrieval.query_transform.decompose import decompose_question
from retrieval.query_transform.hyde import generate_hypothetical_doc
from retrieval.query_transform.multi_query import expand_query
from retrieval.reranker import rerank
from retrieval.source_drilldown import drill_down_sources

_FOLLOW_UP_PROMPT = PromptTemplate.from_template(
    "You are refining a medical retrieval workflow.\n"
    "Original question: {question}\n"
    "Current evidence titles:\n{titles}\n\n"
    "Generate up to 2 focused follow-up search queries that may recover missing evidence.\n"
    "Output one query per line with no numbering."
)


class DeepSearchState(TypedDict):
    question: str
    model_name: str
    role: str
    queries: list[str]
    evidence_pool: list[dict]
    reranked_docs: list[dict]
    is_confident: bool
    context: str
    answer: str
    sources: list[dict]
    follow_up_queries: list[str]
    iteration: int
    max_iterations: int
    progress_callback: object | None


def _dedupe_queries(queries: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for query in queries:
        query = query.strip()
        if not query:
            continue
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(query)
    return ordered


def _doc_key(doc: dict) -> str:
    return doc.get("doc_id") or doc.get("title") or doc.get("content", "")[:120]


def _merge_docs(existing: list[dict], new_docs: list[dict]) -> list[dict]:
    merged: list[dict] = list(existing)
    seen = {_doc_key(doc) for doc in existing}
    for doc in new_docs:
        key = _doc_key(doc)
        if key in seen:
            continue
        seen.add(key)
        merged.append(doc)
    return merged


async def _emit_progress(state: DeepSearchState, step: str, status: str, **payload) -> None:
    callback = state.get("progress_callback")
    if not callback:
        return
    event = {"type": "trace", "step": step, "status": status, **payload}
    result = callback(event)
    if inspect.isawaitable(result):
        await result


async def _generate_follow_up_queries(
    question: str,
    docs: list[dict],
    model_name: str,
    config: RunnableConfig | None = None,
) -> list[str]:
    titles = "\n".join(
        f"- {doc.get('title', 'Untitled')}" for doc in docs[:4] if doc.get("title")
    ) or "- No specific title found"
    chain = _FOLLOW_UP_PROMPT | get_llm(model_name) | StrOutputParser()
    invoke_config = dict(config) if config else {}
    invoke_config["run_name"] = "deep_search_follow_up_queries"
    text = await chain.ainvoke({"question": question, "titles": titles}, config=invoke_config)
    queries = [
        line.strip("-* \t")
        for line in text.splitlines()
        if line.strip("-* \t")
    ]
    return _dedupe_queries(queries)[:2]


async def plan_node(state: DeepSearchState, config: RunnableConfig) -> dict:
    await _emit_progress(
        state,
        "planning",
        "running",
        iteration=state.get("iteration", 0),
    )

    if state.get("follow_up_queries"):
        queries = _dedupe_queries(state["follow_up_queries"])
    else:
        question = state["question"]
        model_name = state.get("model_name", "gemini")

        decomposed: list[str] = []
        expanded: list[str] = []
        hypothetical = ""

        try:
            decomposed = await decompose_question(question, model_name, config=config)
        except Exception:
            decomposed = []

        try:
            expanded = await expand_query(question, model_name, config=config)
        except Exception:
            expanded = [question]

        try:
            hypothetical = await generate_hypothetical_doc(question, model_name, config=config)
        except Exception:
            hypothetical = ""

        queries = _dedupe_queries([question, *decomposed, *expanded, hypothetical])

    await _emit_progress(
        state,
        "planning",
        "done",
        iteration=state.get("iteration", 0),
        queries=queries[:6],
    )
    return {"queries": queries, "follow_up_queries": []}


async def search_node(state: DeepSearchState) -> dict:
    await _emit_progress(
        state,
        "retrieval",
        "running",
        query_count=len(state.get("queries", [])),
    )

    gathered: list[dict] = []
    for query in state.get("queries", []):
        gathered.extend(hybrid_search(query, top_k=8))

    evidence_pool = _merge_docs(state.get("evidence_pool", []), gathered)
    await _emit_progress(
        state,
        "retrieval",
        "done",
        queries=state.get("queries", [])[:6],
        evidence_count=len(evidence_pool),
        top_sources=[doc.get("title", "Untitled") for doc in evidence_pool[:3]],
    )
    return {"evidence_pool": evidence_pool}


async def drilldown_node(state: DeepSearchState) -> dict:
    await _emit_progress(
        state,
        "drilldown",
        "running",
        candidate_count=min(3, len(state.get("evidence_pool", []))),
    )

    extras = drill_down_sources(state.get("evidence_pool", []), top_n=3, per_source=2)
    evidence_pool = _merge_docs(state.get("evidence_pool", []), extras)

    await _emit_progress(
        state,
        "drilldown",
        "done",
        evidence_count=len(evidence_pool),
        top_sources=[doc.get("title", "Untitled") for doc in evidence_pool[:3]],
    )
    return {"evidence_pool": evidence_pool}


async def assess_node(state: DeepSearchState, config: RunnableConfig) -> dict:
    await _emit_progress(
        state,
        "assessment",
        "running",
        evidence_count=len(state.get("evidence_pool", [])),
    )

    reranked_docs = rerank(state["question"], deduplicate(state.get("evidence_pool", [])), top_k=6)
    reranked_docs, is_confident = crag_gate(reranked_docs)

    follow_up_queries: list[str] = []
    can_iterate = state.get("iteration", 0) + 1 < state.get("max_iterations", 2)
    if can_iterate and (not is_confident or len(reranked_docs) < 3):
        try:
            follow_up_queries = await _generate_follow_up_queries(
                state["question"],
                reranked_docs or state.get("evidence_pool", []),
                state.get("model_name", "gemini"),
                config=config,
            )
        except Exception:
            titles = [
                doc.get("title", "").strip()
                for doc in (reranked_docs or state.get("evidence_pool", []))[:2]
                if doc.get("title", "").strip()
            ]
            follow_up_queries = [f"{state['question']} {title}" for title in titles]

    await _emit_progress(
        state,
        "assessment",
        "done",
        is_confident=is_confident,
        evidence_count=len(reranked_docs),
        follow_up_queries=follow_up_queries,
    )
    return {
        "reranked_docs": reranked_docs,
        "is_confident": is_confident,
        "follow_up_queries": _dedupe_queries(follow_up_queries)[:2],
    }


def route_after_assessment(state: DeepSearchState) -> str:
    if state.get("follow_up_queries"):
        return "search_more"
    return "assemble"


async def search_more_node(state: DeepSearchState) -> dict:
    next_iteration = state.get("iteration", 0) + 1
    await _emit_progress(
        state,
        "assessment",
        "running",
        iteration=next_iteration,
        follow_up_queries=state.get("follow_up_queries", []),
    )
    return {"iteration": next_iteration}


def assemble_node(state: DeepSearchState) -> dict:
    context, ordered = assemble_context(state.get("reranked_docs", []))
    return {"context": context, "sources": ordered}


async def generate_node(state: DeepSearchState, config: RunnableConfig) -> dict:
    await _emit_progress(
        state,
        "generation",
        "running",
        source_count=len(state.get("sources", [])),
    )

    if not state.get("is_confident", True) or not state.get("context", "").strip():
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
        source_count=len(state.get("sources", [])),
        is_confident=state.get("is_confident", True),
    )
    return {"answer": answer}


def build_deep_search_graph() -> StateGraph:
    graph = StateGraph(DeepSearchState)
    graph.add_node("plan", plan_node)
    graph.add_node("search", search_node)
    graph.add_node("drilldown", drilldown_node)
    graph.add_node("assessment", assess_node)
    graph.add_node("search_more", search_more_node)
    graph.add_node("assemble", assemble_node)
    graph.add_node("generation", generate_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "drilldown")
    graph.add_edge("drilldown", "assessment")
    graph.add_conditional_edges(
        "assessment",
        route_after_assessment,
        {"search_more": "search_more", "assemble": "assemble"},
    )
    graph.add_edge("search_more", "plan")
    graph.add_edge("assemble", "generation")
    graph.add_edge("generation", END)
    return graph.compile()


_deep_search_graph = None


def get_deep_search_graph():
    global _deep_search_graph
    if _deep_search_graph is None:
        _deep_search_graph = build_deep_search_graph()
    return _deep_search_graph


async def run_deep_search(
    question: str,
    model_name: str = "gemini",
    role: str = "doctor",
    progress_callback=None,
    config: dict | None = None,
) -> dict:
    graph = get_deep_search_graph()
    result = await graph.ainvoke(
        {
            "question": question,
            "model_name": model_name,
            "role": role,
            "queries": [],
            "evidence_pool": [],
            "reranked_docs": [],
            "is_confident": True,
            "context": "",
            "answer": "",
            "sources": [],
            "follow_up_queries": [],
            "iteration": 0,
            "max_iterations": 2,
            "progress_callback": progress_callback,
        },
        config=config,
    )
    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "is_confident": result.get("is_confident", True),
        "search_mode": "deep",
    }
