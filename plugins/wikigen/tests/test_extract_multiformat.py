"""Multi-format ingest: routing per estensione + allowlist routers.

Non chiama docling reale (lento, dipendenza opzionale): patcha
``_extract_docling_generic`` e ``_extract_pdf_impl`` per verificare
routing. Smoke test ``DOCLING_AVAILABLE`` per sanità del fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from llm_wiki.ingest_raw.extractor import (
    SUPPORTED_DOCLING_ONLY_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    SUPPORTED_PDF_EXTENSIONS,
    ExtractedDocument,
    PageContent,
    extract_document,
    extract_pdf,
)


def _fake_doc(path: Path, backend: str) -> ExtractedDocument:
    return ExtractedDocument(
        source_path=path,
        backend=backend,  # type: ignore[arg-type]
        markdown="md",
        pages=[PageContent(number=1, markdown="md", text="md")],
        tables=[],
        metadata={},
    )


def test_extensions_sets_are_disjoint() -> None:
    assert SUPPORTED_PDF_EXTENSIONS.isdisjoint(SUPPORTED_DOCLING_ONLY_EXTENSIONS)
    assert (
        SUPPORTED_EXTENSIONS
        == SUPPORTED_PDF_EXTENSIONS | SUPPORTED_DOCLING_ONLY_EXTENSIONS
    )


def test_extensions_include_common_formats() -> None:
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert ".docx" in SUPPORTED_EXTENSIONS
    assert ".pptx" in SUPPORTED_EXTENSIONS
    assert ".html" in SUPPORTED_EXTENSIONS
    assert ".xlsx" in SUPPORTED_EXTENSIONS


def test_extract_document_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_document(tmp_path / "nope.pdf")


def test_extract_document_unsupported_extension_raises(tmp_path: Path) -> None:
    p = tmp_path / "data.rtf"
    p.write_bytes(b"x")
    with pytest.raises(ValueError, match="non supportata"):
        extract_document(p)


def test_extract_document_routes_docx_to_generic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    p = tmp_path / "report.docx"
    p.write_bytes(b"x")
    calls: list[str] = []

    def _fake_generic(path: Path) -> ExtractedDocument:
        calls.append("generic")
        return _fake_doc(path, "docling")

    def _fake_pdf_impl(*args: Any, **kwargs: Any) -> ExtractedDocument:
        calls.append("pdf")
        return _fake_doc(p, "docling")

    monkeypatch.setattr(
        "llm_wiki.ingest_raw.extractor._extract_docling_generic", _fake_generic
    )
    monkeypatch.setattr(
        "llm_wiki.ingest_raw.extractor._extract_pdf_impl", _fake_pdf_impl
    )
    doc = extract_document(p)
    assert calls == ["generic"]
    assert doc.backend == "docling"


def test_extract_document_routes_pptx_to_generic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    p = tmp_path / "slides.pptx"
    p.write_bytes(b"x")
    state: dict[str, int] = {"generic": 0, "pdf": 0}

    monkeypatch.setattr(
        "llm_wiki.ingest_raw.extractor._extract_docling_generic",
        lambda path: (
            state.__setitem__("generic", state["generic"] + 1)
            or _fake_doc(path, "docling")
        ),
    )
    monkeypatch.setattr(
        "llm_wiki.ingest_raw.extractor._extract_pdf_impl",
        lambda *a, **kw: state.__setitem__("pdf", state["pdf"] + 1)
        or _fake_doc(p, "docling"),
    )
    extract_document(p)
    assert state["generic"] == 1
    assert state["pdf"] == 0


def test_extract_document_routes_pdf_to_chain(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    p = tmp_path / "doc.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    calls: list[str] = []

    monkeypatch.setattr(
        "llm_wiki.ingest_raw.extractor._extract_docling_generic",
        lambda path: (calls.append("generic"), _fake_doc(path, "docling"))[1],
    )
    monkeypatch.setattr(
        "llm_wiki.ingest_raw.extractor._extract_pdf_impl",
        lambda *a, **kw: (calls.append("pdf"), _fake_doc(p, "docling"))[1],
    )
    doc = extract_document(p)
    assert calls == ["pdf"]
    assert doc.source_path == p


def test_extract_document_routes_html_to_generic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    p = tmp_path / "page.html"
    p.write_bytes(b"<html><body>hi</body></html>")
    flag = {"generic": False}
    monkeypatch.setattr(
        "llm_wiki.ingest_raw.extractor._extract_docling_generic",
        lambda path: (flag.__setitem__("generic", True), _fake_doc(path, "docling"))[1],
    )
    extract_document(p)
    assert flag["generic"]


def test_extract_pdf_legacy_alias_works(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Backward-compat: ``extract_pdf`` accetta solo .pdf e usa la chain."""
    p = tmp_path / "doc.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        "llm_wiki.ingest_raw.extractor._extract_pdf_impl",
        lambda *a, **kw: _fake_doc(p, "docling"),
    )
    doc = extract_pdf(p)
    assert doc.backend == "docling"


def test_extract_pdf_legacy_rejects_non_pdf(tmp_path: Path) -> None:
    p = tmp_path / "doc.docx"
    p.write_bytes(b"x")
    with pytest.raises(ValueError, match="atteso .pdf"):
        extract_pdf(p)


def test_extract_document_routes_image_to_generic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    p = tmp_path / "scan.png"
    p.write_bytes(b"\x89PNG\r\n")
    flag = {"generic": False}
    monkeypatch.setattr(
        "llm_wiki.ingest_raw.extractor._extract_docling_generic",
        lambda path: (flag.__setitem__("generic", True), _fake_doc(path, "docling"))[1],
    )
    extract_document(p)
    assert flag["generic"]


# --- env / router integration -------------------------------------------


def test_router_upload_exts_include_pdf_and_extras() -> None:
    """``ALLOWED_UPLOAD_EXTS`` derived dall'env espone almeno PDF + docx."""
    from llm_wiki.api.routers.ingest import ALLOWED_UPLOAD_EXTS

    assert ".pdf" in ALLOWED_UPLOAD_EXTS
    # Default env include docx
    assert ".docx" in ALLOWED_UPLOAD_EXTS


def test_admin_uploads_raw_exts_include_pdf() -> None:
    from llm_wiki.api.admin_uploads import ALLOWED_RAW_EXTS

    assert ".pdf" in ALLOWED_RAW_EXTS


def test_supported_extensions_env_parse() -> None:
    """Smoke: env var → frozenset coerce correctly."""
    from llm_wiki.config import INGEST_SUPPORTED_EXTENSIONS

    assert ".pdf" in INGEST_SUPPORTED_EXTENSIONS
    assert all(ext.startswith(".") for ext in INGEST_SUPPORTED_EXTENSIONS)
    assert all(ext == ext.lower() for ext in INGEST_SUPPORTED_EXTENSIONS)
