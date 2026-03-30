"""MCP Server 1 — medical_search (:9001/mcp).

Exposes hybrid_search + rerank as MCP tools via fastmcp.
"""
import os
from fastmcp import FastMCP
from retrieval.hybrid_retriever import hybrid_search
from retrieval.reranker import rerank

mcp = FastMCP("medical_search")


@mcp.tool()
def search(query: str, top_k: int = 10, filters: dict | None = None) -> list[dict]:
    """Search the StatPearls medical knowledge base. Returns ranked chunks."""
    results = hybrid_search(query, top_k=top_k)
    return results


@mcp.tool()
def search_and_rerank(query: str, top_k: int = 5) -> list[dict]:
    """Hybrid search followed by cross-encoder reranking."""
    raw = hybrid_search(query, top_k=top_k * 2)
    reranked = rerank(query, raw, top_k=top_k)
    return reranked


if __name__ == "__main__":
    port = int(os.getenv("MCP_SEARCH_PORT", "9001"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, path="/mcp")
