"""Tests for ingestion pipeline."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from ingestion.loaders.statpearls_loader import load_chunks
from ingestion.embedders.dense_embedder import embed_texts, embed_query
from ingestion.embedders.sparse_embedder import SparseEmbedder
import ingestion.pipeline as pipeline


def test_sparse_embedder_fit_encode():
    corpus = [
        "diabetes mellitus type 2 insulin resistance",
        "hypertension blood pressure cardiovascular",
        "pneumonia bacterial infection lung",
    ]
    se = SparseEmbedder()
    se.fit(corpus)
    result = se.encode("diabetes insulin")
    assert isinstance(result, dict)
    assert "indices" in result and "values" in result
    assert len(result["indices"]) == len(result["values"])
    assert len(result["indices"]) > 0


def test_sparse_embedder_empty_query():
    se = SparseEmbedder()
    se.fit(["hello world"])
    result = se.encode("xyzzy12345_notaword")
    assert result["indices"] == []
    assert result["values"] == []


def test_sparse_embedder_state_roundtrip(tmp_path):
    se = SparseEmbedder().fit(["diabetes insulin resistance", "hypertension blood pressure"])
    state_path = tmp_path / "sparse_state.json"
    se.dump(state_path)

    restored = SparseEmbedder.load(state_path)

    assert restored.encode("diabetes insulin") == se.encode("diabetes insulin")


def test_dense_embedder_shape():
    texts = ["What is diabetes?", "Describe hypertension."]
    embeddings = embed_texts(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 768
    assert len(embeddings[1]) == 768


def test_dense_embed_query():
    vec = embed_query("What is pneumonia?")
    assert len(vec) == 768
    assert isinstance(vec[0], float)


def test_load_chunks_from_jsonl(tmp_path):
    # Create a small fake JSONL
    jsonl = tmp_path / "test.jsonl"
    jsonl.write_text(
        '{"id": "1", "title": "Diabetes", "content": "Diabetes is ...", "contents": "Diabetes is ..."}\n'
        '{"id": "2", "title": "HTN", "content": "Hypertension is ...", "contents": "Hypertension is ..."}\n'
    )
    chunks = list(load_chunks(jsonl))
    assert len(chunks) == 2
    assert chunks[0]["title"] == "Diabetes"
    assert "content" in chunks[0]


def test_load_chunks_limit(tmp_path):
    jsonl = tmp_path / "test.jsonl"
    lines = [f'{{"id": "{i}", "content": "text {i}", "title": "T{i}"}}\n' for i in range(10)]
    jsonl.write_text("".join(lines))
    chunks = list(load_chunks(jsonl, limit=3))
    assert len(chunks) == 3


def test_pipeline_saves_sparse_state(tmp_path, monkeypatch):
    jsonl = tmp_path / "test.jsonl"
    jsonl.write_text(
        '{"id": "1", "title": "Diabetes", "content": "Diabetes text", "contents": "Diabetes text"}\n'
    )
    state_path = tmp_path / "sparse_embedder_state.json"
    mock_client = MagicMock()

    monkeypatch.setattr(pipeline, "DATA_PATH", jsonl)
    monkeypatch.setattr(pipeline, "SPARSE_STATE_PATH", state_path)
    monkeypatch.setattr(pipeline, "get_client", lambda: mock_client)
    monkeypatch.setattr(pipeline, "ensure_collection", lambda client: None)
    monkeypatch.setattr(pipeline, "embed_texts", lambda texts: [[0.0] * 768 for _ in texts])

    total = pipeline.run(limit=1)

    assert total == 1
    assert state_path.exists()
