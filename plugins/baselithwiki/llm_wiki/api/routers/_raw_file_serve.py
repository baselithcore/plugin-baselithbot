"""Raw-file listing and serving endpoints.

Extracted from :mod:`llm_wiki.api.routers.ingest` to stay within the
500-LOC file cap. The ``router`` fragment is wired into the main
``ingest`` module, which includes these routes automatically.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from llm_wiki import config
from llm_wiki.api.routers._ingest_helpers import (
    ALLOWED_UPLOAD_EXTS,
    _existing_source_slugs,
    _is_pdf_pending,
    _sanitize_filename,
)

router = APIRouter()

_RAW_MEDIA_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tiff": "image/tiff",
}


@router.get("/api/raw/files")
def list_raw_files() -> dict[str, Any]:
    """Files dropped under ``raw/`` + processing state per file.

    Each entry carries a ``processed`` flag computed against
    :func:`_existing_source_slugs` (which already strips ``.needs-review``
    and ``.new`` suffixes). The legacy ``count`` field stays as
    "total raw files"; ``pending_count`` is the subset that has NO source
    page on disk — the only number the UI should surface as "files
    waiting to be ingested" (a ``.needs-review.md`` is the ingest's
    output, not a pending state).
    """
    raw_dir = config.RAW_DIR
    if not raw_dir.exists():
        return {"count": 0, "pending_count": 0, "files": []}
    existing = _existing_source_slugs()
    out: list[dict[str, Any]] = []
    pending = 0
    for p in sorted(raw_dir.iterdir()):
        if not p.is_file() or p.suffix.lower() not in ALLOWED_UPLOAD_EXTS:
            continue
        try:
            stat = p.stat()
        except OSError:
            continue
        processed = not _is_pdf_pending(p, existing)
        if not processed:
            pending += 1
        out.append(
            {
                "name": p.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "processed": processed,
            }
        )
    return {"count": len(out), "pending_count": pending, "files": out}


@router.get("/api/raw/file/{filename}")
def serve_raw_file(filename: str) -> FileResponse:
    """Stream del file originale dentro ``raw/``.

    Sblocca click-to-source UX: il frontend recupera l'URL per ogni
    Source con ``source_file`` non vuoto e apre il PDF/DOCX/etc nel
    visualizzatore nativo del browser. Per PDF, supporta deep-link
    ``#page=N`` (rendered dal browser, non dal server).

    Security:
    - filename sanitizzato (no traversal, ASCII-only)
    - resolved path deve stare dentro RAW_DIR
    - solo estensioni allowed
    - read-only (raw/ è read-only per convenzione)

    NB: endpoint volutamente NON gated da ``require_user``. Le pagine
    sources sono linkate con ``<a href={rawFileUrl(...)}>`` (apertura
    in nuova tab native dal browser); l'access_token vive in JS e non
    viaggia automaticamente nell'header su navigation classica, quindi
    aggiungere ``require_user`` romperebbe il click-to-source. Hardening
    futuro: signed URL a tempo o session cookie. Difese attuali:
    sanitize filename + allowlist estensioni + path containment.
    """
    safe_name = _sanitize_filename(filename)
    raw_dir = config.RAW_DIR.resolve()
    target = (raw_dir / safe_name).resolve()
    try:
        target.relative_to(raw_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid path") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"raw file not found: {safe_name}")
    ext = target.suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(status_code=400, detail=f"extension `{ext}` not allowed")
    media_type = _RAW_MEDIA_TYPES.get(ext, "application/octet-stream")
    # ``inline`` content-disposition consente al browser di renderizzare
    # invece di forzare il download. PDF/HTML/IMG sono nativamente
    # renderizzabili; gli altri formati ricadono in download (browser
    # decide a runtime).
    return FileResponse(
        path=str(target),
        media_type=media_type,
        filename=safe_name,
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )


__all__ = ["router", "_RAW_MEDIA_TYPES"]
