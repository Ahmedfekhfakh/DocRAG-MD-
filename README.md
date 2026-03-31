<div align="center">
  <img src="docs/logo.jpeg" alt="DocRAG-MD" width="280" style="border-radius:16px; margin-bottom:16px"/>
  <h1>DocRAG-MD — Multi-Agent Medical RAG Platform</h1>
  <p><b>Production-grade clinical Q&A with multi-agent routing, GraphRAG, Self-RAG, and PubMed Deep Search over 301k StatPearls chunks</b></p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
    <img src="https://img.shields.io/badge/LangChain-0.3-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white"/>
    <img src="https://img.shields.io/badge/LangGraph-0.2-FF6F00?style=for-the-badge&logo=langchain&logoColor=white"/>
    <img src="https://img.shields.io/badge/Qdrant-latest-DC382D?style=for-the-badge&logo=qdrant&logoColor=white"/>
    <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black"/>
    <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
    <img src="https://img.shields.io/badge/Langfuse-v3-4F46E5?style=for-the-badge&logoColor=white"/>
  </p>
</div>

---

## 📸 Screenshots

<div align="center">

### Authentication
<p float="left">
  <img src="docs/screenshots/signup.png" alt="Sign Up" width="48%"/>
  <img src="docs/screenshots/login.png" alt="Login" width="48%"/>
</p>

### Chat Interface
<p float="left">
  <img src="docs/screenshots/chat_patient_light.png" alt="Patient mode (light)" width="48%"/>
  <img src="docs/screenshots/chat_doctor_sombre.png" alt="Doctor mode (dark)" width="48%"/>
</p>

### Langfuse Observability
<p float="left">
  <img src="docs/screenshots/langfuse_traces.jpeg" alt="Langfuse traces" width="48%"/>
  <img src="docs/screenshots/langfuse_home.jpeg" alt="Langfuse dashboard" width="48%"/>
</p>
<p align="center">
  <img src="docs/screenshots/langfuse_llama_cpp.jpeg" alt="Langfuse BioMistral trace" width="60%"/>
</p>

</div>

---

## 📋 About

DocRAG-MD is a multi-agent Retrieval-Augmented Generation platform for clinical question answering. An LLM-based orchestrator classifies user intent and routes queries to four specialized LangGraph agents — **diagnosis**, **pharmacology**, **general medical QA**, and **benchmark evaluation**. Users choose between three LLMs (Gemini 2.5 Flash, BioMistral 7B local, GPT-4o) and four search modes (RAG, Knowledge Graph, Hybrid, Deep Search PubMed). A role selector (patient / doctor) adapts the response style.

The platform introduces three key technical differentiators: **GraphRAG** enrichment via PrimeKG (Harvard Dataverse) — 100k+ nodes, 4M+ edges, 9 medical relation types filtered from 29 (NetworkX MultiGraph, pickle cache), **Self-RAG** post-generation verification that checks fidelity and completeness before returning answers (max 2 retries with query reformulation), and **CRAG** confidence gating with sigmoid-normalized reranker scores (threshold > 0.60).

DocRAG-MD achieves **62%+ accuracy on 150 MedMCQA validation questions** (vs ~52% baseline). The infrastructure runs as 11 Docker services with Langfuse v3 full observability (traces, spans, generations), 2 MCP servers for tool-augmented retrieval, and a React chat UI with model and mode selection.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **Multi-Agent Orchestrator** | LLM-based intent classification → routes to 4 specialized LangGraph agents (diagnostic, pharmacology, general, evaluator) |
| **GraphRAG** | PrimeKG (Harvard Dataverse) — 100k+ nodes, 4M+ edges, 9 medical relations (`indication`, `contraindication`, `off-label use`, `drug_drug`, `drug_effect`, `disease_phenotype_positive`, `disease_phenotype_negative`, `disease_disease`, `disease_protein`), NetworkX MultiGraph, pickle cache |
| **Self-RAG** | Post-generation fidelity + completeness check via LLM — auto-reformulates on failure (max 2 retries) |
| **Deep Search** | PubMed E-utilities API (36M+ peer-reviewed articles) — esearch → esummary → efetch abstracts |
| **Hybrid Retrieval** | Dense (PubMedBERT 768-dim cosine) + Sparse (BM25 TF-IDF) with Reciprocal Rank Fusion (k=60) |
| **CRAG Gate** | Sigmoid-normalized reranker scores — threshold > 0.60, prevents low-confidence generations |
| **HyDE** | Hypothetical Document Embeddings — generates synthetic passages for expanded query matching |
| **Lost-in-Middle** | Context reordering — best chunks at positions 0 and -1 to maximize LLM attention |
| **MCP Servers** | `medical_search` (:9001) + `citation_lookup` (:9002) via fastmcp Streamable HTTP |
| **Langfuse v3** | Full LLM observability — traces, spans, generations, with ClickHouse analytics and S3 storage |

