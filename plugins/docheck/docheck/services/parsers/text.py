"""Plain-text/Markdown parser."""

import uuid
from pathlib import Path

from ...schemas.state import Chunk

_LINES_PER_CHUNK = 40


def parse(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines() or [""]
    chunks: list[Chunk] = []
    for i in range(0, len(lines), _LINES_PER_CHUNK):
        block = lines[i : i + _LINES_PER_CHUNK]
        body = "\n".join(block)
        chunks.append(
            Chunk(
                id=f"c-{uuid.uuid4().hex[:8]}",
                text=body,
                page=1,
                line_start=i + 1,
                line_end=i + len(block),
                bbox=(0.0, 0.0, 0.0, 0.0),
                token_count=len(body.split()),
            )
        )
    return chunks
