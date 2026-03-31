# CLAUDE.md — Medical RAG Platform (DocRAG-MD)

> **Stack:** Python 3.11 · uv · LangChain LCEL · LangGraph ·
> Qdrant · FastAPI · llama.cpp · Docker Compose · React + Vite
> **LLMs:** BioMistral-7B (local llama.cpp) · Gemini 2.5 Flash
> (API) · GPT-4o (API)
> **Package manager:** uv + pyproject.toml — JAMAIS pip

---

## Ce que c'est

Plateforme RAG medicale. Recherche dans StatPearls (301k chunks)
via Qdrant, traverse un Knowledge Graph construit depuis StatPearls
(co-mentions de titres + classification de relations par regex),
et propose un Deep Search sur PubMed (36M+ articles).

L'utilisateur choisit le LLM (BioMistral local / Gemini / GPT-4o)
et le mode de recherche (RAG local / Deep Search PubMed).

**4 agents LangGraph** via un orchestrateur.
**2 serveurs MCP** (medical_search + citation_lookup).
**Frontend React** avec selecteurs modele et mode.

**3 plus-values :**
1. **Multi-agent** : orchestrateur classifie l'intention → route
   vers diagnostic, pharmacologie, ou general
2. **Self-RAG** : apres generation, verifie fidelite + completude,
   reformule si echec (max 2 retries)
3. **GraphRAG** : KG construit depuis StatPearls (co-mentions de
   titres, relations classifiees par regex, cache pickle)

**POC :** >62% accuracy sur 150 MedMCQA vs ~52% baseline.

---

## Architecture

```
Frontend React (:3000)
  ModelSelector (BioMistral / Gemini / GPT-4o)
  ModeSelector (RAG / Deep Search)
  | WebSocket + REST
FastAPI (:8000)
  |
Orchestrateur (LangGraph StateGraph)
  classify_intent → route
  |→ Agent diagnostic (symptomes, raisonnement clinique)
  |→ Agent pharmacologie (medicaments, interactions)
  |→ Agent general (QA medicale standard)
  |→ Agent evaluateur (benchmark MedMCQA)
  |
Pipeline dans chaque agent specialise :
  query_transform (HyDE)
  → Mode RAG : Qdrant hybrid (PubMedBERT + BM25 + RRF)
              + graph_search (KG StatPearls)
  → Mode Deep Search : PubMed E-utilities
  → rerank (MiniLM-L-6-v2)
  → CRAG gate (seuil > 0.6)
  → context assembly (dedup + lost-in-middle + citations)
  → generate (LLM choisi)
  → self_reflect (fidele ? complete ? → retry ou output)
  |
LLM Router :
  "biomistral" → ChatOpenAI(base_url="http://llama-cpp:8080/v1",
                             api_key="not-needed")
  "gemini"     → ChatGoogleGenerativeAI(model="gemini-2.5-flash")
  "gpt4o"      → ChatOpenAI(model="gpt-4o")
  |
MCP : medical_search (:9001) + citation_lookup (:9002)
```

---

## Docker Compose — 5+ services

```
qdrant         :6333   Vector DB
llama-cpp      :8080   BioMistral-7B Q4_K_M (local)
api            :8000   FastAPI backend
frontend       :3000   React + nginx
postgres       :5432   Langfuse
clickhouse              Langfuse analytics
minio                   Langfuse storage
```

---

## Variables d'environnement (.env)

```bash
QDRANT_HOST=qdrant
QDRANT_PORT=6333
COLLECTION_NAME=medical_rag
DENSE_MODEL=pritamdeka/PubMedBERT-mnli-snli-scinli-scitail-mednli-stsb
BIOMISTRAL_URL=http://llama-cpp:8080/v1
GOOGLE_API_KEY=         # Gemini 2.5 Flash
OPENAI_API_KEY=         # GPT-4o
CRAG_CONFIDENCE_THRESHOLD=0.60
SELF_RAG_MAX_RETRIES=2
```

---

## Knowledge Graph — PrimeKG

```python
# retrieval/knowledge_graph.py
# Source : PrimeKG (Harvard Dataverse) — data/kg.csv
# 100k+ noeuds (disease, drug, gene/protein, phenotype, etc.)
# 4M+ aretes, 29 types de relations
# Filtre medical : indication, contraindication, off-label use,
#   drug_drug, drug_effect, disease_phenotype_positive/negative,
#   disease_disease, disease_protein
# Cache pickle : data/kg_cache.pkl
# Charge dans lifespan : app.state.kg = load_kg()
```

PrimeKG telecharge par `download_data.sh` ou `scripts/download_all.py`.

---

## Self-RAG

```python
# retrieval/self_reflect.py
# Apres generation : verifie fidelite + completude via LLM
# JSON : {"faithful": bool, "complete": bool, "reason": str}
# Si echec → reformule avec reason → relance (max 2)
# Noeud conditional_edge dans StateGraph de chaque agent
```

---

## Deep Search — PubMed E-utilities

```python
# retrieval/deep_search.py
# esearch → IDs, esummary → metadata, efetch → abstracts
# 36M+ articles, gratuit, 3 req/s sans cle
# Active quand mode = "deep_search"
```

---

## Regles critiques

- **uv** : `uv add` pour dependances. JAMAIS `pip install`.
- **LangChain LCEL** : toutes les chains `prompt | llm | parser`.
- **LangGraph StateGraph** : tous les agents.
- **llama.cpp** : `ChatOpenAI(base_url=..., api_key="not-needed")`.
  JAMAIS `llama-cpp-python`.
- **Qdrant** : collection `medical_rag`, vecteurs nommes `dense`
  (768-dim) + `sparse`.
- **Docker** : services par NOM (`qdrant`, `llama-cpp`), PAS
  `localhost`.
- **KG** : PrimeKG (Harvard Dataverse), cache pickle. data/kg.csv.
- **Self-RAG** : max 2 retries.
- **Citations** : `[N] Source: statpearls | Title: ...`.
- **MCP** : `fastmcp`, Streamable HTTP.
- **MedMCQA** : `cop` maps 0→A, 1→B, 2→C, 3→D.
- **Frontend** : model + mode dans le body des requetes.

---

## Fichiers cles (modifies/crees)

| Fichier                          | Role                              |
|:---------------------------------|:----------------------------------|
| `generation/llm_router.py`       | Factory 3 LLMs                   |
| `retrieval/knowledge_graph.py`   | KG StatPearls + cache pickle     |
| `retrieval/self_reflect.py`      | Boucle fidelite/completude       |
| `retrieval/deep_search.py`       | PubMed E-utilities               |
| `agents/orchestrator.py`         | Classifie + route                |
| `agents/diagnosis_agent.py`      | Specialise diagnostic            |
| `agents/pharmacology_agent.py`   | Specialise pharmacologie         |
| `agents/general_agent.py`        | RAG standard + self-reflect      |
| `agents/tools.py`                | @tool wrappers (graph, pubmed)   |
| `api/schemas.py`                 | model + mode dans le schema      |

## Fichiers existants NON modifies

`ingestion/`, `retrieval/hybrid_retriever.py`,
`retrieval/reranker.py`, `retrieval/crag.py`,
`retrieval/context_assembler.py`, `retrieval/query_transform/`,
`mcp_servers/`, `tests/`, `evaluation/`,
`generation/generator.py`, `generation/prompts/`,
`agents/rag_agent.py`, `agents/eval_agent.py`

---

## When compacting, preserve

Current sprint, fichiers done vs TODO, accuracy numbers,
Docker service status, active bugs, KG node/edge count.
