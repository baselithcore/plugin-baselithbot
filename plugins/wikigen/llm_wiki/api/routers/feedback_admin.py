"""Feedback admin endpoints — monitor + triage + moderate user feedback.

Surface
-------

``GET    /api/admin/feedback``                — paginated list (filters)
``GET    /api/admin/feedback/stats``          — KPI dashboard (totals, %, trend, anomaly)
``GET    /api/admin/feedback/stats/sources``  — per-document downvote correlation
``GET    /api/admin/feedback/meta``           — vocabolari (status, suggested tags)
``GET    /api/admin/feedback/export.csv``     — full-filter CSV export
``GET    /api/admin/feedback/{fid}``          — detail (Q/A + sources + triage state)
``PATCH  /api/admin/feedback/{fid}``          — triage (status, tags, resolution_note)
``DELETE /api/admin/feedback/{fid}``          — moderate (hard delete)

Gating
------

- ``feedback.read``    → list/stats/detail/CSV/meta (admin + moderator)
- ``feedback.triage``  → PATCH triage (admin + moderator; mig 018)
- ``feedback.delete``  → DELETE (admin + moderator via seed mig 007/008)

Audit kinds: ``feedback.deleted``, ``feedback.triaged``.

Tutto è tenant-scoped via RLS (mig 006). Niente bypass cross-tenant qui.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from llm_wiki import config
from llm_wiki.auth.audit import write_event
from llm_wiki.auth.dependencies import require_permission
from llm_wiki.auth.permissions import Permission

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/admin/feedback",
    tags=["admin", "feedback"],
)


# --- models ---------------------------------------------------------------


class FeedbackItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    user_id: str | None = None
    user_email: str | None = None
    message_id: str | None = None
    # Deep-link UX: dato il message_id, il backend risolve la
    # conversation parent e la espone qui — il FE costruisce l'URL
    # ``/?conversation=<id>`` senza un secondo round-trip.
    conversation_id: str | None = None
    rating: str
    reason: str | None = None
    question: str | None = None
    answer: str | None = None
    sources: list[dict[str, Any]] | None = None
    created_at: str | None = None
    # Triage workflow (mig 018).
    status: str = "open"
    tags: list[str] = Field(default_factory=list)
    resolution_note: str | None = None
    resolved_by_user_id: str | None = None
    resolved_by_email: str | None = None
    resolved_at: str | None = None


class FeedbackListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[FeedbackItem]
    total: int
    limit: int
    offset: int


class TrendBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bucket: str
    up: int
    down: int


class TopQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    count: int
    down: int


class StatusBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")
    open: int = 0
    triaged: int = 0
    resolved: int = 0
    dismissed: int = 0


class AnomalySignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: str
    down_24h: int
    down_rate_24h: float
    down_rate_baseline: float
    ratio: float
    message: str


class FeedbackStatsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    up: int
    down: int
    positive_rate: float = Field(ge=0.0, le=1.0)
    with_reason: int
    unique_users: int
    trend: list[TrendBucket]
    top_questions: list[TopQuestion]
    status_breakdown: StatusBreakdown = Field(default_factory=StatusBreakdown)
    anomaly: AnomalySignal | None = None


class SourceStat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    title: str
    total: int
    up: int
    down: int
    down_rate: float


class TriageBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str | None = Field(
        default=None,
        pattern="^(open|triaged|resolved|dismissed)$",
    )
    tags: list[str] | None = Field(default=None, max_length=20)
    resolution_note: str | None = Field(default=None, max_length=2000)


# --- helpers --------------------------------------------------------------


def _require_postgres() -> None:
    if not config.POSTGRES_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback admin richiede Postgres attivo.",
        )


def _parse_dt(raw: str | None, *, name: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{name}: timestamp ISO-8601 atteso ({raw!r}).",
        ) from exc


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


# --- endpoints ------------------------------------------------------------


@router.get("/meta")
def meta_endpoint(
    actor: dict = Depends(
        require_permission(Permission.FEEDBACK_READ, rate_limit="admin")
    ),
) -> dict[str, Any]:
    """Vocabolari client-side: status validi + tag suggeriti. Evita
    hard-coded enum lato FE che drifterebbe rispetto al DB."""
    _require_postgres()
    from llm_wiki.db.feedback import ALLOWED_STATUSES, SUGGESTED_TAGS

    return {
        "statuses": sorted(ALLOWED_STATUSES),
        "suggested_tags": list(SUGGESTED_TAGS),
    }


@router.get("", response_model=FeedbackListResponse)
def list_feedback_endpoint(
    rating: str | None = Query(default=None, pattern="^(up|down)$"),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(open|triaged|resolved|dismissed)$",
    ),
    tag: str | None = Query(default=None, max_length=64),
    user_id: str | None = Query(default=None),
    message_id: str | None = Query(default=None),
    since: str | None = Query(default=None, description="ISO-8601"),
    until: str | None = Query(default=None, description="ISO-8601"),
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    actor: dict = Depends(
        require_permission(Permission.FEEDBACK_READ, rate_limit="admin")
    ),
) -> FeedbackListResponse:
    _require_postgres()
    from llm_wiki.db.feedback import list_feedback_admin

    rows, total = list_feedback_admin(
        rating=rating,
        user_id=user_id,
        message_id=message_id,
        since=_parse_dt(since, name="since"),
        until=_parse_dt(until, name="until"),
        search=search,
        status=status_filter,
        tag=tag,
        limit=limit,
        offset=offset,
    )
    return FeedbackListResponse(
        items=[FeedbackItem(**r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=FeedbackStatsResponse)
def stats_endpoint(
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    bucket: str = Query(default="day", pattern="^(hour|day|week)$"),
    actor: dict = Depends(
        require_permission(Permission.FEEDBACK_READ, rate_limit="admin")
    ),
) -> FeedbackStatsResponse:
    _require_postgres()
    from llm_wiki.db.feedback import feedback_stats

    data = feedback_stats(
        since=_parse_dt(since, name="since"),
        until=_parse_dt(until, name="until"),
        bucket=bucket,
    )
    return FeedbackStatsResponse(**data)


@router.get("/stats/sources", response_model=list[SourceStat])
def stats_sources_endpoint(
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    actor: dict = Depends(
        require_permission(Permission.FEEDBACK_READ, rate_limit="admin")
    ),
) -> list[SourceStat]:
    """Per-document down-rate. Chiude il loop tra moderazione e ingest:
    documenti con down_rate alto sono candidati a re-ingest / refresh."""
    _require_postgres()
    from llm_wiki.db.feedback import feedback_source_stats

    rows = feedback_source_stats(
        since=_parse_dt(since, name="since"),
        until=_parse_dt(until, name="until"),
        limit=limit,
    )
    return [SourceStat(**r) for r in rows]


@router.get("/export.csv")
def export_csv_endpoint(
    rating: str | None = Query(default=None, pattern="^(up|down)$"),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(open|triaged|resolved|dismissed)$",
    ),
    tag: str | None = Query(default=None, max_length=64),
    user_id: str | None = Query(default=None),
    message_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=1000, ge=1, le=10000),
    actor: dict = Depends(
        require_permission(Permission.FEEDBACK_READ, rate_limit="admin")
    ),
) -> StreamingResponse:
    _require_postgres()
    from llm_wiki.db.feedback import list_feedback_admin

    rows, _total = list_feedback_admin(
        rating=rating,
        user_id=user_id,
        message_id=message_id,
        since=_parse_dt(since, name="since"),
        until=_parse_dt(until, name="until"),
        search=search,
        status=status_filter,
        tag=tag,
        limit=limit,
        offset=0,
    )
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "id",
            "created_at",
            "rating",
            "status",
            "tags",
            "user_email",
            "user_id",
            "conversation_id",
            "message_id",
            "reason",
            "question",
            "answer",
            "resolution_note",
            "resolved_by_email",
            "resolved_at",
            "sources_count",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.get("id") or "",
                r.get("created_at") or "",
                r.get("rating") or "",
                r.get("status") or "",
                "|".join(r.get("tags") or []),
                r.get("user_email") or "",
                r.get("user_id") or "",
                r.get("conversation_id") or "",
                r.get("message_id") or "",
                (r.get("reason") or "").replace("\n", " ").strip(),
                (r.get("question") or "").replace("\n", " ").strip(),
                (r.get("answer") or "").replace("\n", " ").strip(),
                (r.get("resolution_note") or "").replace("\n", " ").strip(),
                r.get("resolved_by_email") or "",
                r.get("resolved_at") or "",
                len(r.get("sources") or []),
            ]
        )
    payload = "﻿" + buf.getvalue()
    filename = f"feedback-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        iter([payload]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{feedback_id}", response_model=FeedbackItem)
def detail_endpoint(
    feedback_id: str,
    actor: dict = Depends(
        require_permission(Permission.FEEDBACK_READ, rate_limit="admin")
    ),
) -> FeedbackItem:
    _require_postgres()
    from llm_wiki.db.feedback import get_feedback_by_id

    row = get_feedback_by_id(feedback_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="feedback non trovato",
        )
    return FeedbackItem(**row)


@router.patch("/{feedback_id}", response_model=FeedbackItem)
def triage_endpoint(
    feedback_id: str,
    body: TriageBody,
    request: Request,
    actor: dict = Depends(
        require_permission(Permission.FEEDBACK_TRIAGE, rate_limit="admin")
    ),
) -> FeedbackItem:
    """Workflow triage: status, tag, note. Tutti i field opzionali.

    ``status=resolved|dismissed`` setta automaticamente resolved_by/at.
    Tornando a ``open|triaged`` li nulla.
    """
    _require_postgres()
    from llm_wiki.db.feedback import get_feedback_by_id, update_triage

    if not get_feedback_by_id(feedback_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="feedback non trovato",
        )
    try:
        updated = update_triage(
            feedback_id,
            actor_user_id=actor["id"],
            status=body.status,
            tags=body.tags,
            resolution_note=body.resolution_note,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="feedback non trovato (race)",
        )
    write_event(
        "feedback.triaged",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "feedback_id": feedback_id,
            "status": updated.get("status"),
            "tags": updated.get("tags") or [],
            "has_note": bool(updated.get("resolution_note")),
        },
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return FeedbackItem(**updated)


@router.delete("/{feedback_id}", status_code=status.HTTP_200_OK)
def delete_endpoint(
    feedback_id: str,
    request: Request,
    actor: dict = Depends(
        require_permission(Permission.FEEDBACK_DELETE, rate_limit="admin")
    ),
) -> dict[str, str]:
    _require_postgres()
    from llm_wiki.db.feedback import delete_feedback, get_feedback_by_id

    target = get_feedback_by_id(feedback_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="feedback non trovato",
        )
    deleted = delete_feedback(feedback_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="feedback non trovato (race)",
        )
    write_event(
        "feedback.deleted",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "feedback_id": feedback_id,
            "rating": target.get("rating"),
            "status": target.get("status"),
            "target_user_id": target.get("user_id"),
            "message_id": target.get("message_id"),
        },
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return {"status": "ok", "id": feedback_id}


__all__ = ["router"]
