# DocRAG-MD

Production-grade Medical RAG platform powered by Gemini, built on StatPearls clinical knowledge. Features hybrid dense+sparse retrieval, LangGraph agents, MCP servers, and a React chat UI.

---

## Architecture

```
┌─────────────────── REACT FRONTEND  :3000 ──────────────────────┐
│  Chat UI · Expandable citations sidebar · WebSocket streaming  │
└────────────────────────────┬───────────────────────────────────┘
                             │ REST + WebSocket
┌────────────────────────────▼───────────────────────────────────┐
│               FASTAPI BACKEND  :8000                           │
│  POST /query · POST /ingest · GET /health · WS /ws/chat        │
├────────────────────────────────────────────────────────────────┤
│  AGENT 1 — RAG Orchestrator (LangGraph)                        │
│    HyDE → hybrid_search → rerank → CRAG gate → generate        │
│  AGENT 2 — Evaluator Agent (LangGraph)                         │
│    MedMCQA benchmark · accuracy report                         │
├────────────────────────────────────────────────────────────────┤
│  MCP SERVER 1 — medical_search  :9001/mcp                      │
│  MCP SERVER 2 — citation_lookup :9002/mcp                      │
├──────────────────────────────┬─────────────────────────────────┤
│  QDRANT  :6333               │  POSTGRES :5432                 │
│  dense (PubMedBERT) + sparse │  (Langfuse observability)       │
└──────────────────────────────┴─────────────────────────────────┘
```

**Pipeline:** Query → HyDE + multi-query expansion → Hybrid RRF (dense PubMedBERT + sparse BM25) → MiniLM cross-encoder rerank → CRAG confidence gate → lost-in-middle context assembly → Gemini generation → cited response.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| Package manager | [uv](https://github.com/astral-sh/uv) + `pyproject.toml` |
| LLM | Gemini 2.5 Flash (via `GOOGLE_API_KEY`) |
| LLM framework | LangChain (LCEL) + LangGraph |
| Vector DB | Qdrant (dense 768-dim cosine + sparse BM25) |
| Embeddings | PubMedBERT (`pritamdeka/PubMedBERT-mnli-snli-scinli-scitail-mednli-stsb`) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| API | FastAPI + WebSocket |
| MCP | fastmcp (Streamable HTTP) |
| Frontend | React 18 + Vite + TailwindCSS |
| Infra | Docker Compose (4 services) |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Ahmedfekhfakh/DocRAG-MD-.git
cd DocRAG-MD-
```

### 2. Set your Gemini API key

Copy the example env file and fill in your key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
GOOGLE_API_KEY=AIza...   # get one free at https://aistudio.google.com
```

### 3. Download the data (run once, locally)

This downloads and chunks the StatPearls medical knowledge base (~1.7 GB download → JSONL):

```bash
# Full dataset (~300k chunks, takes 10–20 min)
bash download_data.sh

# Or smoke test (5000 chunks, fast)
bash download_data.sh 5000
```

> **Requirements:** Python 3.11+ with dependencies installed (see Manual Installation below if not using Docker directly).

### 4. Start with Docker Compose

```bash
docker compose up
```

On first run, Docker will:
- Start Qdrant vector DB on `:6333`
- Build and start the API — auto-ingests `data/statpearls_chunks.jsonl` into Qdrant if collection is empty
- Start MCP servers on `:9001` and `:9002`
- Serve the React frontend via nginx on `:3000`

**Open `http://localhost:3000`** — the chat UI is ready.

> On subsequent runs, ingestion is skipped (Qdrant already has data). HuggingFace model weights are cached in a Docker volume so they don't re-download.

---

## Manual Installation (no Docker for the app)

Use this if you want to run the API locally outside Docker (you still need Docker for Qdrant).

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Create virtual environment and install dependencies

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e .
```

### 3. Start Qdrant

```bash
docker run -d -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

### 4. Download the data

```bash
bash download_data.sh 5000    # or without argument for full dataset
```

### 5. Set environment variables

```bash
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export GOOGLE_API_KEY=AIza...
```

### 6. Ingest StatPearls into Qdrant

```bash
python -m ingestion.pipeline
```

### 7. Start the API

```bash
# Start MCP servers
python -m mcp_servers.medical_search_server &
python -m mcp_servers.citation_lookup_server &

# Start FastAPI
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 8. (Optional) Run the frontend locally

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

---

## API Reference

### `GET /health`

```json
{ "status": "ok", "qdrant": "ok", "version": "0.1.0" }
```

### `POST /query`

```json
// Request
{
  "question": "What are the first-line treatments for hypertension?",
  "model": "gemini",
  "use_cot": false
}

// Response
{
  "answer": "First-line antihypertensives include ACE inhibitors [1], thiazide diuretics [2]...",
  "sources": [
    { "doc_id": "...", "title": "Hypertension", "content": "...", "source": "statpearls", "score": 8.3 }
  ],
  "model": "gemini",
  "is_confident": true
}
```

### `WS /ws/chat`

WebSocket for the frontend. Send:
```json
{ "question": "What is Type 2 diabetes?", "model": "gemini" }
```

Receive:
```json
{ "type": "answer", "answer": "...", "sources": [...], "model": "gemini" }
```

### `POST /ingest`

```json
{ "limit": null }   // null = all chunks
```

---

## MCP Servers

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "medical_search": {"url": "http://localhost:9001/mcp", "transport": "http"},
    "citation_lookup": {"url": "http://localhost:9002/mcp", "transport": "http"},
})
```

| Server | Tool | Description |
|--------|------|-------------|
| `medical_search` | `search(query, top_k)` | Hybrid dense+sparse search with reranking |
| `citation_lookup` | `lookup(doc_id)` | Fetch full article text by doc_id |

---

## Running Tests

```bash
uv run pytest tests/ -v
```

**37 / 37 passing.**

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | — | **Required.** Gemini API key |
| `QDRANT_HOST` | `qdrant` | Qdrant hostname (use `localhost` for local dev) |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `COLLECTION_NAME` | `medical_rag` | Qdrant collection name |
| `DENSE_MODEL` | `pritamdeka/PubMedBERT-...` | HuggingFace embedding model |
| `CRAG_CONFIDENCE_THRESHOLD` | `0.60` | Sigmoid score cutoff for CRAG gate |

---

## Service URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| FastAPI | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| MCP medical_search | http://localhost:9001/mcp |
| MCP citation_lookup | http://localhost:9002/mcp |
| Qdrant dashboard | http://localhost:6333/dashboard |

---

## Troubleshooting

**Qdrant collection empty after startup**
```bash
docker compose exec api python -m ingestion.pipeline
```

**HuggingFace model re-downloads on every restart**
The `hf_cache` Docker volume persists the model weights. If it was just added, restart once:
```bash
docker compose down && docker compose up
```

**Permission denied on `data/statpearls_chunks.jsonl`**
```bash
sudo chown -R $USER:$USER data/
```

**Docker not found in WSL**
Open Docker Desktop → Settings → Resources → WSL Integration → enable your distro.
