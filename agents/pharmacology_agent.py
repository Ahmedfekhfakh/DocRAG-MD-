"""Agent pharmacologie — Spécialisé médicaments, interactions, contre-indications, posologie.

Pipeline : query_transform → search + graph_search → rerank → assemble → generate → self_reflect
Utilise PrimeKG avec filtre contraindication, indication, drug_drug, off-label use.
"""
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from generation.llm_router import get_llm
from retrieval.hybrid_retriever import hybrid_search
from retrieval.deep_search import search_pubmed, fetch_abstracts
from retrieval.reranker import rerank_async
from retrieval.crag import crag_gate
from retrieval.context_assembler import assemble_context
from retrieval.query_transform.hyde import generate_hypothetical_doc
from retrieval.self_reflect import check_response
from retrieval.knowledge_graph import query_graph, extract_medical_terms
from generation.generator import generate_answer
import asyncio
import operator


class PharmacologyState(TypedDict):
    question: str
    model_name: str
    mode: str
    queries: list[str]
    raw_docs: list[dict]
    graph_context: str
    reranked_docs: list[dict]
    is_confident: bool
    context: str
    sources_text: str
    answer: str
    sources: list[dict]
    retry_count: int
    retry_reason: str
    final_answer: str
    messages: Annotated[list, operator.add]


async def query_transform_and_search_node(state: PharmacologyState, config: RunnableConfig) -> dict:
    question = state["question"]
    reason = state.get("retry_reason", "")
    if reason:
        question = f"{question} (Contexte: {reason})"
    mode = state.get("mode", "rag")
    model_name = state.get("model_name", "gemini")

    if mode == "graph":
        return {"queries": [question], "raw_docs": []}

    if mode == "deep_search":
        results = search_pubmed(question, max_results=10)
        pmids = [r["pmid"] for r in results]
        abstracts = fetch_abstracts(pmids) if pmids else {}
        for r in results:
            r["content"] = abstracts.get(r["pmid"], "")
            r["doc_id"] = f"pubmed:{r['pmid']}"
        return {"queries": [question], "raw_docs": results}

    async def _hyde():
        try:
            return await generate_hypothetical_doc(question, model_name, config=config)
        except Exception:
            return None

    async def _search_original():
        return await asyncio.to_thread(hybrid_search, question, 10)

    hypo, base_docs = await asyncio.gather(_hyde(), _search_original())

    seen_ids = {d.get("doc_id", d.get("content", "")[:50]) for d in base_docs}
    all_docs = list(base_docs)

    if hypo:
        hyde_docs = await asyncio.to_thread(hybrid_search, hypo, 10)
        for d in hyde_docs:
            did = d.get("doc_id", d.get("content", "")[:50])
            if did not in seen_ids:
                seen_ids.add(did)
                all_docs.append(d)

    queries = [question, hypo] if hypo else [question]
    return {"queries": queries, "raw_docs": all_docs}


async def graph_search_node(state: PharmacologyState, config: RunnableConfig) -> dict:
    """Enrichit avec PrimeKG — relations pharmacologiques."""
    mode = state.get("mode", "rag")
    if mode not in ("graph", "hybrid"):
        return {"graph_context": ""}
    try:
        from api.main import app
        G = app.state.kg
        if G is None:
            return {"graph_context": ""}
    except Exception:
        return {"graph_context": ""}

    terms = await extract_medical_terms(state["question"], state.get("model_name", "gemini"), config=config)
    results = []
    seen = set()
    for term in terms:
        for relation in ["contraindication", "indication", "drug_drug", "off-label use"]:
            hits = query_graph(G, term, relation_filter=relation)
            for h in hits:
                key = (h["entity"], h["relation"])
                if key not in seen:
                    seen.add(key)
                    results.append(h)
        if len(results) >= 15:
            break

    if not results:
        return {"graph_context": ""}

    lines = ["[Knowledge Graph — Pharmacology Relations]"]
    for r in results[:15]:
        lines.append(f"  {r['relation']}: {r['entity']} [{r['type']}]")
    return {"graph_context": "\n".join(lines)}


async def rerank_node(state: PharmacologyState) -> dict:
    mode = state.get("mode", "rag")
    if mode == "graph":
        return {"reranked_docs": [], "is_confident": True}
    docs = await rerank_async(state["question"], state["raw_docs"], top_k=5)
    filtered, is_confident = crag_gate(docs)
    return {"reranked_docs": filtered, "is_confident": is_confident}


def assemble_node(state: PharmacologyState) -> dict:
    context, ordered = assemble_context(state["reranked_docs"])
    graph_ctx = state.get("graph_context", "")
    if graph_ctx:
        context = f"{graph_ctx}\n\n{context}"
    return {"context": context, "sources": ordered, "sources_text": context}


async def generate_node(state: PharmacologyState, config: RunnableConfig) -> dict:
    context = state.get("context", "")
    if not state.get("is_confident", True) or not context.strip():
        answer = (
            "I could not find sufficiently relevant pharmacological information "
            "to answer this question confidently. Please consult a pharmacist or physician."
        )
    else:
        answer = await generate_answer(
            state["question"], context, state.get("model_name", "gemini"),
            mode=state.get("mode", "rag"), config=config,
        )
    return {"answer": answer}


async def self_reflect_node(state: PharmacologyState, config: RunnableConfig) -> dict:
    llm = get_llm(state.get("model_name", "gemini"))
    result = await check_response(
        llm=llm,
        question=state["question"],
        sources=state.get("sources_text", ""),
        answer=state["answer"],
        config=config,
    )
    if (result.get("faithful") and result.get("complete")) \
       or state.get("retry_count", 0) >= 2:
        return {"final_answer": state["answer"]}
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "retry_reason": result.get("reason", ""),
        "final_answer": "",
    }


def should_retry(state: PharmacologyState) -> str:
    if state.get("final_answer"):
        return "done"
    return "retry"


def build_pharmacology_graph() -> StateGraph:
    graph = StateGraph(PharmacologyState)
    graph.add_node("query_and_search", query_transform_and_search_node)
    graph.add_node("graph_search", graph_search_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("assemble", assemble_node)
    graph.add_node("generate", generate_node)
    graph.add_node("self_reflect", self_reflect_node)

    graph.set_entry_point("query_and_search")
    graph.add_edge("query_and_search", "graph_search")
    graph.add_edge("graph_search", "rerank")
    graph.add_edge("rerank", "assemble")
    graph.add_edge("assemble", "generate")
    graph.add_edge("generate", "self_reflect")
    graph.add_conditional_edges("self_reflect", should_retry, {
        "done": END,
        "retry": "query_and_search",
    })

    return graph.compile()


_pharmacology_graph = None


def get_pharmacology_graph():
    global _pharmacology_graph
    if _pharmacology_graph is None:
        _pharmacology_graph = build_pharmacology_graph()
    return _pharmacology_graph


async def run_pharmacology_pipeline(question: str, model_name: str = "gemini", mode: str = "rag", config=None) -> dict:
    graph = get_pharmacology_graph()
    result = await graph.ainvoke({
        "question": question,
        "model_name": model_name,
        "mode": mode,
        "queries": [],
        "raw_docs": [],
        "graph_context": "",
        "reranked_docs": [],
        "is_confident": True,
        "context": "",
        "sources_text": "",
        "answer": "",
        "sources": [],
        "retry_count": 0,
        "retry_reason": "",
        "final_answer": "",
        "messages": [HumanMessage(content=question)],
    }, config=config)
    return {
        "answer": result.get("final_answer") or result["answer"],
        "sources": result["sources"],
        "is_confident": result["is_confident"],
    }
