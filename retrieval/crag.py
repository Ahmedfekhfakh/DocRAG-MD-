"""CRAG confidence gate — refuse if top rerank score < threshold."""
import os

THRESHOLD = float(os.getenv("CRAG_CONFIDENCE_THRESHOLD", "0.60"))


def crag_gate(docs: list[dict], threshold: float = THRESHOLD) -> tuple[list[dict], bool]:
    """
    Returns (docs, is_confident).
    If top rerank_score < threshold, is_confident=False → caller should refuse.
    Uses normalised sigmoid-like score from cross-encoder (range ~ -10 to 10).
    We normalise with sigmoid before comparing.
    """
    if not docs:
        return [], False

    import math

    def sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    top_score = docs[0].get("rerank_score", docs[0].get("score", 0.0))
    normalised = sigmoid(top_score)
    is_confident = normalised >= threshold
    return docs, is_confident
