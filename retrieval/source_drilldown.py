"""Source drilldown for Deep Search, with Qdrant-first and local fallback."""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from qdrant_client import models as qmodels

from ingestion.loaders.statpearls_loader import load_chunks
from retrieval.qdrant_client import get_qdrant_client

COLLECTION = os.getenv("COLLECTION_NAME", "medical_rag")
DATA_PATH = Path(os.getenv("DATA_PATH", "data/statpearls_chunks.jsonl"))

_docs_by_title: dict[str, list[dict]] | None = None


def _load_docs_by_title() -> dict[str, list[dict]]:
    global _docs_by_title
    if _docs_by_title is None:
        grouped: dict[str, list[dict]] = defaultdict(list)
        if DATA_PATH.exists():
            for doc in load_chunks(DATA_PATH):
                grouped[doc.get("title", "").strip()].append(doc)
        _docs_by_title = grouped
    return _docs_by_title


def _local_doc_to_result(doc: dict) -> dict:
    return {
        "doc_id": doc.get("id", doc.get("doc_id", "")),
        "title": doc.get("title", ""),
        "content": doc.get("content", doc.get("contents", "")),
        "source": doc.get("source", "statpearls"),
        "score": float(doc.get("score", 0.0)),
    }


def _local_drilldown(docs: list[dict], top_n: int = 3, per_source: int = 2) -> list[dict]:
    docs_by_title = _load_docs_by_title()
    seen = {doc.get("doc_id") for doc in docs if doc.get("doc_id")}
    expanded: list[dict] = []

    for doc in docs[:top_n]:
        title = doc.get("title", "").strip()
        if not title or title not in docs_by_title:
            continue
        added = 0
        for candidate in docs_by_title[title]:
            result = _local_doc_to_result(candidate)
            if result["doc_id"] in seen:
                continue
            seen.add(result["doc_id"])
            expanded.append(result)
            added += 1
            if added >= per_source:
                break
    return expanded


def drill_down_sources(docs: list[dict], top_n: int = 3, per_source: int = 2) -> list[dict]:
    if not docs:
        return []

    try:
        client = get_qdrant_client()
        seen = {doc.get("doc_id") for doc in docs if doc.get("doc_id")}
        expanded: list[dict] = []

        for doc in docs[:top_n]:
            title = doc.get("title", "").strip()
            if not title:
                continue

            records, _ = client.scroll(
                collection_name=COLLECTION,
                scroll_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="title",
                            match=qmodels.MatchValue(value=title),
                        )
                    ]
                ),
                with_payload=True,
                limit=per_source + 2,
            )

            added = 0
            for record in records:
                payload = record.payload or {}
                result = {
                    "doc_id": payload.get("doc_id", str(record.id)),
                    "title": payload.get("title", ""),
                    "content": payload.get("content", ""),
                    "source": payload.get("source", "statpearls"),
                    "score": float(getattr(record, "score", 0.0) or 0.0),
                }
                if result["doc_id"] in seen:
                    continue
                seen.add(result["doc_id"])
                expanded.append(result)
                added += 1
                if added >= per_source:
                    break

        if expanded:
            return expanded
    except Exception:
        pass

    return _local_drilldown(docs, top_n=top_n, per_source=per_source)
