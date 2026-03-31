# Skill : Testing & Evaluation

Expert en tests et benchmark du Medical RAG.

## Scope
`tests/`, `evaluation/`.

## Regles
- Package manager : `uv run pytest tests/ -v`
- 37 tests existants doivent TOUJOURS passer
- Nouveaux tests pour : knowledge_graph, self_reflect,
  orchestrator, deep_search, llm_router
- Benchmark : 150 questions MedMCQA
- Evaluation : RAGAS (faithfulness + relevancy)
- MedMCQA : `cop` maps 0→A, 1→B, 2→C, 3→D

## Targets
```
Baseline (no RAG):     ~50-55%
Dense-only:            ~58-62%
Hybrid + rerank:       >65%
+ Self-RAG + agents:   >67%
```

## Commandes
```bash
uv run pytest tests/ -v
uv run python -m evaluation.poc_benchmark
```
