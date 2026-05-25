"""Fallback PDF backend (pymupdf + pdfplumber) + text-only fast-path probe."""

from __future__ import annotations

import logging
from pathlib import Path

from llm_wiki.ingest_raw.extractor._helpers import (
    _extract_metadata,
    _rows_to_markdown,
)
from llm_wiki.ingest_raw.extractor.models import (
    ExtractedDocument,
    ExtractedTable,
    PageContent,
)

logger = logging.getLogger(__name__)


def _try_text_only_fast_path(path: Path) -> ExtractedDocument | None:
    """Probe rapido: PDF con testo nativo denso e zero tabelle → fallback.

    Docling impiega 10–60s/PDF (model load + layout analysis); su PDF nativi
    text-only (CV, articoli, contratti puri) il fallback pymupdf produce
    output equivalente in ~1s. Probe a due step:

    1. pymupdf su tutte le pagine: char/page sopra
       ``INGEST_SKIP_DOCLING_THRESHOLD`` → text-dense.
    2. pdfplumber sulle prime 3 pagine: zero tabelle → docling non aggiunge
       valore (TableFormer è il suo principale differenziatore).

    Se passa entrambi → ritorna ``_extract_fallback(path)`` direttamente.
    Altrimenti ``None`` → caller usa la backend chain normale.

    Imports lazy: niente costo se pymupdf/pdfplumber non sono installati.
    """
    from llm_wiki.config import INGEST_SKIP_DOCLING_THRESHOLD

    if INGEST_SKIP_DOCLING_THRESHOLD <= 0:
        return None
    try:
        import fitz  # type: ignore[import-not-found]
        import pdfplumber  # type: ignore[import-not-found]
    except ImportError:
        return None

    try:
        with fitz.open(str(path)) as doc:
            n_pages = len(doc)
            if n_pages == 0:
                return None
            total_chars = sum(len(page.get_text("text")) for page in doc)
        if total_chars / n_pages < INGEST_SKIP_DOCLING_THRESHOLD:
            return None
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages[:3]:
                if page.extract_tables():
                    return None
    except Exception as exc:
        logger.debug("text-only probe fallita (%s); userò backend chain", exc)
        return None

    logger.info(
        "text-only fast-path: %s (%d pagine, ~%d char/page) → fallback",
        path.name,
        n_pages,
        total_chars // n_pages,
    )
    return _extract_fallback(path)


def _extract_fallback(path: Path) -> ExtractedDocument:
    """Fallback deterministic senza ML: pymupdf (testo) + pdfplumber (tabelle)."""
    try:
        import fitz  # type: ignore[import-not-found]  # pymupdf
    except ImportError as exc:
        raise ImportError(
            "pymupdf non installato (fallback). `pip install pymupdf pdfplumber`"
        ) from exc

    try:
        import pdfplumber  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError("pdfplumber non installato (fallback). `pip install pdfplumber`") from exc

    pages: list[PageContent] = []
    md_parts: list[str] = []
    with fitz.open(str(path)) as doc:
        title = doc.metadata.get("title") if doc.metadata else None
        author = doc.metadata.get("author") if doc.metadata else None
        for i, page in enumerate(doc, start=1):
            txt = page.get_text("text")
            pages.append(PageContent(number=i, markdown=txt, text=txt))
            md_parts.append(f"\n\n<!-- page {i} -->\n\n{txt}")

    tables: list[ExtractedTable] = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            for tbl_raw in page.extract_tables() or []:
                if not tbl_raw:
                    continue
                header = [str(c or "").strip() for c in tbl_raw[0]]
                rows = [[str(c or "").strip() for c in r] for r in tbl_raw[1:]]
                md = _rows_to_markdown(header, rows)
                tables.append(
                    ExtractedTable(caption=None, page=i, header=header, rows=rows, markdown=md)
                )

    full_md = "".join(md_parts)
    metadata = _extract_metadata(path, full_md)
    metadata.setdefault("title", title)
    metadata.setdefault("author", author)
    return ExtractedDocument(
        source_path=path,
        backend="fallback",
        markdown=full_md,
        pages=pages,
        tables=tables,
        metadata=metadata,
    )
