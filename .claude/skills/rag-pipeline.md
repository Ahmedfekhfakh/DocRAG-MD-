# Skill : RAG Pipeline

Expert en retrieval, ingestion, et generation pour le Medical RAG.

## Scope
Tout travail dans `retrieval/`, `ingestion/`, `generation/`.

## Regles
- Embeddings : sentence-transformers + PubMedBERT 768-dim
- Qdrant collection `medical_rag` : vecteurs nommes `dense` + `sparse`
- Sparse format : `SparseVector(indices=[int,...], values=[float,...])`
- Hybrid search : dense + sparse → RRF fusion (k=60)
- Reranking : `cross-encoder/ms-marco-MiniLM-L-6-v2` (22M, CPU)
- CRAG gate : seuil sigmoid > 0.60, sinon refuse
- Context assembly : dedup + lost-in-middle reorder
  (best→index 0, 2nd-best→index -1)
- Citations : `[N] Source: statpearls | Title: ...`
- StatPearls fields : `content`→dense, `contents`→sparse, `title`→metadata

## KG StatPearls (retrieval/knowledge_graph.py)
- Noeuds = titres d'articles StatPearls
- Aretes = co-mentions (titre A apparait dans contenu de B)
- Relations classifiees par regex : treatment, causes, symptom,
  diagnosis, contraindication, complication, associated
- Cache pickle : `data/kg_cache.pkl`
- Charge dans lifespan FastAPI : `app.state.kg = load_kg()`
- Query : `query_graph(G, entity, relation_filter=None)`
- NE PAS utiliser PrimeKG. Le KG est construit depuis StatPearls.

## Deep Search (retrieval/deep_search.py)
- PubMed E-utilities : esearch → esummary → efetch
- 36M+ articles, gratuit, 3 req/s sans cle
- Retourne : PMID, titre, auteurs, journal, date, abstract
- Active quand mode = "deep_search" dans la requete

## Self-RAG (retrieval/self_reflect.py)
- Apres generation : prompt verifie fidelite + completude
- Reponse JSON : `{"faithful": bool, "complete": bool, "reason": str}`
- Si echec → rajouter reason au contexte → relancer le pipeline
- Max 2 retries via compteur dans le state de l'agent
