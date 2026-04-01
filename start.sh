#!/bin/bash

# Start MCP servers in background
echo "Starting MCP server 1 (medical_search) on :9001 ..."
python -m mcp_servers.medical_search_server &

echo "Starting MCP server 2 (citation_lookup) on :9002 ..."
python -m mcp_servers.citation_lookup_server &

# Start FastAPI in background (so healthcheck passes during ingestion)
echo "Starting FastAPI on :8000 ..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for API to be ready
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "API is ready."
        break
    fi
    sleep 2
done

AUTO_INGEST="${AUTO_INGEST:-0}"
INGEST_LIMIT="${INGEST_LIMIT:-}"

if [ "$AUTO_INGEST" = "1" ]; then
    # Auto-ingest if Qdrant collection is empty
    echo "Checking if ingestion is needed ..."
    if ! python - <<'PYEOF'
import os, sys
from qdrant_client import QdrantClient

COLLECTION = os.getenv("COLLECTION_NAME", "medical_rag")

try:
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "qdrant"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )
    info = client.get_collection(COLLECTION)
    count = info.points_count or 0
    print(f"Collection '{COLLECTION}' has {count} points.")
    sys.exit(0 if count > 0 else 1)
except Exception:
    sys.exit(1)
PYEOF
    then
        DATA_FILE="${DATA_PATH:-/app/data/statpearls_chunks.jsonl}"
        if [ -f "$DATA_FILE" ]; then
            echo "Running ingestion pipeline ..."
            if [ -n "$INGEST_LIMIT" ]; then
                python -m ingestion.pipeline "$INGEST_LIMIT"
            else
                python -m ingestion.pipeline
            fi
        else
            echo "Warning: $DATA_FILE not found, skipping ingestion."
            echo "Run 'bash download_data.sh' on the host to download StatPearls."
        fi
    fi
else
    echo "AUTO_INGEST=0, skipping ingestion at startup."
fi

# Keep container alive with uvicorn as main process
wait $API_PID
