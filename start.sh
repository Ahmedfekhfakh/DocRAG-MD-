#!/bin/bash
set -e

# Auto-ingest if Qdrant collection is empty
echo "Checking if ingestion is needed ..."
python - <<'PYEOF'
import os, sys
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

COLLECTION = os.getenv("COLLECTION_NAME", "medical_rag")
try:
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "qdrant"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )
    info = client.get_collection(COLLECTION)
    count = info.points_count or 0
    print(f"Collection '{COLLECTION}' has {count} points.")
    if count == 0:
        raise SystemExit(1)
    sys.exit(0)
except Exception:
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    DATA_FILE="${DATA_PATH:-/app/data/statpearls_chunks.jsonl}"
    if [ -f "$DATA_FILE" ]; then
        echo "Running ingestion pipeline ..."
        python -m ingestion.pipeline
    else
        echo "Warning: $DATA_FILE not found, skipping ingestion."
    fi
fi

echo "Starting MCP server 1 (medical_search) on :9001 ..."
python -m mcp_servers.medical_search_server &

echo "Starting MCP server 2 (citation_lookup) on :9002 ..."
python -m mcp_servers.citation_lookup_server &

echo "Starting FastAPI on :8000 ..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
