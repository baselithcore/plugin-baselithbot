"""Endpoint ``GET /api/raw/file/{filename}`` — security + happy path.

Test diretti su FastAPI TestClient, bypassano loopback guard (il
router public è esposto a tutti i client autenticati).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client_and_raw_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[TestClient, Path]:
    """Crea raw/ + monta solo il router ingest. Niente Postgres, niente
    Qdrant — il endpoint è I/O su file."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    monkeypatch.setattr("llm_wiki.config.RAW_DIR", raw_dir)

    # Import dopo monkeypatch così config è patchato
    from llm_wiki.api.routers.ingest import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app), raw_dir


def test_serve_pdf_happy_path(client_and_raw_dir: tuple[TestClient, Path]) -> None:
    client, raw_dir = client_and_raw_dir
    (raw_dir / "contract.pdf").write_bytes(b"%PDF-1.4\nfake")
    r = client.get("/api/raw/file/contract.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "inline" in r.headers.get("content-disposition", "")
    assert r.content == b"%PDF-1.4\nfake"


def test_serve_docx_happy_path(client_and_raw_dir: tuple[TestClient, Path]) -> None:
    client, raw_dir = client_and_raw_dir
    (raw_dir / "doc.docx").write_bytes(b"PKfake")
    r = client.get("/api/raw/file/doc.docx")
    assert r.status_code == 200
    assert "officedocument.wordprocessingml" in r.headers["content-type"]


def test_serve_missing_file_returns_404(client_and_raw_dir: tuple[TestClient, Path]) -> None:
    client, _ = client_and_raw_dir
    r = client.get("/api/raw/file/nope.pdf")
    assert r.status_code == 404


def test_serve_traversal_blocked(client_and_raw_dir: tuple[TestClient, Path]) -> None:
    """``../etc/passwd`` deve essere rifiutato dal sanitize + path resolve."""
    client, _ = client_and_raw_dir
    # FastAPI auto-decodifica %2F, ma il sanitize strappa "/" → resta solo
    # "etcpasswd" o simile. Test che la richiesta NON colpisca /etc/passwd.
    for evil in ["..%2Fetc%2Fpasswd", "...%2F...%2Fetc%2Fpasswd", "etc%2Fpasswd"]:
        r = client.get(f"/api/raw/file/{evil}")
        assert r.status_code in (400, 404)


def test_serve_disallowed_extension(client_and_raw_dir: tuple[TestClient, Path]) -> None:
    """File esistente ma estensione non in allowlist → 400."""
    client, raw_dir = client_and_raw_dir
    (raw_dir / "script.sh").write_bytes(b"#!/bin/sh\nls\n")
    r = client.get("/api/raw/file/script.sh")
    # Il sanitize accetta .sh come ext? Lasciamo allowlist a decidere.
    # In ogni caso, 400 o 404 sono accettabili — mai 200.
    assert r.status_code in (400, 404)


def test_serve_html_inline(client_and_raw_dir: tuple[TestClient, Path]) -> None:
    client, raw_dir = client_and_raw_dir
    (raw_dir / "page.html").write_bytes(b"<html><body>hi</body></html>")
    r = client.get("/api/raw/file/page.html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_serve_image_png(client_and_raw_dir: tuple[TestClient, Path]) -> None:
    client, raw_dir = client_and_raw_dir
    (raw_dir / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    r = client.get("/api/raw/file/diagram.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


def test_serve_invalid_filename_empty(client_and_raw_dir: tuple[TestClient, Path]) -> None:
    client, _ = client_and_raw_dir
    r = client.get("/api/raw/file/")
    assert r.status_code in (404, 405)


def test_serve_filename_with_null_byte_rejected(
    client_and_raw_dir: tuple[TestClient, Path],
) -> None:
    client, _ = client_and_raw_dir
    # NULL byte rifiutato dal sanitize a monte del filesystem.
    r = client.get("/api/raw/file/file%00.pdf")
    assert r.status_code in (400, 404)
