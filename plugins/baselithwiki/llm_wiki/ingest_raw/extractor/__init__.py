"""Estrazione PDF → markdown strutturato.

Priorità backend:
1. **Docling** (IBM, MIT) — state-of-the-art 2024-2025: TableFormer preserva
   struttura riga/colonna, reading order, OCR opzionale, export markdown + JSON.
   GPU-accelerato su DGX Spark. Backend consigliato.
2. **Marker** (`marker-pdf`) — alternativa MD diretta.
3. **Fallback manuale**: `pymupdf` (testo) + `pdfplumber` (tabelle) + `pypdf` (meta).
   Senza dipendenze ML, funziona ovunque.

Output: `ExtractedDocument` con:
- `markdown`: testo complete in Markdown, tabelle preservate.
- `pages`: lista `PageContent` con range char e testo raw.
- `tables`: lista `ExtractedTable` con righe strutturate + pagina.
- `metadata`: dict con titolo, autore, numero pagine, edizione se rilevabile.

CLAUDE.md §Workflow ingest PDF richiede doppio passaggio verifica tabelle:
qui lo facciamo automaticamente se il backend non è deterministic (docling lo è).

Modular layout (>500 LOC budget):
- :mod:`.models`    — dataclasses + extension allowlists
- :mod:`._helpers`  — metadata regex, table markdown render, marker-md parser
- :mod:`._docling`  — docling backend (PDF + multi-format)
- :mod:`._marker`   — marker-pdf backend
- :mod:`._fallback` — pymupdf + pdfplumber + text-only fast-path probe
- This module       — public ``extract_document`` / ``extract_pdf`` plus diagnostics
"""

from __future__ import annotations

import logging
from pathlib import Path

from llm_wiki.ingest_raw.extractor._docling import (
    _extract_docling,
    _extract_docling_generic,
)
from llm_wiki.ingest_raw.extractor._fallback import (
    _extract_fallback,
    _try_text_only_fast_path,
)
from llm_wiki.ingest_raw.extractor._marker import _extract_marker
from llm_wiki.ingest_raw.extractor.models import (
    SUPPORTED_DOCLING_ONLY_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    SUPPORTED_PDF_EXTENSIONS,
    Backend,
    ExtractedDocument,
    ExtractedTable,
    PageContent,
)

logger = logging.getLogger(__name__)


# --- API pubblica ----------------------------------------------------------


def extract_document(
    path: Path,
    *,
    prefer_backend: Backend | None = None,
    ocr: bool = False,
) -> ExtractedDocument:
    """Estrae un documento di qualsiasi formato supportato.

    Routing per estensione:

    - ``.pdf`` → backend chain completa (docling → marker → fallback
      pymupdf+pdfplumber). Mantiene il fast-path text-only.
    - ``.docx``, ``.pptx``, ``.html``, ``.htm``, ``.md``, ``.xlsx``,
      immagini → SOLO docling (multi-format converter nativo). Senza
      docling installato, ``ImportError`` esplicito.

    L'output ``ExtractedDocument`` è uniforme: l'agentic + chunking
    pipeline non distingue il formato originale, lavora sempre su
    ``markdown``/``pages``/``tables``.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"estensione {suffix!r} non supportata. Supportate: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    if suffix in SUPPORTED_DOCLING_ONLY_EXTENSIONS:
        return _extract_docling_generic(path)
    return _extract_pdf_impl(path, prefer_backend=prefer_backend, ocr=ocr)


def extract_pdf(
    path: Path,
    *,
    prefer_backend: Backend | None = None,
    ocr: bool = False,
) -> ExtractedDocument:
    """Alias backward-compat. Nuovi caller usino :func:`extract_document`."""
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"atteso .pdf, ricevuto: {path.suffix}")
    return _extract_pdf_impl(path, prefer_backend=prefer_backend, ocr=ocr)


def _extract_pdf_impl(
    path: Path,
    *,
    prefer_backend: Backend | None = None,
    ocr: bool = False,
) -> ExtractedDocument:
    """PDF-specific extraction (chain di backend con fallback)."""
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"atteso .pdf, ricevuto: {path.suffix}")

    if prefer_backend is None and not ocr:
        probed = _try_text_only_fast_path(path)
        if probed is not None:
            return probed

    order: list[Backend] = ["docling", "marker", "fallback"]
    if prefer_backend:
        order = [prefer_backend, *[b for b in order if b != prefer_backend]]

    last_err: Exception | None = None
    for backend in order:
        try:
            if backend == "docling":
                return _extract_docling(path, ocr=ocr)
            if backend == "marker":
                return _extract_marker(path)
            return _extract_fallback(path)
        except ImportError as exc:
            logger.info("backend %s non disponibile: %s", backend, exc)
            last_err = exc
            continue
        except Exception as exc:
            logger.warning("backend %s fallito: %s", backend, exc)
            last_err = exc
            continue
    raise RuntimeError(
        f"Nessun backend PDF funzionante. Installa `docling` (consigliato) o "
        f"`pymupdf pdfplumber`. Ultimo errore: {last_err}"
    )


# --- diagnostic ------------------------------------------------------------


def available_backends() -> list[Backend]:
    """Ritorna i backend effettivamente installati."""
    out: list[Backend] = []
    if _has_module("docling"):
        out.append("docling")
    if _has_module("marker"):
        out.append("marker")
    if _has_module("fitz") and _has_module("pdfplumber"):
        out.append("fallback")
    return out


def _has_module(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None


def assert_extraction_tool_available() -> None:
    """Solleva RuntimeError con messaggio utile se nessun backend è installato."""
    if available_backends():
        return
    raise RuntimeError(
        "Nessun backend PDF installato. Opzioni:\n"
        "  - consigliato: `pip install docling` (GPU su DGX Spark)\n"
        "  - alternativa: `pip install marker-pdf`\n"
        "  - minimo: `pip install pymupdf pdfplumber`"
    )


__all__ = [
    "Backend",
    "ExtractedDocument",
    "ExtractedTable",
    "PageContent",
    "SUPPORTED_DOCLING_ONLY_EXTENSIONS",
    "SUPPORTED_EXTENSIONS",
    "SUPPORTED_PDF_EXTENSIONS",
    "assert_extraction_tool_available",
    "available_backends",
    "extract_document",
    "extract_pdf",
]
