"""Load StatPearls chunks from JSONL file."""
import json
from pathlib import Path
from typing import Generator


def load_chunks(path: str | Path, limit: int | None = None) -> Generator[dict, None, None]:
    """Yield chunks from statpearls_chunks.jsonl.

    Each chunk has: content (str), contents (str), title (str), id (str).
    StatPearls fields: content→dense, contents→sparse, title→metadata.
    """
    path = Path(path)
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunk = json.loads(line)
            # Normalise field names
            if "content" not in chunk and "contents" in chunk:
                chunk["content"] = chunk["contents"]
            yield chunk
            count += 1
            if limit and count >= limit:
                break
