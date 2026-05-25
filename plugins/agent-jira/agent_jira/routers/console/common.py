from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional

from fastapi import HTTPException, UploadFile, status

from agent_jira.cache import RedisTTLCache, TTLCache, create_redis_client
from agent_jira.cost_control import CostController
from agent_jira.vectorstore import index_docs
from agent_jira.tenant_context import get_tenant_cache_prefix
from agent_jira.config import (
    ANALYSIS_CACHE_ENABLED,
    ANALYSIS_CACHE_MAXSIZE,
    ANALYSIS_CACHE_TTL,
    CACHE_BACKEND,
    CACHE_REDIS_PREFIX,
    CACHE_REDIS_URL,
    MAX_UPLOAD_SIZE_BYTES,
)

TMP_UPLOAD_DIR = Path(tempfile.gettempdir()) / "agent-jira-uploads"
FRONTEND_INDEX = (
    Path(__file__).resolve().parents[2] / "static" / "frontend" / "index.html"
)
logger = logging.getLogger(__name__)

_analysis_cache: Optional[TTLCache] = None
_analysis_cache_client = None
_analysis_cache_logged = False


def _reset_analysis_cache_state() -> None:
    """Svuota la cache analisi (in-memory o Redis) e forza la ricreazione al prossimo accesso.
    Usata dagli endpoint di reset amministrativo.
    """
    global _analysis_cache, _analysis_cache_client, _analysis_cache_logged
    cache = _analysis_cache
    if cache is not None:
        try:
            cache.clear()
        except Exception as exc:
            logger.warning("Analysis cache clear failed: %s", exc)
    _analysis_cache = None
    _analysis_cache_client = None
    _analysis_cache_logged = False


def _get_project_planner():
    import importlib

    ui_services = importlib.import_module("app.ui.services")
    planner = getattr(ui_services.get_chat_service(), "project_planner", None)
    if planner is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Project Planner disabilitato in configurazione.",
        )
    return planner


async def _run_incremental_index() -> int:
    """
    Esegue l'indicizzazione incrementale.

    Il tracking costi per-request è sospeso: questa operazione può essere
    lanciata da un BackgroundTask che eredita il contextvar della request,
    ma il budget per-request non è dimensionato per operazioni batch.
    """
    with CostController.unbounded(reason="incremental-index"):
        return await index_docs(incremental=True)


def _get_analysis_cache() -> Optional[TTLCache]:
    global _analysis_cache, _analysis_cache_client, _analysis_cache_logged
    if not ANALYSIS_CACHE_ENABLED:
        if not _analysis_cache_logged:
            logger.info("Analysis cache disabled")
            _analysis_cache_logged = True
        return None
    if _analysis_cache is not None:
        return _analysis_cache
    if CACHE_BACKEND == "redis":
        _analysis_cache_client = _analysis_cache_client or create_redis_client(
            CACHE_REDIS_URL
        )
        _analysis_cache = RedisTTLCache(
            _analysis_cache_client,
            prefix=get_tenant_cache_prefix(f"{CACHE_REDIS_PREFIX}:analysis"),
            default_ttl=ANALYSIS_CACHE_TTL,
        )
        if not _analysis_cache_logged:
            logger.info(
                "Analysis cache enabled (redis) url=%s prefix=%s ttl=%ss",
                CACHE_REDIS_URL,
                f"{CACHE_REDIS_PREFIX}:analysis",
                ANALYSIS_CACHE_TTL,
            )
    else:
        _analysis_cache = TTLCache(
            maxsize=ANALYSIS_CACHE_MAXSIZE, ttl=ANALYSIS_CACHE_TTL
        )
        if not _analysis_cache_logged:
            logger.info(
                "Analysis cache enabled (local) maxsize=%s ttl=%ss",
                ANALYSIS_CACHE_MAXSIZE,
                ANALYSIS_CACHE_TTL,
            )
    _analysis_cache_logged = True
    return _analysis_cache


def _prompt_fingerprint(prompt: Optional[str]) -> str:
    normalized = (prompt or "").strip()
    if not normalized:
        return "noprompt"
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


def _cache_key_from_metadata(
    metadata: Mapping[str, Any], prompt: Optional[str] = None
) -> Optional[str]:
    # Includi il tenant_id nella chiave per isolare le cache in-memory
    # (evita che un TTLCache locale serva risultati cross-tenant).
    from agent_jira.tenant_context import get_current_tenant_id

    tenant_scope = get_current_tenant_id() or "_default"
    for key_name in (
        "kb_label",
        "kb_path",
        "doc_label",
        "path",
        "filename",
        "file_name",
        "display_name",
    ):
        val = metadata.get(key_name)
        if val:
            return f"analysis:t:{tenant_scope}:{val}:{_prompt_fingerprint(prompt)}"
    return None


def _human_size_from_kb(size_kb: float | int | None) -> Optional[str]:
    if size_kb is None:
        return None
    try:
        size = float(size_kb)
    except (TypeError, ValueError):
        return None
    if size >= 1024:
        return f"{size / 1024:.1f} MB ({size:.1f} KB)"
    return f"{size:.1f} KB"


def _doc_type_label(doc_type: Optional[str], extension: Optional[str] = None) -> str:
    doc_type = (doc_type or "").lower().strip()
    ext = (extension or "").lstrip(".").lower()
    if doc_type == "pdf" or ext == "pdf":
        return "PDF"
    if doc_type == "word" or ext in {"doc", "docx"}:
        return "Word"
    if doc_type == "spreadsheet" or ext in {"xls", "xlsx"}:
        return "Excel"
    if doc_type == "presentation" or ext in {"ppt", "pptx"}:
        return "PowerPoint"
    if doc_type == "markdown" or ext in {"md", "markdown"}:
        return "Markdown"
    if doc_type == "image" or ext in {
        "png",
        "jpg",
        "jpeg",
        "gif",
        "webp",
        "tif",
        "tiff",
    }:
        return "Immagine"
    return "Documento"


async def _persist_upload(file: UploadFile) -> Path:
    TMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "document").suffix or ".bin"
    handle, tmp_path = tempfile.mkstemp(
        prefix="console_upload_", suffix=suffix, dir=TMP_UPLOAD_DIR
    )
    try:
        total_size = 0
        with os.fdopen(handle, "wb") as buffer:
            while True:
                chunk = await file.read(64 * 1024)  # 64 KB chunks, non-blocking
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    buffer.close()
                    Path(tmp_path).unlink(missing_ok=True)
                    max_mb = MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File troppo grande. Dimensione massima: {max_mb:.0f} MB.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    return Path(tmp_path)


def _validate_temp_path(raw_path: str) -> Path:
    try:
        candidate = Path(raw_path).resolve()
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Percorso file non valido.")
    root = TMP_UPLOAD_DIR.resolve()
    if not str(candidate).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Percorso file non ammesso.")
    if not candidate.exists():
        raise HTTPException(
            status_code=400, detail="Il file temporaneo non esiste più."
        )
    return candidate
