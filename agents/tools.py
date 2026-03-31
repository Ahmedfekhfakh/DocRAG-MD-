"""LangChain @tool wrappers for retrieval, rerank, generation, graph, and deep search."""
from langchain_core.tools import tool
from retrieval.hybrid_retriever import hybrid_search
from retrieval.reranker import rerank
from retrieval.crag import crag_gate
from retrieval.context_assembler import assemble_context
from generation.generator import generate_answer
from retrieval.knowledge_graph import query_graph
from retrieval.deep_search import search_pubmed, fetch_abstracts


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
async def generate_answer_tool(question: str, context: str, model_name: str = "gemini") -> str:
    """Generate a cited answer from context using the specified LLM."""
    return await generate_answer(question, context, model_name)


@tool
def search_knowledge_graph(entity: str) -> str:
    """Cherche les relations d'une entité médicale dans PrimeKG
    (maladies, médicaments, symptômes, interactions).
    """
    from api.main import app
    G = app.state.kg
    results = query_graph(G, entity)
    if not results:
        return f"Aucune donnée pour '{entity}' dans le graph."
    grouped: dict[str, list[str]] = {}
    for r in results[:20]:
        rel = r["relation"]
        if rel not in grouped:
            grouped[rel] = []
        grouped[rel].append(f"{r['entity']} [{r['type']}]")
    lines = [f"Knowledge graph — '{entity}' :"]
    for rel, entities in grouped.items():
        lines.append(f"  [{rel}] : {', '.join(entities)}")
    return "\n".join(lines)


@tool
def deep_search_pubmed(query: str) -> str:
    """Recherche web sur PubMed : 36M+ articles médicaux peer-reviewed.
    Utilisé quand le mode Deep Search est activé.
    """
    results = search_pubmed(query, max_results=5)
    if not results:
        return "Aucun article trouvé sur PubMed."
    pmids = [r["pmid"] for r in results]
    abstracts = fetch_abstracts(pmids)
    lines = []
    for r in results:
        abstract = abstracts.get(r["pmid"], "Pas d'abstract.")
        lines.append(
            f"[PMID:{r['pmid']}] {r['title']}\n"
            f"  {r['authors']} — {r['journal']} ({r['date']})\n"
            f"  {abstract[:300]}..."
        )
    return "\n\n".join(lines)
