"""Ingest pipeline endpoints: full vault, single file, raw uploads, jobs.

The raw-upload subset (``/api/ingest/raw*``) is the surface the wizard's
"Documenti" step relies on. Auto-ingest of pending PDFs at startup is
also exposed as a helper here so :mod:`main` can call it from the
lifespan hook without re-implementing the dedup logic.

Helpers and constants are in :mod:`_ingest_helpers`; raw-file listing
and serving routes live in :mod:`_raw_file_serve` and are included via
``router.include_router`` so external imports of ``router`` pick up all
routes transparently.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm_wiki import config
from llm_wiki.api.routers._ingest_helpers import (
    ALLOWED_UPLOAD_EXTS,
    MAX_UPLOAD_BYTES,
    _existing_source_slugs,
    _is_pdf_pending,
    _require_active_pack,
    _sanitize_filename,
    autostart_pending_ingest,
)
from llm_wiki.api.routers._raw_file_serve import router as _raw_router
from llm_wiki.ingest_raw.jobs import get_registry, load_recent_jobs
from llm_wiki.ingest_raw.runner import spawn_worker
from llm_wiki.wiki.ingest import ingest_all, ingest_file

logger = logging.getLogger(__name__)


def _require_ingest_or_setup_mode(request: Request) -> None:
    """Gate writeable ingest endpoints.

    - Postgres OFF (setup mode / dev senza auth): allow.
      Il wizard "Documenti" gira con loopback in first-boot e Postgres
      può essere ancora offline. Mantenere la rotta accessibile evita
      regressioni sul flow di onboarding.
    - Postgres ON: richiede permesso ``ingest.run``. Seed 008 lo dà
      solo a ``superuser`` / ``admin`` — moderator/user NON possono
      uploadare/ingestare nuovi documenti.
    """
    if not config.POSTGRES_ENABLED:
        return
    from llm_wiki.auth.dependencies import require_permission

    require_permission("ingest.run")(request)


router = APIRouter()

# Pull in raw-file listing / serving routes from the sibling module so
# all routes are reachable through this single ``router`` object as before.
router.include_router(_raw_router)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class IngestFileRequest(BaseModel):
    path: str


# ---------------------------------------------------------------------------
# Routes — full vault / single file
# ---------------------------------------------------------------------------


@router.post("/api/ingest", dependencies=[Depends(_require_ingest_or_setup_mode)])
async def api_ingest_all(concurrency: int = 4, force: bool = False) -> dict[str, Any]:
    """Walk dell'intero ``wiki/`` + indicizzazione batch.

    ``force=true`` bypassa il content-hash cache: utile dopo un wipe del
    collection Qdrant quando ``.cache/state/`` ha ancora gli hash della
    sessione precedente e farebbe skip su pagine in realtà non indicizzate.
    """
    _require_active_pack()
    return await ingest_all(concurrency=concurrency, force=force)


@router.post("/api/ingest/file", dependencies=[Depends(_require_ingest_or_setup_mode)])
async def api_ingest_file(req: IngestFileRequest) -> dict[str, Any]:
    _require_active_pack()
    # Hardening: restringiamo il path a `RAW_DIR`. La versione precedente
    # accettava qualunque path assoluto o relativo a WIKI_ROOT, lasciando
    # ingestare arbitrarily anche file fuori dai sorgenti pre-vetted.
    raw_root = config.RAW_DIR.resolve()
    path = Path(req.path).expanduser()
    if not path.is_absolute():
        path = (raw_root / path).resolve()
    else:
        path = path.resolve()
    try:
        path.relative_to(raw_root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"path must live inside raw/ ({raw_root})",
        ) from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"file not found: {path}")
    if path.suffix.lower() not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"extension `{path.suffix}` not allowed",
        )
    return await ingest_file(path)


# ---------------------------------------------------------------------------
# Routes — raw upload
# ---------------------------------------------------------------------------


@router.post("/api/ingest/raw", dependencies=[Depends(_require_ingest_or_setup_mode)])
async def api_ingest_raw(
    file: UploadFile = File(...),
    overwrite: bool = Form(False),
    reindex: bool = Form(True),
    dry_run: bool = Form(False),
    only_source_page: bool = Form(False),
    replace_existing: bool = Form(False),
) -> dict[str, Any]:
    _require_active_pack()
    if file.filename is None:
        raise HTTPException(status_code=400, detail="missing filename")

    safe_name = _sanitize_filename(file.filename)

    raw_dir = config.RAW_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = (raw_dir / safe_name).resolve()
    try:
        target.relative_to(raw_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid path") from exc

    if target.exists() and not replace_existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"file `{safe_name}` already in raw/. "
                f"Send `replace_existing=true` to overwrite the RAW."
            ),
        )

    bytes_read = 0
    try:
        with target.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                bytes_read += len(chunk)
                if bytes_read > MAX_UPLOAD_BYTES:
                    out.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"file too large (> {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"upload failed: {exc}") from exc

    options = {
        "overwrite": overwrite,
        "reindex": reindex,
        "dry_run": dry_run,
        "only_source_page": only_source_page,
    }
    registry = get_registry()
    registry.set_loop(asyncio.get_running_loop())
    job = registry.create(filename=safe_name, options=options)
    spawn_worker(job, target, options)

    return {
        "job_id": job.id,
        "filename": safe_name,
        "size": bytes_read,
        "status": job.status,
        "options": options,
    }


@router.get("/api/ingest/raw/pending")
def list_pending_raw() -> dict[str, Any]:
    """Return PDFs in ``raw/`` that don't have a corresponding source page.

    Used by the empty-state banner to detect "wizard-deposited PDFs not
    yet processed". Matching is by stem against the ``wiki/sources/``
    directory; pages live elsewhere in the engine but `sources/` is the
    canonical destination of raw-derived pages.
    """
    raw_dir = config.RAW_DIR
    if not raw_dir.exists():
        return {"count": 0, "files": []}

    existing_slugs = _existing_source_slugs()

    pending: list[dict[str, Any]] = []
    for p in sorted(raw_dir.iterdir()):
        if not p.is_file() or p.suffix.lower() not in ALLOWED_UPLOAD_EXTS:
            continue
        if not _is_pdf_pending(p, existing_slugs):
            continue
        try:
            stat = p.stat()
        except OSError:
            continue
        pending.append(
            {"name": p.name, "size": stat.st_size, "modified": stat.st_mtime}
        )
    return {"count": len(pending), "files": pending}


@router.post(
    "/api/ingest/raw/from-disk",
    dependencies=[Depends(_require_ingest_or_setup_mode)],
)
async def api_ingest_raw_from_disk(
    filename: str | None = None,
    overwrite: bool = False,
    reindex: bool = True,
) -> dict[str, Any]:
    """Spawn the full ingest pipeline on a PDF *already* in ``raw/``.

    Use case: the wizard's "Documenti" step deposits files into the
    new tenant's ``<vault>/raw/``. After restart the user wants to
    ingest them without re-uploading. ``filename=null`` ingests every
    PDF in raw/ that has no matching wiki/sources/<slug>.md yet.
    """
    _require_active_pack()
    raw_dir = config.RAW_DIR
    if not raw_dir.exists():
        return {"started": 0, "jobs": []}

    targets: list[Path] = []
    if filename:
        safe = _sanitize_filename(filename)
        candidate = (raw_dir / safe).resolve()
        try:
            candidate.relative_to(raw_dir.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid path") from exc
        if not candidate.is_file():
            raise HTTPException(status_code=404, detail=f"raw file not found: {safe}")
        targets = [candidate]
    else:
        for p in sorted(raw_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in ALLOWED_UPLOAD_EXTS:
                targets.append(p)

    if not targets:
        return {"started": 0, "jobs": []}

    options = {
        "overwrite": overwrite,
        "reindex": reindex,
        "dry_run": False,
        "only_source_page": False,
    }
    registry = get_registry()
    registry.set_loop(asyncio.get_running_loop())
    started = []
    for t in targets:
        job = registry.create(filename=t.name, options=options)
        spawn_worker(job, t, options)
        started.append({"job_id": job.id, "filename": t.name})
    return {"started": len(started), "jobs": started}


# ---------------------------------------------------------------------------
# Routes — job management
# ---------------------------------------------------------------------------


@router.get("/api/ingest/raw/jobs")
def list_jobs(limit: int = 20) -> dict[str, Any]:
    registry = get_registry()
    live = [j.to_dict() for j in registry.list_jobs(limit=limit)]
    if live:
        return {"count": len(live), "jobs": live}
    persisted = load_recent_jobs(limit=limit)
    return {"count": len(persisted), "jobs": persisted}


@router.get("/api/ingest/raw/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = get_registry().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    return job.to_dict()


@router.get("/api/ingest/raw/jobs/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    registry = get_registry()
    registry.set_loop(asyncio.get_running_loop())
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")

    async def generator() -> Any:
        try:
            async for event in registry.subscribe(job_id):
                yield json.dumps(event, ensure_ascii=False) + "\n"
            final = registry.get(job_id)
            if final is not None:
                yield (
                    json.dumps({"type": "final", **final.to_dict()}, ensure_ascii=False)
                    + "\n"
                )
        except asyncio.CancelledError:
            raise

    return StreamingResponse(
        generator(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = [
    "router",
    "autostart_pending_ingest",
    "IngestFileRequest",
    "_require_ingest_or_setup_mode",
]
