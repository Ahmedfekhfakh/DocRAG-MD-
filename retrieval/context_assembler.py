"""Dedup + lost-in-middle reorder + citation formatting."""


def deduplicate(docs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique = []
    for doc in docs:
        key = doc.get("doc_id", doc.get("content", "")[:100])
        if key not in seen:
            seen.add(key)
            unique.append(doc)
    return unique


def lost_in_middle_reorder(docs: list[dict]) -> list[dict]:
    """Best chunk → index 0, 2nd-best → index -1, rest fill the middle."""
    if len(docs) <= 2:
        return docs
    reordered = [None] * len(docs)
    reordered[0] = docs[0]
    reordered[-1] = docs[1]
    middle = docs[2:]
    for i, doc in enumerate(middle):
        reordered[i + 1] = doc
    return reordered


def format_citations(docs: list[dict]) -> str:
    """Format as [N] Source: statpearls | Title: ... \n content"""
    parts = []
    for i, doc in enumerate(docs, start=1):
        header = f"[{i}] Source: {doc.get('source', 'statpearls')} | Title: {doc.get('title', 'Unknown')}"
        parts.append(f"{header}\n{doc.get('content', '')}")
    return "\n\n".join(parts)


def assemble_context(docs: list[dict]) -> tuple[str, list[dict]]:
    """Full pipeline: dedup → lost-in-middle → format. Returns (context_str, ordered_docs)."""
    docs = deduplicate(docs)
    docs = lost_in_middle_reorder(docs)
    context = format_citations(docs)
    return context, docs
