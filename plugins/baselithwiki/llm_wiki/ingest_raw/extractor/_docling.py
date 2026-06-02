"""Docling backend: PDF + multi-format converter."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

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


def _extract_docling_generic(path: Path) -> ExtractedDocument:
    """Estrazione docling per formati non-PDF (DOCX/PPTX/HTML/XLSX/MD/IMG).

    Docling ``DocumentConverter`` autorouta per estensione via
    ``InputFormat``. Output uniforme con backend marker ``docling``.

    Nota: per file ``.md`` nativi docling fa comunque parsing strutturale
    (heading detection, list normalization) — utile se il MD viene da
    un export tool che ha sporcato l'AST.
    """
    try:
        from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            f"docling non installato. Necessario per ingest di {path.suffix} "
            "files. `pip install docling`"
        ) from exc

    converter = DocumentConverter()
    try:
        result = converter.convert(str(path))
    except Exception as exc:
        raise RuntimeError(f"docling convert fallito per {path.name}: {exc}") from exc
    doc = result.document

    full_md = doc.export_to_markdown()

    pages: list[PageContent] = []
    if hasattr(doc, "pages") and doc.pages:
        for page_no, page in sorted(doc.pages.items()):
            page_text = getattr(page, "text", "") or ""
            pages.append(
                PageContent(number=int(page_no), markdown=page_text, text=page_text)
            )
    else:
        pages.append(PageContent(number=1, markdown=full_md, text=full_md))

    tables: list[ExtractedTable] = []
    for tbl in getattr(doc, "tables", []) or []:
        try:
            header, rows = _docling_table_to_rows(tbl)
            md = _rows_to_markdown(header, rows)
            page_no = _docling_table_page(tbl)
            tables.append(
                ExtractedTable(
                    caption=getattr(tbl, "caption", None),
                    page=page_no,
                    header=header,
                    rows=rows,
                    markdown=md,
                )
            )
        except Exception as exc:
            logger.debug(
                "docling tabella non serializzabile (%s): %s", path.suffix, exc
            )
            continue

    metadata = _extract_metadata(path, full_md)
    return ExtractedDocument(
        source_path=path,
        backend="docling",
        markdown=full_md,
        pages=pages,
        tables=tables,
        metadata=metadata,
    )


def _extract_docling(path: Path, *, ocr: bool) -> ExtractedDocument:
    """Backend preferito: IBM Docling con TableFormer.

    Installazione: `pip install docling`
    """
    try:
        from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise ImportError("docling non installato. `pip install docling`") from exc

    converter: Any
    if ocr:
        try:
            from docling.datamodel.base_models import InputFormat  # type: ignore[import-not-found]
            from docling.datamodel.pipeline_options import (  # type: ignore[import-not-found]
                PdfPipelineOptions,
            )
            from docling.document_converter import (  # type: ignore[import-not-found]
                PdfFormatOption,
            )

            opts = PdfPipelineOptions()
            opts.do_ocr = True
            opts.do_table_structure = True
            converter = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
            )
        except ImportError:
            logger.info(
                "docling opzioni OCR non disponibili in questa versione; uso default"
            )
            converter = DocumentConverter()
    else:
        converter = DocumentConverter()
    result = converter.convert(str(path))
    doc = result.document

    full_md = doc.export_to_markdown()

    pages: list[PageContent] = []
    if hasattr(doc, "pages") and doc.pages:
        for page_no, page in sorted(doc.pages.items()):
            page_text = getattr(page, "text", "") or ""
            pages.append(
                PageContent(number=int(page_no), markdown=page_text, text=page_text)
            )
    else:
        pages.append(PageContent(number=1, markdown=full_md, text=full_md))

    tables: list[ExtractedTable] = []
    for tbl in getattr(doc, "tables", []) or []:
        try:
            header, rows = _docling_table_to_rows(tbl)
            md = _rows_to_markdown(header, rows)
            page_no = _docling_table_page(tbl)
            tables.append(
                ExtractedTable(
                    caption=getattr(tbl, "caption", None),
                    page=page_no,
                    header=header,
                    rows=rows,
                    markdown=md,
                )
            )
        except Exception as exc:
            logger.debug("docling tabella non serializzabile: %s", exc)
            continue

    metadata = _extract_metadata(path, full_md)
    return ExtractedDocument(
        source_path=path,
        backend="docling",
        markdown=full_md,
        pages=pages,
        tables=tables,
        metadata=metadata,
    )


def _docling_table_to_rows(tbl: Any) -> tuple[list[str], list[list[str]]]:
    """Tenta di estrarre header+rows da vari schemi docling (API in evoluzione)."""
    if hasattr(tbl, "export_to_dataframe"):
        try:
            df = tbl.export_to_dataframe()
            header = [str(c) for c in df.columns]
            rows = [[str(x) for x in row] for row in df.itertuples(index=False)]
            return header, rows
        except Exception:
            pass
    grid = getattr(getattr(tbl, "data", None), "grid", None)
    if grid:
        header = [str(c.text) if hasattr(c, "text") else str(c) for c in grid[0]]
        rows = [
            [str(c.text) if hasattr(c, "text") else str(c) for c in row]
            for row in grid[1:]
        ]
        return header, rows
    return [], []


def _docling_table_page(tbl: Any) -> int:
    prov = getattr(tbl, "prov", None)
    if prov and len(prov) > 0:
        return int(getattr(prov[0], "page_no", 1))
    return 1
