"""DOCX parser via python-docx."""

import uuid
from pathlib import Path

from ...schemas.state import Chunk


def parse(path: Path) -> list[Chunk]:
    from docx import Document

    doc = Document(str(path))
    chunks: list[Chunk] = []
    line = 1
    for para in doc.paragraphs:
        text = para.text
        if not text.strip():
            line += 1
            continue
        chunks.append(
            Chunk(
                id=f"c-{uuid.uuid4().hex[:8]}",
                text=text,
                page=1,
                line_start=line,
                line_end=line,
                bbox=(0.0, 0.0, 0.0, 0.0),
                token_count=len(text.split()),
            )
        )
        line += 1
    return chunks
