"""PubMedBERT dense embedder via sentence-transformers (768-dim)."""
import os
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        model_name = os.getenv(
            "DENSE_MODEL",
            "pritamdeka/PubMedBERT-mnli-snli-scinli-scitail-mednli-stsb",
        )
        _model = SentenceTransformer(model_name)
    return _model


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Return dense embeddings for a list of texts."""
    model = _get_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
