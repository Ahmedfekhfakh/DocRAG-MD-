# CLAUDE.md — Medical RAG Platform

> **Stack:** Python 3.11 · LangChain · LangGraph · Qdrant · FastAPI · llama.cpp · Docker Compose · React (frontend)
> **LLMs:** BioMistral-7B (local GGUF via llama.cpp) · Gemini 2.5 Flash (API) · GPT-4o (API)
> **DEADLINE: tomorrow afternoon. Every decision must favor "working now" over "perfect later".**

---

## What this is

A production-grade RAG platform for medical knowledge. Retrieves from StatPearls (301k clinical chunks) in Qdrant, answers questions via multiple LLMs (user picks: BioMistral local, Gemini Flash, or GPT-4o), evaluated on MedMCQA.

**Two LangGraph agents** orchestrate the system. **Two MCP servers** expose tools externally. A **React chatbot frontend** lets users query, select models, and see cited answers.

**POC proof:** >62% accuracy on 150 MedMCQA questions vs ~52% baseline = +10pp delta.

---

## Architecture

```
┌─────────────────── REACT FRONTEND (Vite + TailwindCSS) ───────────────────┐
│  Model selector (BioMistral / Gemini Flash / GPT-4o) · Chat UI · Sources  │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │ REST + WebSocket
┌────────────────────────────────▼───────────────────────────────────────────┐
│                    FASTAPI BACKEND (:8000)                                  │
│  POST /query · POST /ingest · GET /health · WS /ws/chat                    │
│  Exposes 2 MCP servers (medical_search + citation_lookup)                  │
├────────────────────────────────────────────────────────────────────────────┤
│  AGENT 1 — RAG Orchestrator (LangGraph ReAct)                              │
│    query_transform → hybrid_search → rerank → crag_gate → generate         │
│  AGENT 2 — Evaluator Agent (LangGraph)                                     │
│    runs MedMCQA benchmark, compares models, reports accuracy               │
├────────────────────────────────────────────────────────────────────────────┤
│  MCP SERVER 1 — medical_search: search Qdrant, return ranked chunks        │
│  MCP SERVER 2 — citation_lookup: fetch StatPearls source by doc_id         │
├────────────────────────────────────────────────────────────────────────────┤
│  LLM ROUTER (LangChain)                                                    │
│    "biomistral"  → llama.cpp OpenAI-compat API (:8080)                     │
│    "gemini"      → ChatGoogleGenerativeAI(model="gemini-2.5-flash")        │
│    "gpt4o"       → ChatOpenAI(model="gpt-4o")                              │
├──────────────────────┬─────────────────────┬──────────────────────────────┤
│  QDRANT (:6333)      │  LLAMA.CPP (:8080)  │  POSTGRES (:5432) (Langfuse) │
│  dense+sparse vectors│  BioMistral Q4_K_M  │  optional observability       │
└──────────────────────┴─────────────────────┴──────────────────────────────┘
```

**Pipeline:** Ingest → Embed (PubMedBERT dense + BM25 sparse) → Qdrant → HyDE + multi-query → Hybrid RRF → MiniLM reranker → CRAG gate → Lost-in-middle assembly → LLM generation → Cited response

---

## Repository structure