---

## 🏗️ Architecture

### System Overview

<p align="center">
  <a href="https://excalidraw.com/#json=BU9NH1Lak05pmpxnunUQT,0UdIHI2jo8KaphhyOFzZMw">
    <img src="docs/diagrams/architecture.svg" alt="Architecture Overview" width="90%"/>
  </a>
</p>

<details>
<summary>Text version (click to expand)</summary>

```
┌────────────────────── REACT FRONTEND  :3000 ───────────────────────┐
│  Chat UI · ModelSelector (Gemini / BioMistral / GPT-4o)            │
│           ModeSelector  (RAG / Graph / Hybrid / Deep Search)       │
│           RoleSelector  (Patient / Doctor)                         │
└────────────────────────────┬───────────────────────────────────────┘
                             │ WebSocket + REST
┌────────────────────────────▼───────────────────────────────────────┐
│                    FASTAPI BACKEND  :8000                           │
│   /auth · /query · /ingest · /evaluate · /health · WS /ws/chat     │
├────────────────────────────────────────────────────────────────────┤
│  ORCHESTRATOR (LangGraph StateGraph)                                │
│    classify_intent → route_to_agent                                 │
│    ├─ DIAGNOSTIC      → Diagnosis Agent                             │
│    ├─ PHARMACOLOGIE   → Pharmacology Agent                          │
│    ├─ GENERAL         → General Agent                               │
│    └─ BENCHMARK       → Evaluator Agent                             │
├────────────────────────────────────────────────────────────────────┤
│  AGENT PIPELINE (per specialized agent)                             │
│    query_transform (HyDE)                                           │
│    → search: Qdrant hybrid (dense + sparse + RRF)                   │
│            | Deep Search (PubMed E-utilities)                       │
│    → graph_search: PrimeKG (diagnosis/pharmacology only)            │
│    → rerank (MiniLM-L-6-v2 cross-encoder)                          │
│    → CRAG gate (sigmoid > 0.60)                                     │
│    → context assembly (dedup + lost-in-middle + citations)          │
│    → generate (selected LLM)                                        │
│    → self_reflect (faithful? complete? → retry or output)           │
├────────────────────────────────────────────────────────────────────┤
│  LLM ROUTER                                                        │
│    biomistral → llama.cpp (:8080)                                   │
│    gemini     → Gemini 2.5 Flash (API)                              │
│    gpt4o      → GPT-4o (API)                                       │
├──────────────────────────────┬─────────────────────────────────────┤
│  MCP SERVERS                 │  OBSERVABILITY                      │
│  medical_search  :9001/mcp   │  Langfuse v3  :3001                 │
│  citation_lookup :9002/mcp   │  Postgres · ClickHouse · MinIO     │
└──────────────────────────────┴─────────────────────────────────────┘
```

</details>

### RAG Pipeline (per agent)

<p align="center">
  <a href="https://excalidraw.com/#json=ObhoU4gfAOFXWximmrGj2,kZc_Vj-KfSmFCPF3bYqzCw">
    <img src="docs/diagrams/rag_pipeline.svg" alt="RAG Pipeline" width="90%"/>
  </a>
</p>

**Flow:** Query → HyDE → Hybrid RRF (PubMedBERT dense + BM25 sparse) + GraphRAG (PrimeKG) → MiniLM rerank → CRAG gate → lost-in-middle assembly → LLM generation → Self-RAG reflection → cited response

---

## 🛠️ Tech Stack

