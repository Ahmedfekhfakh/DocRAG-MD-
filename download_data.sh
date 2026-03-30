#!/bin/bash
# Download and chunk StatPearls data locally before running Docker Compose.
# Run once:  bash download_data.sh [CHUNK_LIMIT]
#
# CHUNK_LIMIT (optional): max chunks to extract (0 = all, default = all)
# Example:   bash download_data.sh 5000   # smoke-test with 5 000 chunks
#            bash download_data.sh         # full dataset

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CHUNK_LIMIT="${1:-0}"

export SKIP_GGUF=1
export SKIP_DATA=0
export DATA_CHUNK_LIMIT="$CHUNK_LIMIT"

echo "================================================"
echo "  StatPearls Data Downloader"
echo "  Chunk limit: ${CHUNK_LIMIT:-all}"
echo "  Output: data/statpearls_chunks.jsonl"
echo "================================================"

# Ensure Python is available
if ! command -v python &>/dev/null && ! command -v python3 &>/dev/null; then
    echo "ERROR: Python not found. Please activate your virtual environment first."
    echo "  uv venv && source .venv/bin/activate && uv pip install -e ."
    exit 1
fi

PYTHON="${PYTHON:-python}"
command -v python &>/dev/null || PYTHON=python3

"$PYTHON" -m scripts.download_all

echo ""
echo "================================================"
echo "  Data ready: data/statpearls_chunks.jsonl"
echo "  Next step: docker compose up"
echo "================================================"