```
medical-rag/
├── CLAUDE.md
├── docker-compose.yml              # ALL services: qdrant, api, llama-cpp, frontend, postgres
├── Dockerfile                       # FastAPI backend
├── Dockerfile.frontend              # React frontend (Vite build)
├── .env.example
├── requirements.txt
├── data/
│   └── statpearls_chunks.jsonl      # 301k chunks (gitignored, see setup)
├── models/
│   └── BioMistral-7B.Q4_K_M.gguf   # ~4.5GB (gitignored, see setup)
├── ingestion/
│   ├── loaders/statpearls_loader.py
│   ├── embedders/dense_embedder.py  # PubMedBERT via sentence-transformers
│   ├── embedders/sparse_embedder.py # BM25 sparse vectors
│   └── pipeline.py                  # load → embed → upsert to Qdrant
├── retrieval/
│   ├── qdrant_client.py
│   ├── hybrid_retriever.py          # dense + sparse + RRF fusion
│   ├── reranker.py                  # cross-encoder/ms-marco-MiniLM-L-6-v2 (local)
│   ├── query_transform/
│   │   ├── hyde.py                  # hypothetical document embedding
│   │   └── multi_query.py           # 3 LLM-generated rephrasings
│   ├── crag.py                      # confidence gate → refuse if score < 0.6
│   └── context_assembler.py         # dedup + lost-in-middle reorder + citations
├── generation/
│   ├── llm_router.py                # IMPORTANT: LangChain LLM factory for all 3 models
│   ├── prompts/
│   │   ├── clinical_qa.txt
│   │   └── cot_medical.txt
│   └── generator.py                 # LangChain LCEL chain: prompt | llm | parser
├── agents/
│   ├── rag_agent.py                 # AGENT 1: LangGraph ReAct — full RAG orchestration
│   ├── eval_agent.py                # AGENT 2: LangGraph — benchmark runner + model comparison
│   └── tools.py                     # LangChain @tool wrappers for retrieval, rerank, generate
├── mcp_servers/
│   ├── medical_search_server.py     # MCP 1: exposes hybrid_search + rerank as MCP tools
│   └── citation_lookup_server.py    # MCP 2: exposes source lookup by doc_id
├── api/
│   ├── main.py                      # FastAPI app with lifespan, CORS for React
│   ├── routers/query.py             # POST /query — calls RAG agent
│   ├── routers/ingest.py            # POST /ingest — trigger pipeline
│   ├── routers/health.py            # GET /health
│   ├── routers/ws.py                # WebSocket /ws/chat — streaming responses
│   └── schemas.py                   # Pydantic models
├── evaluation/
│   ├── poc_benchmark.py             # 150-question MedMCQA eval
│   ├── ragas_eval.py                # faithfulness + relevancy
│   └── datasets/medmcqa.py          # HuggingFace loader
├── frontend/                        # React app (Vite + TailwindCSS)
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx                  # Main chat interface
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx       # Message list + streaming
│   │   │   ├── ModelSelector.jsx    # Dropdown: BioMistral / Gemini / GPT-4o
│   │   │   ├── SourcePanel.jsx      # Expandable citations sidebar
│   │   │   └── MessageBubble.jsx
│   │   └── api/client.js            # Axios + WebSocket hooks
│   └── Dockerfile                   # Multi-stage: npm build → nginx
└── tests/
    ├── test_ingestion.py
    ├── test_retrieval.py
    ├── test_agents.py
    └── test_api.py
```

---

## Docker Compose — ALL services

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["qdrant_storage:/qdrant/storage"]

  llama-cpp:
    image: ghcr.io/ggerganov/llama.cpp:server
    ports: ["8080:8080"]
    volumes: ["./models:/models"]
    command: >
      --model /models/BioMistral-7B.Q4_K_M.gguf
      --host 0.0.0.0 --port 8080
      --ctx-size 4096 --threads 4 --cont-batching
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s

  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [qdrant, llama-cpp]
    env_file: .env
    volumes: ["./data:/app/data", "./models:/app/models"]

  frontend:
    build: { context: ./frontend, dockerfile: Dockerfile }
    ports: ["3000:80"]
    depends_on: [api]

  postgres:
    image: postgres:15
    environment: { POSTGRES_DB: langfuse, POSTGRES_USER: langfuse, POSTGRES_PASSWORD: langfuse }
    volumes: ["pg_data:/var/lib/postgresql/data"]

volumes:
  qdrant_storage:
  pg_data:
```

IMPORTANT: llama.cpp serves an **OpenAI-compatible API** at `:8080/v1`. LangChain connects via `ChatOpenAI(base_url="http://llama-cpp:8080/v1", api_key="not-needed")`.

---

## Environment variables (.env)

```bash
QDRANT_HOST=qdrant
QDRANT_PORT=6333
DENSE_MODEL=pritamdeka/PubMedBERT-mnli-snli-scinli-scitail-mednli-stsb
OPENAI_API_KEY=                    # GPT-4o
GOOGLE_API_KEY=                    # Gemini 2.5 Flash (free tier: 15 RPM)
BIOMISTRAL_URL=http://llama-cpp:8080/v1
CRAG_CONFIDENCE_THRESHOLD=0.60
```

---

## LLM Router — CRITICAL

```python
# generation/llm_router.py — ALL LLM access goes through here
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm(model_name: str):
    if model_name == "biomistral":
        return ChatOpenAI(base_url=os.getenv("BIOMISTRAL_URL"),
                          api_key="not-needed", model="biomistral",
                          temperature=0.0, max_tokens=1024)
    elif model_name == "gemini":
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0,
                                       google_api_key=os.getenv("GOOGLE_API_KEY"))
    elif model_name == "gpt4o":
        return ChatOpenAI(model="gpt-4o", temperature=0.0)
    raise ValueError(f"Unknown model: {model_name}")
