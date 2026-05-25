"""System / runtime configuration endpoints (read-only + safe admin actions).

Exposes non-secret runtime config, storage stats, LLM connectivity probe and
cache metric reset. All endpoints are RBAC-gated under the `system` resource.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.security import Principal
from ..db import get_session
from ..db.models import (
    AuditLog,
    Document,
    DocumentChunk,
    EmbeddingCache,
    Policy,
    Report,
    Setting,
    User,
    VerdictCache,
)
from ..services.cache import get_metrics, reset_metrics
from .deps import require

router = APIRouter()


# --------------------------- schemas ---------------------------


class RuntimeInfo(BaseModel):
    app_name: str
    version: str
    debug: bool
    llm_base_url: str
    llm_primary_model: str
    llm_fallback_model: str
    llm_temperature: float
    llm_top_p: float
    embedding_model: str
    ocr_engine: str
    vector_backend: str
    db_backend: str
    multitenant_enabled: bool
    db_encryption_enabled: bool
    oidc_enabled: bool
    retention_default_days: int


class StorageStats(BaseModel):
    db_path: str
    db_size_bytes: int
    chroma_path: str
    chroma_size_bytes: int
    storage_root: str
    storage_size_bytes: int
    documents: int
    chunks: int
    reports: int
    policies: int
    audit_entries: int
    users: int
    verdict_cache: int
    embedding_cache: int


class LLMProbeResult(BaseModel):
    ok: bool
    base_url: str
    latency_ms: int
    models: list[str] = Field(default_factory=list)
    error: str | None = None


class RetentionUpdate(BaseModel):
    days: int = Field(ge=1, le=3650)


class RetentionInfo(BaseModel):
    days: int
    source: str  # "config" | "override"


# --------------------------- helpers ---------------------------


def _path_size(p: Path) -> int:
    if not p.exists():
        return 0
    if p.is_file():
        try:
            return p.stat().st_size
        except OSError:
            return 0
    total = 0
    for child in p.rglob("*"):
        try:
            if child.is_file():
                total += child.stat().st_size
        except OSError:
            continue
    return total


async def _count(db: AsyncSession, table: Any) -> int:
    return int((await db.execute(select(func.count()).select_from(table))).scalar_one())


# --------------------------- endpoints ---------------------------


@router.get("/system/runtime", response_model=RuntimeInfo)
async def runtime_info(
    _: Principal = Depends(require("system", "read")),
) -> RuntimeInfo:
    return RuntimeInfo(
        app_name=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        llm_base_url=settings.llm_base_url,
        llm_primary_model=settings.llm_primary_model,
        llm_fallback_model=settings.llm_fallback_model,
        llm_temperature=settings.llm_temperature,
        llm_top_p=settings.llm_top_p,
        embedding_model=settings.embedding_model,
        ocr_engine=settings.ocr_engine,
        vector_backend=settings.vector_backend,
        db_backend=settings.db_backend,
        multitenant_enabled=settings.multitenant_enabled,
        db_encryption_enabled=settings.db_encryption_enabled,
        oidc_enabled=bool(settings.oidc_issuer),
        retention_default_days=await _resolve_retention_days(),
    )


@router.get("/system/storage", response_model=StorageStats)
async def storage_stats(
    _: Principal = Depends(require("system", "read")),
    db: AsyncSession = Depends(get_session),
) -> StorageStats:
    db_path = Path(settings.db_path)
    chroma_path = Path(settings.chroma_persist_dir)
    root_path = Path(settings.storage_root)

    db_size, chroma_size, root_size = await asyncio.to_thread(
        lambda: (_path_size(db_path), _path_size(chroma_path), _path_size(root_path)),
    )

    return StorageStats(
        db_path=str(db_path),
        db_size_bytes=db_size,
        chroma_path=str(chroma_path),
        chroma_size_bytes=chroma_size,
        storage_root=str(root_path),
        storage_size_bytes=root_size,
        documents=await _count(db, Document),
        chunks=await _count(db, DocumentChunk),
        reports=await _count(db, Report),
        policies=await _count(db, Policy),
        audit_entries=await _count(db, AuditLog),
        users=await _count(db, User),
        verdict_cache=await _count(db, VerdictCache),
        embedding_cache=await _count(db, EmbeddingCache),
    )


@router.post("/system/llm/probe", response_model=LLMProbeResult)
async def llm_probe(
    _: Principal = Depends(require("system", "read")),
) -> LLMProbeResult:
    base = settings.llm_base_url.rstrip("/")
    url = f"{base}/models"
    started = datetime.now(UTC)
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(url, headers={"Authorization": "Bearer local"})
        elapsed = int((datetime.now(UTC) - started).total_seconds() * 1000)
        if res.status_code >= 400:
            return LLMProbeResult(
                ok=False,
                base_url=settings.llm_base_url,
                latency_ms=elapsed,
                error=f"HTTP {res.status_code}: {res.text[:200]}",
            )
        data = res.json()
        models = [m.get("id", "") for m in (data.get("data") or []) if isinstance(m, dict)]
        return LLMProbeResult(
            ok=True,
            base_url=settings.llm_base_url,
            latency_ms=elapsed,
            models=[m for m in models if m],
        )
    except (httpx.HTTPError, ValueError) as exc:
        elapsed = int((datetime.now(UTC) - started).total_seconds() * 1000)
        return LLMProbeResult(
            ok=False,
            base_url=settings.llm_base_url,
            latency_ms=elapsed,
            error=str(exc) or exc.__class__.__name__,
        )


@router.get("/system/cache", response_model=dict)
async def cache_state(
    _: Principal = Depends(require("system", "read")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return {
        "metrics": get_metrics(),
        "verdict_rows": await _count(db, VerdictCache),
        "embedding_rows": await _count(db, EmbeddingCache),
    }


@router.post("/system/cache/reset")
async def cache_reset(
    _: Principal = Depends(require("system", "admin")),
) -> dict[str, Any]:
    reset_metrics()
    return {"ok": True, "metrics": get_metrics()}


@router.get("/system/retention", response_model=RetentionInfo)
async def retention_get(
    _: Principal = Depends(require("system", "read")),
    db: AsyncSession = Depends(get_session),
) -> RetentionInfo:
    row = await db.get(Setting, "retention_default_days")
    if row is not None:
        try:
            return RetentionInfo(days=int(row.value), source="override")
        except ValueError:
            pass
    return RetentionInfo(days=settings.retention_default_days, source="config")


@router.put("/system/retention", response_model=RetentionInfo)
async def retention_set(
    body: RetentionUpdate,
    _: Principal = Depends(require("system", "admin")),
    db: AsyncSession = Depends(get_session),
) -> RetentionInfo:
    row = await db.get(Setting, "retention_default_days")
    if row is None:
        db.add(Setting(key="retention_default_days", value=str(body.days)))
    else:
        row.value = str(body.days)
        row.updated_at = datetime.now(UTC)
    await db.commit()
    return RetentionInfo(days=body.days, source="override")


async def _resolve_retention_days() -> int:
    """Resolve retention without holding the request session."""
    from ..db import get_session as _gs

    async for db in _gs():
        row = await db.get(Setting, "retention_default_days")
        if row is not None:
            try:
                return int(row.value)
            except ValueError:
                break
        break
    return settings.retention_default_days
