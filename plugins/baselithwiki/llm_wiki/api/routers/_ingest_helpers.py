"""Ingest helpers: constants, filename sanitisation, raw-dir utilities.

Extracted from :mod:`llm_wiki.api.routers.ingest` to stay within the
500-LOC file cap. All symbols are re-exported by the parent module so
existing imports remain unaffected.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from pathlib import Path

from fastapi import HTTPException

from llm_wiki import config
from llm_wiki.config import INGEST_SUPPORTED_EXTENSIONS
from llm_wiki.ingest_raw.jobs import get_registry
from llm_wiki.ingest_raw.planner import slug_from_raw
from llm_wiki.ingest_raw.runner import spawn_worker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Upload constants
# ---------------------------------------------------------------------------

# Multi-format: estensioni accettate dal raw/ scan e dall'upload API.
# Derived dall'env ``INGEST_SUPPORTED_EXTENSIONS``. PDF resta sempre
# in lista anche se l'env non lo include (fallback safety).
ALLOWED_UPLOAD_EXTS: set[str] = set(INGEST_SUPPORTED_EXTENSIONS) | {".pdf"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_SAFE_FILENAME_RE = re.compile(r"[^a-z0-9._-]+")


# ---------------------------------------------------------------------------
# Filename sanitisation
# ---------------------------------------------------------------------------


def _sanitize_filename(name: str) -> str:
    if not name or "\x00" in name:
        raise HTTPException(status_code=400, detail="invalid filename")
    name = Path(name).name
    norm = unicodedata.normalize("NFKD", name)
    ascii_ = norm.encode("ascii", "ignore").decode("ascii")
    base, _, ext = ascii_.rpartition(".")
    if not base:
        base = ascii_
        ext = ""
    base = _SAFE_FILENAME_RE.sub("-", base.lower()).strip("-")
    ext = ext.lower()
    if not base:
        raise HTTPException(status_code=400, detail="filename empty after sanitisation")
    if not ext or f".{ext}" not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"extension `.{ext}` not allowed. Allowed: {sorted(ALLOWED_UPLOAD_EXTS)}",
        )
    return f"{base}.{ext}"


# ---------------------------------------------------------------------------
# Domain-pack guard
# ---------------------------------------------------------------------------


def _require_active_pack() -> None:
    """Refuse ingest when no Domain Pack is active.

    Without an active pack, ``COLLECTION_NAME`` falls back to the bare
    ``"wiki"`` default and any vectors written here would be orphaned the
    moment the wizard activates a real domain (which switches the
    collection to ``"<domain>-wiki"``). Fail-fast with 409 instead.
    """
    import os

    if not os.getenv("APP_DOMAIN", "").strip():
        raise HTTPException(
            status_code=409,
            detail="no Domain Pack is active; complete the setup wizard before ingesting.",
        )


# ---------------------------------------------------------------------------
# Raw-dir slug helpers
# ---------------------------------------------------------------------------


def _existing_source_slugs() -> set[str]:
    """Set of source-page slugs already present in ``wiki/sources/``.

    Page filenames are kebabized by the planner (`slug_from_raw`) so the
    raw filename `foo_bar-44.pdf` lands at `wiki/sources/foo-bar-44.md`.
    Comparing raw stem directly produced false negatives (`_` vs `-`,
    duplicated dashes, etc.) and looped `autostart_pending_ingest` on
    every boot. Strip critic suffixes so `.needs-review.md` / `.new.md`
    still count as "already processed".
    """
    sources_dir = config.WIKI_DIR / "sources"
    if not sources_dir.exists():
        return set()
    out: set[str] = set()
    for p in sources_dir.rglob("*.md"):
        stem = p.stem.lower()
        for suffix in (".needs-review", ".new"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        out.add(stem)
    return out


def _is_pdf_pending(raw_path: Path, existing_slugs: set[str]) -> bool:
    return slug_from_raw(str(raw_path)) not in existing_slugs


# ---------------------------------------------------------------------------
# Auto-ingest on startup
# ---------------------------------------------------------------------------


async def autostart_pending_ingest() -> None:
    """Spawn ingest workers for any PDF in raw/ without a wiki source page.

    Idempotent: runs once per boot. The pipeline's own filename lock
    prevents double-processing if the user manually triggers an ingest
    in parallel.
    """
    import os as _os

    if not _os.getenv("APP_DOMAIN", "").strip():
        logger.info("[startup] auto-ingest skipped: no Domain Pack active")
        return
    raw_dir = config.RAW_DIR
    if not raw_dir.exists():
        return
    existing = _existing_source_slugs()
    targets = [
        p
        for p in sorted(raw_dir.iterdir())
        if p.is_file()
        and p.suffix.lower() in ALLOWED_UPLOAD_EXTS
        and _is_pdf_pending(p, existing)
    ]
    if not targets:
        return
    options = {
        "overwrite": False,
        "reindex": True,
        "dry_run": False,
        "only_source_page": False,
    }
    registry = get_registry()
    registry.set_loop(asyncio.get_running_loop())
    logger.info("[startup] auto-ingest: %d pending PDF(s) in raw/", len(targets))
    for t in targets:
        try:
            job = registry.create(filename=t.name, options=options)
            spawn_worker(job, t, options)
            logger.info("[startup] auto-ingest spawned job=%s file=%s", job.id, t.name)
        except Exception as exc:
            logger.warning("[startup] auto-ingest failed for %s: %s", t.name, exc)


__all__ = [
    "ALLOWED_UPLOAD_EXTS",
    "MAX_UPLOAD_BYTES",
    "_SAFE_FILENAME_RE",
    "_sanitize_filename",
    "_require_active_pack",
    "_existing_source_slugs",
    "_is_pdf_pending",
    "autostart_pending_ingest",
]
