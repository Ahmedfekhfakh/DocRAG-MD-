"""Knowledge Graph médical — PrimeKG (Precision Medicine Knowledge Graph).

Source : Harvard Dataverse — 4M+ arêtes, 100k+ noeuds, 29 types de relations.
Fichier : data/kg.csv (téléchargé par download_data.sh)

Colonnes CSV : relation, display_relation, x_index, x_id, x_type, x_name,
               x_source, y_index, y_id, y_type, y_name, y_source

Cache pickle pour éviter de recharger le CSV à chaque démarrage.
"""
import csv
import pickle
import logging
from pathlib import Path

import networkx as nx

log = logging.getLogger(__name__)

CACHE_PATH = Path("data/kg_cache.pkl")
PRIMEKG_PATH = Path("data/kg.csv")

# Relations pertinentes pour le RAG médical (ignore protein_protein, etc.)
MEDICAL_RELATIONS = {
    "indication", "contraindication", "off-label use",
    "drug_drug", "drug_effect",
    "disease_phenotype_positive", "disease_phenotype_negative",
    "disease_disease", "disease_protein",
}


def build_kg_from_primekg(csv_path: str | Path = PRIMEKG_PATH) -> nx.MultiGraph:
    """Charge PrimeKG depuis le CSV et construit un NetworkX MultiGraph.

    Filtre uniquement les relations médicalement pertinentes pour garder
    un graphe de taille raisonnable en mémoire.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        log.warning("PrimeKG introuvable : %s", csv_path)
        return nx.MultiGraph()

    log.info("Chargement de PrimeKG depuis %s ...", csv_path)
    G = nx.MultiGraph()
    edge_count = 0

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            relation = row.get("relation", "")
            if relation not in MEDICAL_RELATIONS:
                continue

            x_name = row.get("x_name", "").strip()
            y_name = row.get("y_name", "").strip()
            if not x_name or not y_name:
                continue

            x_type = row.get("x_type", "unknown")
            y_type = row.get("y_type", "unknown")

            if not G.has_node(x_name):
                G.add_node(x_name, type=x_type)
            if not G.has_node(y_name):
                G.add_node(y_name, type=y_type)

            G.add_edge(
                x_name, y_name,
                relation=relation,
                display_relation=row.get("display_relation", relation),
                x_type=x_type,
                y_type=y_type,
                weight=1,
            )
            edge_count += 1

            if edge_count % 500_000 == 0:
                log.info("  %d arêtes chargées ...", edge_count)

    log.info("PrimeKG chargé : %d noeuds, %d arêtes",
             G.number_of_nodes(), G.number_of_edges())
    return G


def load_kg(
    csv_path: str | Path = PRIMEKG_PATH,
    cache_path: str | Path = CACHE_PATH,
) -> nx.MultiGraph:
    """Charge le KG depuis le cache ou le construit depuis PrimeKG."""
    cache_path = Path(cache_path)
    csv_path = Path(csv_path)

    if cache_path.exists():
        if not csv_path.exists() or cache_path.stat().st_mtime > csv_path.stat().st_mtime:
            log.info("Chargement du KG depuis le cache : %s", cache_path)
            with cache_path.open("rb") as f:
                return pickle.load(f)
        log.info("Cache obsolète, reconstruction...")

    G = build_kg_from_primekg(csv_path)
    if G.number_of_nodes() > 0:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("wb") as f:
            pickle.dump(G, f)
        log.info("KG sauvegardé en cache : %s", cache_path)
    return G


async def extract_medical_terms(question: str, model_name: str = "gemini", config=None) -> list[str]:
    """Extract medical entities from a question using the LLM."""
    from langchain_core.prompts import ChatPromptTemplate
    from generation.llm_router import get_llm

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract the medical entity names from the question. "
         "Return ONLY a comma-separated list of medical terms (diseases, drugs, symptoms). "
         "Example: 'systemic lupus erythematosus, metformin, seizure'"),
        ("human", "{question}"),
    ])
    llm = get_llm(model_name)
    chain = prompt | llm
    invoke_config = dict(config) if config else {}
    invoke_config["run_name"] = "2_extract_entities"
    result = await chain.ainvoke({"question": question}, config=invoke_config)
    terms = [t.strip() for t in result.content.split(",") if t.strip()]
    return terms


def _clean_node_name(name: str) -> str:
    """Strip parenthetical suffixes like '(disease)' for matching."""
    import re
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def query_graph(
    G: nx.MultiGraph,
    entity: str,
    relation_filter: str | None = None,
) -> list[dict]:
    """Cherche les voisins d'une entité médicale dans PrimeKG."""
    entity_lower = entity.lower()
    matched = [
        n for n in G.nodes()
        if entity_lower in n.lower()
        or (len(n) >= 4 and _clean_node_name(n).lower() in entity_lower)
    ]
    if not matched:
        return []
    results = []
    for node in matched:
        for neighbor in G.neighbors(node):
            for _key, edge_data in G[node][neighbor].items():
                rel = edge_data.get("relation", "")
                if relation_filter and rel != relation_filter:
                    continue
                results.append({
                    "entity": neighbor,
                    "relation": edge_data.get("display_relation", rel),
                    "type": edge_data.get("y_type", "unknown"),
                    "weight": edge_data.get("weight", 1),
                })
    results.sort(key=lambda r: r.get("weight", 0), reverse=True)
    return results