```

---

## Agents (LangGraph)

**Agent 1 — RAG Orchestrator** (`agents/rag_agent.py`): LangGraph ReAct with tools: `search_qdrant`, `rerank_results`, `generate_answer`. Receives question + model choice → runs full pipeline as a state graph. Uses `StateGraph` + `MessagesState` + `ToolNode`.

**Agent 2 — Evaluator** (`agents/eval_agent.py`): LangGraph agent with tools: `load_medmcqa_sample`, `run_rag_query`, `compute_accuracy`. Compares all 3 models on same questions. Outputs accuracy table.

---

## MCP Servers

**MCP 1 — medical_search** (`:9001/mcp`): exposes `search(query, top_k, filters)` → ranked chunks.
**MCP 2 — citation_lookup** (`:9002/mcp`): exposes `lookup(doc_id)` → full article text + metadata.

Use `fastmcp` package. Connect from LangChain via `langchain-mcp-adapters`:
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
client = MultiServerMCPClient({
    "medical_search": {"url": "http://localhost:9001/mcp", "transport": "http"},
    "citation_lookup": {"url": "http://localhost:9002/mcp", "transport": "http"},
})
```

---

## Setup (run once)

```bash
git clone https://github.com/Teddy-XiongGZ/MedRAG.git
wget https://ftp.ncbi.nlm.nih.gov/pub/litarch/3d/12/statpearls_NBK430685.tar.gz -P MedRAG/corpus/statpearls
tar -xzvf MedRAG/corpus/statpearls/statpearls_NBK430685.tar.gz -C MedRAG/corpus/statpearls
cd MedRAG && python src/data/statpearls.py && cd ..
cp MedRAG/corpus/statpearls/chunks.jsonl data/statpearls_chunks.jsonl
wget https://huggingface.co/BioMistral/BioMistral-7B-GGUF/resolve/main/BioMistral-7B.Q4_K_M.gguf -P models/
docker compose up -d && docker compose exec api python -m ingestion.pipeline
```

---

## Implementation sprints

**Sprint 1 (today):** `docker-compose.yml` all 5 services up. `llm_router.py` — verify 3 LLMs respond. `statpearls_loader.py` + `dense_embedder.py` → 5k chunks in Qdrant. 20-question smoke test.

**Sprint 2 (tonight):** `sparse_embedder.py` + full 301k ingestion. `hybrid_retriever.py` (RRF k=60). `reranker.py` (MiniLM). `crag.py` + `context_assembler.py`. 50-question eval.

**Sprint 3 (tomorrow AM):** Both LangGraph agents + `@tool` wrappers. Both MCP servers. `generator.py` LCEL chain. HyDE + multi-query.

**Sprint 4 (tomorrow PM):** React frontend + WebSocket streaming. Full 150-question benchmark. Results table.

---

## Critical rules

- **LangChain everywhere**: ALL LLM calls via LangChain. ALL chains use LCEL. ALL agents use LangGraph.
- **llama.cpp OpenAI-compat**: `ChatOpenAI(base_url=..., api_key="not-needed")`. Do NOT use `llama-cpp-python`.
- **Gemini**: `langchain-google-genai` package, `model="gemini-2.5-flash"`.
- **Qdrant**: ONE collection `medical_rag`, named vectors `dense` (768-dim cosine) + sparse `sparse`.
- **Sparse vector format**: `SparseVector(indices=[int,...], values=[float,...])`.
- **RRF**: `score = sum(1/(rank + 60))`. **Lost-in-middle**: best→index 0, 2nd-best→index -1.
- **StatPearls fields**: `content`→dense, `contents`→sparse, `title`→metadata.
- **MedMCQA**: `cop` maps 0→A, 1→B, 2→C, 3→D.
- **Docker networking**: services use names (`qdrant`, `llama-cpp`), NOT `localhost`.
- **CORS**: `allow_origins=["http://localhost:3000"]` for React frontend.
- **MCP**: `fastmcp` package, Streamable HTTP transport.
- **Citations**: format chunks as `[N] Source: statpearls | Title: ...` so LLM cites `[N]`.

---

## Dependencies (requirements.txt)

```
langchain langchain-openai langchain-google-genai langchain-community
langgraph langchain-mcp-adapters
sentence-transformers qdrant-client>=1.9.0
fastapi uvicorn[standard] websockets
ragas>=0.1.0 datasets cross-encoder
fastmcp python-dotenv pydantic
```

---

## Eval targets

```
Baseline (no RAG):     ~50–55%  |  Hybrid + rerank: >65%
Dense-only:            ~58–62%  |  + HyDE/multi-query: >67%
```

BioMistral will score lower than GPT-4o/Gemini — expected for a 7B local model.

---

## When compacting, preserve

Current sprint, files done vs TODO, accuracy numbers, Docker service status, active bugs.
