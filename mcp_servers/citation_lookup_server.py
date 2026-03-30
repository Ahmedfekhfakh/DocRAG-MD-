"""MCP Server 2 — citation_lookup (:9002/mcp).

Exposes source lookup by doc_id from Qdrant.
"""
import os
from fastmcp import FastMCP
from retrieval.qdrant_client import get_qdrant_client

COLLECTION = os.getenv("COLLECTION_NAME", "medical_rag")

mcp = FastMCP("citation_lookup")


@mcp.tool()
def lookup(doc_id: str) -> dict:
    """Fetch full article text + metadata by doc_id from StatPearls."""
    client = get_qdrant_client()
    results = client.scroll(
        collection_name=COLLECTION,
        scroll_filter={"must": [{"key": "doc_id", "match": {"value": doc_id}}]},
        limit=1,
        with_payload=True,
    )
    points, _ = results
    if not points:
        return {"error": f"No document found with doc_id={doc_id}"}
    payload = points[0].payload
    return {
        "doc_id": payload.get("doc_id", doc_id),
        "title": payload.get("title", ""),
        "content": payload.get("content", ""),
        "source": payload.get("source", "statpearls"),
    }


if __name__ == "__main__":
    port = int(os.getenv("MCP_CITATION_PORT", "9002"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, path="/mcp")
