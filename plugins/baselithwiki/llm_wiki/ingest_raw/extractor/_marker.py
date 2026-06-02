"""Marker-pdf backend: alternative MD-direct PDF converter."""

from __future__ import annotations

from pathlib import Path

from llm_wiki.ingest_raw.extractor._helpers import (
    _extract_metadata,
    _extract_tables_from_markdown,
)
from llm_wiki.ingest_raw.extractor.models import ExtractedDocument, PageContent


def _extract_marker(path: Path) -> ExtractedDocument:
    """Backend alternativo: marker-pdf (CLI o Python API)."""
    try:
        from marker.convert import convert_single_pdf  # type: ignore[import-not-found]
        from marker.models import load_all_models  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError("marker non installato. `pip install marker-pdf`") from exc

    model_lst = load_all_models()
    full_md, _images, out_meta = convert_single_pdf(str(path), model_lst)
    pages = [PageContent(number=1, markdown=full_md, text=full_md)]
    tables = _extract_tables_from_markdown(full_md, default_page=1)
    metadata = _extract_metadata(path, full_md) | (out_meta or {})
    return ExtractedDocument(
        source_path=path,
        backend="marker",
        markdown=full_md,
        pages=pages,
        tables=tables,
        metadata=metadata,
    )
