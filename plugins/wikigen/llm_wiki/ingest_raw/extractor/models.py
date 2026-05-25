"""Dataclasses + extension allowlists for the document extractor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Backend = Literal["docling", "marker", "fallback"]


# Estensioni supportate dal pipeline. ``.pdf`` ha una backend chain
# (docling → marker → fallback pymupdf+pdfplumber); gli altri formati
# passano SOLO per docling (multi-format converter nativo). Senza
# docling installato, l'ingest di .docx/.pptx/.html/.xlsx fallisce con
# ImportError esplicito.
SUPPORTED_PDF_EXTENSIONS = frozenset({".pdf"})
SUPPORTED_DOCLING_ONLY_EXTENSIONS = frozenset(
    {".docx", ".pptx", ".html", ".htm", ".md", ".xlsx", ".png", ".jpg", ".jpeg", ".tiff"}
)
SUPPORTED_EXTENSIONS = SUPPORTED_PDF_EXTENSIONS | SUPPORTED_DOCLING_ONLY_EXTENSIONS


@dataclass
class PageContent:
    number: int  # 1-based
    markdown: str
    text: str  # plain text (no markup)


@dataclass
class ExtractedTable:
    caption: str | None  # riga sopra la tabella nel PDF, se disponibile
    page: int
    header: list[str]
    rows: list[list[str]]
    markdown: str  # tabella in md pronta all'uso

    def as_markdown_block(self) -> str:
        if self.markdown.strip():
            return self.markdown
        if not self.header:
            return ""
        sep = " | ".join("---" for _ in self.header)
        rows_md = "\n".join(" | ".join(r) for r in self.rows)
        return f"| {' | '.join(self.header)} |\n| {sep} |\n{rows_md}"


@dataclass
class ExtractedDocument:
    source_path: Path
    backend: Backend
    markdown: str
    pages: list[PageContent]
    tables: list[ExtractedTable]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_pages(self) -> int:
        return len(self.pages)

    def to_summary(self) -> str:
        ed = self.metadata.get("edizione") or "?"
        return (
            f"ExtractedDocument({self.source_path.name}, backend={self.backend}, "
            f"pages={self.n_pages}, tables={len(self.tables)}, edizione={ed})"
        )