| Component | Technology | Role |
|---|---|---|
| **Language** | Python 3.11 | Backend runtime |
| **Package Manager** | [uv](https://github.com/astral-sh/uv) + `pyproject.toml` | Dependency management |
| **LLMs** | Gemini 2.5 Flash · BioMistral 7B (Q4_K_M) · GPT-4o | Cloud + local inference |
| **LLM Framework** | LangChain LCEL + LangGraph | Chains and agent orchestration |
| **Vector DB** | Qdrant | Dense (768-dim cosine) + sparse (BM25) named vectors |
| **Embeddings** | PubMedBERT (`pritamdeka/PubMedBERT-mnli-snli-scinli-scitail-mednli-stsb`) | Biomedical dense embeddings |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder rescoring |
| **Knowledge Graph** | PrimeKG + NetworkX MultiGraph | 100k+ nodes, 4M+ edges, 9 medical relations, pickle cache |
| **API** | FastAPI + WebSocket | REST and streaming endpoints |
| **MCP** | fastmcp (Streamable HTTP) | Tool-augmented retrieval servers |
| **Frontend** | React 18 + Vite + TailwindCSS | Chat UI with model/mode selectors |
| **Observability** | Langfuse v3 | Traces, spans, cost tracking |
| **Infra** | Docker Compose (11 services) | Full-stack orchestration |

---

## 📊 Data Sources

| Source | Volume | Usage |
|---|---|---|
| **StatPearls** | 301k chunks | Primary knowledge base — ingested into Qdrant + used to build KG |
| **PubMed** | 36M+ articles | Deep Search mode — queried live via NCBI E-utilities API |
| **MedMCQA** | 194k questions | Evaluation benchmark (150 sampled for POC) |

---

## 🤖 Agents

<p align="center">
  <a href="https://excalidraw.com/#json=7eeqn6ZwMkJQX5zjvoAlv,KxCxg3mAqFmnNWqOjhPM7A">
    <img src="docs/diagrams/agent_routing.svg" alt="Agent Routing" width="85%"/>
  </a>
</p>

| Agent | Intent Trigger | Specialty | PrimeKG Relations |
|---|---|---|---|
| **Diagnosis** | `DIAGNOSTIC` | Symptoms, differential diagnosis, clinical decision trees | `disease_phenotype_positive`, `disease_disease` |
| **Pharmacology** | `PHARMACOLOGIE` | Drugs, interactions, contraindications, dosing | `contraindication`, `indication`, `drug_drug`, `off-label use` |
| **General** | `GENERAL` | Standard medical QA | All medical relations |
| **Evaluator** | `BENCHMARK` | MedMCQA accuracy reporting | N/A |

Each specialized agent runs the full pipeline: **query_transform → search → graph_search → rerank → CRAG gate → assemble → generate → self_reflect** with conditional retry (max 2).

---

## 🚀 Getting Started

**Prerequisites**
- Docker + Docker Compose
- GCP project with Vertex AI API enabled (recommended), or Gemini API key from [aistudio.google.com](https://aistudio.google.com)
- OpenAI API key (optional, for GPT-4o)

**Quick Start**

```bash
# 1. Clone the repository
git clone https://github.com/Ahmedfekhfakh/DocRAG-MD-.git
cd DocRAG-MD-

# 2. Configure environment
cp .env.example .env
# Edit .env: set GOOGLE_API_KEY=AIza...

# 3. Download StatPearls data + BioMistral model (~6 GB total)
bash download_data.sh          # Full dataset (~300k chunks) + BioMistral 7B GGUF
bash download_data.sh 5000     # Smoke test (5000 chunks) + BioMistral 7B GGUF

# 4. Start all services (first run builds the images)
docker compose up --build
```

On first run, Docker will start Qdrant, build the API, auto-ingest StatPearls into the vector DB, build the Knowledge Graph (cached as pickle), and serve the frontend. HuggingFace model weights are cached in a Docker volume.

**Frontend:** `http://localhost:3000` — **API docs:** `http://localhost:8000/docs`

**Manual Installation (no Docker for the app)**

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup environment
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e .

# Start Qdrant separately
docker run -d -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant

# Configure and run
export QDRANT_HOST=localhost GOOGLE_API_KEY=AIza...
bash download_data.sh 5000
python -m ingestion.pipeline
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 🔌 API Reference

**`GET /health`**

```json
{ "status": "ok", "qdrant": "ok", "version": "0.1.0" }
```

**`POST /auth/signup`**

```json
// Request
{
  "username": "john",
  "password": "secret",
  "role": "doctor"          // "patient" | "doctor"
}

// Response
{ "id": 1, "username": "john", "role": "doctor" }
```

**`POST /auth/login`**

```json
// Request
{ "username": "john", "password": "secret" }

// Response
{ "id": 1, "username": "john", "role": "doctor" }
```

**`POST /query`**

```json
// Request
{
  "question": "What are the first-line treatments for hypertension?",
  "model": "gemini",       // "gemini" | "biomistral" | "gpt4o"
  "mode": "rag",            // "rag" | "graph" | "hybrid" | "deep_search"
  "use_cot": false,
  "role": "doctor"          // "patient" | "doctor"
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

**`WS /ws/chat`**

```json
// Send
{ "question": "What is Type 2 diabetes?", "model": "gemini", "mode": "rag", "role": "doctor" }

// Receive
{ "type": "start", "model": "gemini" }
{ "type": "answer", "answer": "...", "sources": [...], "model": "gemini", "intent": "GENERAL" }
```

**`POST /ingest`**

```json
{ "limit": null }   // null = all chunks
```

**`POST /evaluate/ragas`**

```json
// Request
{
  "questions": ["What causes hypertension?", "What is metformin used for?"],
  "model": "gemini"         // "gemini" | "biomistral"
}

// Response
{
  "scores": { "faithfulness": 0.85, "answer_relevancy": 0.91 },
  "n_samples": 2,
  "model": "gemini",
  "langfuse_trace_id": "trace-abc123"
}
```

---

## 🧰 MCP Servers

| Server | Tool | Description |
|---|---|---|
| `medical_search` | `search(query, top_k)` | Hybrid dense+sparse search with cross-encoder reranking |
| `medical_search` | `search_and_rerank(query, top_k)` | Search with full rerank pipeline |
| `citation_lookup` | `lookup(doc_id)` | Fetch full article content by document ID |

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "medical_search": {"url": "http://localhost:9001/mcp", "transport": "http"},
    "citation_lookup": {"url": "http://localhost:9002/mcp", "transport": "http"},
})
```

---

## 🧪 Tests

```bash
uv run pytest tests/ -v
```

**37 / 37 passing** — covers API endpoints, agent pipelines, hybrid retrieval, reranking, ingestion, and generation.

---

## 📈 Benchmark

| Metric | Baseline | DocRAG-MD |
|---|---|---|
| **MedMCQA Accuracy** (150 questions) | ~52% | **62%+** |

Self-RAG retry improves accuracy by ~2-3% through fidelity and completeness checks on generated answers.

---

## ⚙️ Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | — | **Yes** | Gemini 2.5 Flash API key |
| `OPENAI_API_KEY` | — | No | GPT-4o API key |
| `BIOMISTRAL_URL` | `http://llama-cpp:8080/v1` | No | Local BioMistral endpoint |
| `QDRANT_HOST` | `qdrant` | No | Qdrant hostname (`localhost` for local dev) |
| `QDRANT_PORT` | `6333` | No | Qdrant port |
| `COLLECTION_NAME` | `medical_rag` | No | Qdrant collection name |
| `DENSE_DIM` | `768` | No | Dense vector dimensionality |
| `DENSE_MODEL` | `pritamdeka/PubMedBERT-...` | No | HuggingFace embedding model |
| `CRAG_CONFIDENCE_THRESHOLD` | `0.60` | No | Sigmoid score cutoff for CRAG gate |
| `LANGFUSE_PUBLIC_KEY` | — | No | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | — | No | Langfuse project secret key |
| `LANGFUSE_HOST` | `http://langfuse:3000` | No | Langfuse server URL |
| `DATABASE_URL` | `postgresql://langfuse:langfuse@postgres:5432/medrag` | No | PostgreSQL connection (auth) |
| `SELF_RAG_MAX_RETRIES` | `2` | No | Max self-reflection retry attempts |

---

## 🐳 Docker Services

| Service | Port | Role |
|---|---|---|
| `qdrant` | :6333 | Vector database (dense + sparse storage) |
| `llama-cpp` | :8080 | BioMistral 7B Q4_K_M local inference |
| `api` | :8000, :9001, :9002 | FastAPI backend + MCP servers |
| `frontend` | :3000 | React chat UI via nginx |
| `postgres` | :5432 | Langfuse metadata database |
| `clickhouse` | — | Langfuse analytics engine |
| `minio` | — | S3-compatible event storage |
| `minio-init` | — | Bootstrap: creates `langfuse-events` bucket |
| `redis` | — | Langfuse cache and background jobs |
| `langfuse` | :3001 | LLM observability UI |
| `langfuse-worker` | — | Background job processor |

---

## 📁 Project Structure

```
DocRAG-MD/
├── agents/                          # LangGraph agents
│   ├── orchestrator.py              # Intent classification + routing
│   ├── diagnosis_agent.py           # Specialized diagnostic agent
│   ├── pharmacology_agent.py        # Specialized pharmacology agent
│   ├── general_agent.py             # Standard RAG + Self-RAG
│   ├── eval_agent.py                # MedMCQA benchmark runner
│   └── tools.py                     # @tool wrappers (graph, pubmed, search)
├── retrieval/                       # Search & retrieval pipeline
│   ├── hybrid_retriever.py          # Dense + sparse RRF fusion
│   ├── reranker.py                  # Cross-encoder rescoring
│   ├── crag.py                      # Confidence gate
│   ├── context_assembler.py         # Dedup + lost-in-middle + citations
│   ├── knowledge_graph.py           # PrimeKG loader + cache pickle
│   ├── deep_search.py               # PubMed E-utilities integration
│   ├── self_reflect.py              # Fidelity + completeness checker
│   └── query_transform/             # HyDE + multi-query expansion
├── generation/                      # LLM chains
│   ├── llm_router.py                # Factory: Gemini / BioMistral / GPT-4o
│   ├── generator.py                 # LCEL prompt | llm | parser
│   ├── observability.py             # Langfuse integration
│   └── prompts/                     # clinical_qa.txt, cot_medical.txt
├── ingestion/                       # Data pipeline
│   ├── pipeline.py                  # Batch embed + upsert to Qdrant
│   ├── loaders/                     # StatPearls JSONL loader
│   └── embedders/                   # Dense (PubMedBERT) + sparse (BM25)
├── api/                             # FastAPI application
│   ├── main.py                      # App + lifespan (Qdrant + KG loading)
│   ├── schemas.py                   # Pydantic models
│   └── routers/                     # auth, query, ws, health, ingest, evaluate
├── mcp_servers/                     # MCP tool servers
│   ├── medical_search_server.py     # :9001 — search + rerank
│   └── citation_lookup_server.py    # :9002 — doc lookup
├── evaluation/                      # Benchmarking
│   ├── poc_benchmark.py             # MedMCQA runner
│   ├── ragas_eval.py                # RAGAS faithfulness + answer relevancy
│   └── datasets/medmcqa.py          # Dataset loader
├── frontend/src/                    # React application
│   ├── App.jsx                      # Main state + WebSocket
│   └── components/                  # ChatWindow, ModelSelector, ModeSelector, SourcePanel
├── tests/                           # 37 tests (pytest)
├── docker-compose.yml               # 11 services
├── Dockerfile                       # Python 3.11 slim + uv
└── pyproject.toml                   # Dependencies (uv)
```

---

## ❓ Troubleshooting

**Qdrant collection empty after startup**
```bash
docker compose exec api python -m ingestion.pipeline
```

**HuggingFace model re-downloads on every restart** — The `hf_cache` Docker volume persists weights. If it was just added, restart once:
```bash
docker compose down && docker compose up
```

**BioMistral GGUF not found** — Download the quantized model and place it in `models/`:
```bash
mkdir -p models/
# Download BioMistral-7B.Q4_K_M.gguf into models/
```

**Knowledge Graph cache stale** — Delete the pickle cache and restart:
```bash
rm -f data/kg_cache.pkl
docker compose restart api
```

**Langfuse not connecting** — Create a project at `http://localhost:3001`, then copy the public/secret keys into `.env`:
```bash
LANGFUSE_PUBLIC_KEY=pk_...
LANGFUSE_SECRET_KEY=sk_...
```

**Permission denied on data files**
```bash
sudo chown -R $USER:$USER data/
```

**Docker not found in WSL** — Open Docker Desktop → Settings → Resources → WSL Integration → enable your distro.

---

## 👥 Authors

| | Name | GitHub |
|---|---|---|
| 👨‍💻 | **Tahiana Andriambahoaka** | [@tahianahajanirina](https://github.com/tahianahajanirina) |
| 👨‍💻 | **Ahmed Fekhfakh** | [@Ahmedfekhfakh](https://github.com/Ahmedfekhfakh) |
| 👨‍💻 | **Oussama Rhouma** | [@oussama10rhouma](https://github.com/oussama10rhouma) |
| 👨‍💻 | **Mohamed Khalil Ounis** | [@AMATERASU11](https://github.com/AMATERASU11) |
| 👨‍💻 | **Mohamed Amar** | |

---

<p align="center">
  <strong>DocRAG-MD</strong><br>
  Multi-Agent Medical RAG Platform<br>
  StatPearls · PubMed · LangGraph · Qdrant
</p>
