"""Tests for download_all.py — no network calls, uses temp files."""
import io
import json
import tarfile
import tempfile
import pytest
from pathlib import Path
from scripts.download_all import _clean, _strip_tags, _extract_chunks_from_tar


def make_jats_xml(title: str, body: str) -> bytes:
    return f"""<?xml version="1.0"?>
<article xmlns="http://jats.nlm.nih.gov">
  <front><article-meta><title-group>
    <article-title>{title}</article-title>
  </title-group></article-meta></front>
  <body><p>{body}</p></body>
</article>""".encode()


def make_tarball(articles: dict[str, bytes]) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
    with tarfile.open(tmp.name, "w:gz") as tar:
        for name, content in articles.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return Path(tmp.name)


def test_strip_tags():
    assert _strip_tags("<p>Hello <b>world</b></p>") == " Hello  world  "


def test_clean():
    assert _clean("<p>  Hello   <b>world</b>  </p>") == "Hello world"
    assert _clean("  multiple   spaces  ") == "multiple spaces"


def test_extract_single_article():
    xml = make_jats_xml(
        "Hypertension",
        "Hypertension is elevated blood pressure above 140/90 mmHg. "
        "It is a major risk factor for stroke and heart disease.",
    )
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = make_tarball({"hypertension.xml": xml})
        out_path = Path(tmp) / "chunks.jsonl"
        count = _extract_chunks_from_tar(tar_path, out_path, chunk_size=100)
        assert count == 1
        chunks = [json.loads(l) for l in out_path.read_text().splitlines()]
        assert chunks[0]["title"] == "Hypertension"
        assert "blood pressure" in chunks[0]["content"]
        assert "content" in chunks[0] and "contents" in chunks[0]
        assert "id" in chunks[0]


def test_extract_multiple_chunks():
    # 50 words → should produce 5 chunks with chunk_size=10
    words = " ".join([f"word{i}" for i in range(50)])
    xml = make_jats_xml("Big Article", words)
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = make_tarball({"big.xml": xml})
        out_path = Path(tmp) / "chunks.jsonl"
        count = _extract_chunks_from_tar(tar_path, out_path, chunk_size=10)
        assert count == 5
        chunks = [json.loads(l) for l in out_path.read_text().splitlines()]
        assert all(c["title"] == "Big Article" for c in chunks)


def test_extract_multiple_articles():
    articles = {
        "a.xml": make_jats_xml("Article A", "Content about diabetes and insulin."),
        "b.xml": make_jats_xml("Article B", "Content about hypertension and stroke."),
        "c.xml": make_jats_xml("Article C", "Content about pneumonia and antibiotics."),
    }
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = make_tarball(articles)
        out_path = Path(tmp) / "chunks.jsonl"
        count = _extract_chunks_from_tar(tar_path, out_path, chunk_size=100)
        assert count == 3
        chunks = [json.loads(l) for l in out_path.read_text().splitlines()]
        titles = {c["title"] for c in chunks}
        assert titles == {"Article A", "Article B", "Article C"}


def test_extract_skips_non_xml():
    articles = {
        "article.xml": make_jats_xml("Real Article", "Medical content here."),
        "readme.txt": b"This is not XML",
    }
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = make_tarball(articles)
        out_path = Path(tmp) / "chunks.jsonl"
        count = _extract_chunks_from_tar(tar_path, out_path, chunk_size=100)
        assert count == 1  # Only the XML article


def test_extract_handles_bad_xml_gracefully():
    articles = {
        "good.xml": make_jats_xml("Good Article", "Valid content."),
        "bad.xml": b"<not valid xml at all >>>",
    }
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = make_tarball(articles)
        out_path = Path(tmp) / "chunks.jsonl"
        count = _extract_chunks_from_tar(tar_path, out_path, chunk_size=100)
        assert count == 1  # bad.xml skipped, good.xml processed


def test_chunk_ids_are_unique():
    words = " ".join([f"w{i}" for i in range(30)])
    xml = make_jats_xml("Test", words)
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = make_tarball({"test.xml": xml})
        out_path = Path(tmp) / "chunks.jsonl"
        _extract_chunks_from_tar(tar_path, out_path, chunk_size=10)
        chunks = [json.loads(l) for l in out_path.read_text().splitlines()]
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"


def test_idempotent_skip_when_file_exists(monkeypatch, tmp_path):
    """download_statpearls() should skip if chunks file already exists."""
    import scripts.download_all as dl
    chunks_file = tmp_path / "statpearls_chunks.jsonl"
    chunks_file.write_text('{"id":"1","title":"T","content":"C","contents":"C"}\n')

    monkeypatch.setattr(dl, "CHUNKS_FILE", chunks_file)
    called = []
    monkeypatch.setattr(dl, "download_file", lambda *a, **k: called.append(1))

    dl.download_statpearls()
    assert called == [], "Should not re-download if file already exists"
