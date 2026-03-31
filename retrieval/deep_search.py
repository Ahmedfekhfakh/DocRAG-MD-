"""Deep Search — Recherche web via PubMed E-utilities API.

API gratuite, 3 req/s sans clé, 10 req/s avec clé NCBI.
Accès à 36M+ articles médicaux peer-reviewed.
"""
import requests
import xml.etree.ElementTree as ET


def search_pubmed(query: str, max_results: int = 10) -> list[dict]:
    """Cherche des articles sur PubMed et retourne les résumés."""
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
    }
    resp = requests.get(search_url, params=params, timeout=10)
    ids = resp.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "json",
    }
    summary = requests.get(summary_url, params=params, timeout=10).json()

    results = []
    for pmid in ids:
        paper = summary.get("result", {}).get(pmid, {})
        if not paper or pmid == "uids":
            continue
        authors = [a.get("name", "") for a in paper.get("authors", [])[:3]]
        results.append({
            "pmid": pmid,
            "title": paper.get("title", ""),
            "authors": ", ".join(authors),
            "journal": paper.get("fulljournalname", ""),
            "date": paper.get("pubdate", ""),
            "source": "pubmed",
        })
    return results


def fetch_abstracts(pmids: list[str]) -> dict[str, str]:
    """Récupère les abstracts pour une liste de PMIDs."""
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    resp = requests.get(fetch_url, params=params, timeout=15)
    root = ET.fromstring(resp.text)
    abstracts = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        abstract_el = article.find(".//AbstractText")
        if pmid_el is not None and abstract_el is not None:
            abstracts[pmid_el.text] = abstract_el.text or ""
    return abstracts
