"""
Download and chunk StatPearls data into JSONL format.

Run via:  python -m scripts.download_all
Or via:   bash download_data.sh [CHUNK_LIMIT]
"""
import os
import json
import tarfile
import urllib.request
import tempfile
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
CHUNKS_FILE = DATA_DIR / "statpearls_chunks.jsonl"

STATPEARLS_TAR_URL = (
    "https://ftp.ncbi.nlm.nih.gov/pub/litarch/3d/12/statpearls_NBK430685.tar.gz"
)


def _progress_hook(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(downloaded / total_size * 100, 100)
        mb = downloaded / 1024 / 1024
        total_mb = total_size / 1024 / 1024
        print(f"\r  {pct:.1f}%  {mb:.0f} / {total_mb:.0f} MB", end="", flush=True)


def download_file(url: str, dest: Path, label: str) -> None:
    log.info("Downloading %s → %s", label, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    try:
        urllib.request.urlretrieve(url, tmp, _progress_hook)
        print()  # newline after progress
        tmp.rename(dest)
        log.info("Saved %s (%.1f MB)", dest.name, dest.stat().st_size / 1024 / 1024)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _strip_tags(text: str) -> str:
    """Minimal XML/HTML tag stripper."""
    return re.sub(r"<[^>]+>", " ", text)


def _clean(text: str) -> str:
    text = _strip_tags(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_chunks_from_tar(tar_path: Path, out_path: Path, chunk_size: int = 400, limit: int | None = None) -> int:
    """
    Parse StatPearls tarball (JATS XML articles) into JSONL chunks.
    Each article is split into ~400-word chunks matching MedRAG's format:
      {"id": str, "title": str, "content": str, "contents": str}
    """
    import xml.etree.ElementTree as ET

    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with tarfile.open(tar_path, "r:gz") as tar, out_path.open("w", encoding="utf-8") as out:
        members = [m for m in tar.getmembers() if m.name.endswith((".xml", ".nxml"))]
        log.info("Processing %d XML articles ...", len(members))
        for i, member in enumerate(members):
            try:
                f = tar.extractfile(member)
                if f is None:
                    continue
                xml_bytes = f.read()
                root = ET.fromstring(xml_bytes)

                # Extract title
                title_el = root.find(".//{http://jats.nlm.nih.gov}article-title")
                if title_el is None:
                    title_el = root.find(".//article-title")
                title = _clean(ET.tostring(title_el, encoding="unicode", method="text")) if title_el is not None else member.name

                # Extract all body text
                body_el = root.find(".//{http://jats.nlm.nih.gov}body")
                if body_el is None:
                    body_el = root.find(".//body")
                if body_el is None:
                    continue
                full_text = _clean(ET.tostring(body_el, encoding="unicode", method="text"))
                if not full_text:
                    continue

                # Split into chunks
                words = full_text.split()
                for j in range(0, len(words), chunk_size):
                    chunk_words = words[j : j + chunk_size]
                    chunk_text = " ".join(chunk_words)
                    chunk_id = f"{member.name}_{j}"
                    record = {
                        "id": chunk_id,
                        "title": title,
                        "content": chunk_text,
                        "contents": chunk_text,
                    }
                    out.write(json.dumps(record) + "\n")
                    count += 1
                    if limit and count >= limit:
                        log.info("DATA_CHUNK_LIMIT=%d reached, stopping early.", limit)
                        return count

            except Exception as e:
                log.warning("Skipping %s: %s", member.name, e)

            if (i + 1) % 500 == 0:
                log.info("  Processed %d / %d articles, %d chunks so far", i + 1, len(members), count)

    log.info("Total chunks written: %d", count)
    return count


def download_statpearls() -> None:
    if CHUNKS_FILE.exists():
        lines = sum(1 for _ in CHUNKS_FILE.open())
        if lines > 0:
            log.info("StatPearls chunks already present: %d chunks", lines)
            return
        log.info("StatPearls file exists but is empty — re-downloading.")
        CHUNKS_FILE.unlink()

    log.info("=== Downloading StatPearls tarball (~1.7 GB) ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = Path(tmpdir) / "statpearls.tar.gz"
        download_file(STATPEARLS_TAR_URL, tar_path, "statpearls_NBK430685.tar.gz")
        limit = int(os.getenv("DATA_CHUNK_LIMIT", "0")) or None
        log.info("Extracting and chunking StatPearls articles (limit=%s) ...", limit or "all")
        count = _extract_chunks_from_tar(tar_path, CHUNKS_FILE, limit=limit)
        log.info("StatPearls ready: %d chunks → %s", count, CHUNKS_FILE)


PRIMEKG_URL = "https://dataverse.harvard.edu/api/access/datafile/6180620"
PRIMEKG_FILE = DATA_DIR / "kg.csv"


def download_primekg() -> None:
    if PRIMEKG_FILE.exists() and PRIMEKG_FILE.stat().st_size > 1000:
        log.info("PrimeKG already present: %s (%.0f MB)",
                 PRIMEKG_FILE, PRIMEKG_FILE.stat().st_size / 1024 / 1024)
        return
    log.info("=== Downloading PrimeKG (~500 MB) ===")
    download_file(PRIMEKG_URL, PRIMEKG_FILE, "PrimeKG kg.csv")


def main():
    DATA_DIR.mkdir(exist_ok=True)
    download_statpearls()
    download_primekg()
    log.info("=== Download complete ===")


if __name__ == "__main__":
    main()
