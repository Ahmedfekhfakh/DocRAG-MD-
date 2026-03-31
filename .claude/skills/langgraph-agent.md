# Skill : LangGraph Agent

Expert en agents LangGraph pour l'orchestration multi-agent.

## Scope
Tout travail dans `agents/`.

## Architecture multi-agent
```
Orchestrateur (classify_intent → route)
  |→ diagnosis_agent  (symptomes, raisonnement clinique)
  |→ pharmacology_agent (medicaments, interactions)
  |→ general_agent (QA medicale)
  |→ eval_agent (benchmark MedMCQA)
```

## Regles
- TOUS les agents : `StateGraph` + `TypedDict` ou `MessagesState`
- Orchestrateur : classifie via LLM → route par conditional_edges
- Chaque agent specialise a les noeuds :
  query_transform → search → graph_search → rerank →
  assemble → generate → self_reflect
- Self-reflect : conditional_edge → retry (max 2) ou END
- L'evaluateur N'a PAS de self_reflect
- Outils partages via `@tool` dans `agents/tools.py`

## Outils disponibles (@tool)
- `search_qdrant(query, top_k)` → hybrid search Qdrant
- `rerank_results(query, chunks)` → MiniLM reranker
- `search_knowledge_graph(entity)` → KG StatPearls
- `deep_search_pubmed(query)` → PubMed E-utilities
- `generate_answer(question, context, model)` → LLM via router

## Classification de l'orchestrateur
```python
CLASSIFY_PROMPT → categories :
  DIAGNOSTIC → symptomes, diagnostic differentiel
  PHARMACOLOGIE → medicaments, interactions, contre-indications
  GENERAL → toute autre question medicale
  BENCHMARK → evaluation / benchmark
```

## Patterns
```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))
graph.add_node("self_reflect", check_and_retry)
graph.add_conditional_edges("self_reflect", retry_or_end,
    {"retry": "agent", "end": END})
```
