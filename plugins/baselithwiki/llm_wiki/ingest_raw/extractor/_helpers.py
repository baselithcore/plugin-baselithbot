"""Shared text/table helpers for the document extractor."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from llm_wiki.ingest_raw.extractor.models import ExtractedTable

_EDIZIONE_RE = re.compile(
    r"(?:Ed|Edizione|Versione)\.?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
    re.IGNORECASE,
)
_MODELLO_RE = re.compile(r"\b([A-Z]{2}/\d{4,5}/\d+/\d+(?:/[A-Z])?)\b")


def _extract_metadata(path: Path, text: str) -> dict[str, Any]:
    """Heuristica leggera: cerca edizione, modello, titolo candidato."""
    out: dict[str, Any] = {"source_file": str(path)}
    m_ed = _EDIZIONE_RE.search(text[:5000])
    if m_ed:
        out["edizione"] = m_ed.group(1).replace("-", "/").replace(".", "/")
    m_mod = _MODELLO_RE.search(text[:5000])
    if m_mod:
        out["modello"] = m_mod.group(1)
    for line in text.splitlines()[:50]:
        line = line.strip()
        if line.startswith("#"):
            out.setdefault("title_candidate", line.lstrip("# ").strip())
            break
        if len(line) > 20 and not line.isdigit():
            out.setdefault("title_candidate", line[:120])
            break
    return out


def _rows_to_markdown(header: list[str], rows: list[list[str]]) -> str:
    if not header:
        return ""
    sep = " | ".join("---" for _ in header)
    body = "\n".join(" | ".join(_escape_cell(c) for c in row) for row in rows)
    return f"| {' | '.join(_escape_cell(c) for c in header)} |\n| {sep} |\n{body}"


def _escape_cell(c: str) -> str:
    return (c or "").replace("\n", " ").replace("|", "\\|").strip()


def _extract_tables_from_markdown(
    md: str, *, default_page: int
) -> list[ExtractedTable]:
    """Parse tabelle da markdown già esistente (backend marker)."""
    out: list[ExtractedTable] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        if (
            lines[i].lstrip().startswith("|")
            and i + 1 < len(lines)
            and "---" in lines[i + 1]
        ):
            start = i
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                i += 1
            block = lines[start:i]
            header = [c.strip() for c in block[0].strip().strip("|").split("|")]
            rows = [
                [c.strip() for c in r.strip().strip("|").split("|")] for r in block[2:]
            ]
            out.append(
                ExtractedTable(
                    caption=None,
                    page=default_page,
                    header=header,
                    rows=rows,
                    markdown="\n".join(block),
                )
            )
        else:
            i += 1
    return out
