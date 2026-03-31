"""Tests for retrieval pipeline."""
import pytest
from retrieval.hybrid_retriever import rrf_fuse
from retrieval.crag import crag_gate
from retrieval.context_assembler import deduplicate, lost_in_middle_reorder, format_citations, assemble_context


def test_rrf_fuse_basic():
    list1 = [{"doc_id": "a", "content": "A", "score": 0.9}, {"doc_id": "b", "content": "B", "score": 0.7}]
    list2 = [{"doc_id": "b", "content": "B", "score": 0.8}, {"doc_id": "c", "content": "C", "score": 0.5}]
    fused = rrf_fuse([list1, list2], k=60)
    ids = [d["doc_id"] for d in fused]
    # 'b' appears in both lists → should rank high
    assert "b" in ids
    assert ids[0] == "b" or ids[1] == "b"


def test_rrf_fuse_empty():
    fused = rrf_fuse([[], []])
    assert fused == []


def test_crag_gate_confident():
    docs = [{"doc_id": "a", "content": "x", "rerank_score": 5.0}]
    filtered, confident = crag_gate(docs, threshold=0.6)
    assert confident is True
    assert filtered == docs


def test_crag_gate_not_confident():
    docs = [{"doc_id": "a", "content": "x", "rerank_score": -10.0}]
    filtered, confident = crag_gate(docs, threshold=0.6)
    assert confident is False


def test_crag_gate_empty():
    _, confident = crag_gate([])
    assert confident is False


def test_deduplicate():
    docs = [
        {"doc_id": "a", "content": "A"},
        {"doc_id": "b", "content": "B"},
        {"doc_id": "a", "content": "A"},
    ]
    result = deduplicate(docs)
    assert len(result) == 2
    assert result[0]["doc_id"] == "a"
    assert result[1]["doc_id"] == "b"


def test_lost_in_middle_reorder():
    docs = [{"doc_id": str(i)} for i in range(5)]
    reordered = lost_in_middle_reorder(docs)
    assert reordered[0]["doc_id"] == "0"
    assert reordered[-1]["doc_id"] == "1"


def test_format_citations():
    docs = [
        {"doc_id": "1", "title": "Diabetes", "content": "Diabetes text", "source": "statpearls"},
        {"doc_id": "2", "title": "HTN", "content": "HTN text", "source": "statpearls"},
    ]
    context = format_citations(docs)
    assert "[1] Source: statpearls | Title: Diabetes" in context
    assert "[2] Source: statpearls | Title: HTN" in context


def test_assemble_context():
    docs = [
        {"doc_id": "a", "title": "A", "content": "A text", "source": "statpearls"},
        {"doc_id": "b", "title": "B", "content": "B text", "source": "statpearls"},
        {"doc_id": "a", "title": "A", "content": "A text", "source": "statpearls"},  # duplicate
    ]
    context, ordered = assemble_context(docs)
    assert len(ordered) == 2  # deduplicated
    assert "[1]" in context
