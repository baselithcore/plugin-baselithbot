"""Workspace dashboard endpoints: queue counters, recent activity, active policies summary."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import Principal
from ..db import get_session
from ..db.models import Document, Policy, Report
from .deps import require

router = APIRouter()


@router.get("/workspace/queue")
async def workspace_queue(
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Live counters for Workspace landing.

    - in_review: documents uploaded/parsed by this user without a signed report yet.
    - pending_approval: signed reports owned by this user with no accept/reject decision on every FAIL finding.
    - compliant: signed reports owned by this user with score >= 80 in the last 30 days.
    """
    week_ago = datetime.now(UTC) - timedelta(days=7)
    month_ago = datetime.now(UTC) - timedelta(days=30)

    reports_subq = (
        select(Report.doc_id).where(Report.user_id == principal.user_id).subquery()
    )

    in_review = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.owner_id == principal.user_id)
            .where(Document.id.notin_(select(reports_subq.c.doc_id)))
        )
    ).scalar_one()

    in_review_recent = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.owner_id == principal.user_id)
            .where(Document.id.notin_(select(reports_subq.c.doc_id)))
            .where(Document.uploaded_at >= week_ago)
        )
    ).scalar_one()

    pending_total = (
        await db.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.user_id == principal.user_id)
            .where(Report.score < 80)
        )
    ).scalar_one()

    pending_recent = (
        await db.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.user_id == principal.user_id)
            .where(Report.score < 80)
            .where(Report.signed_at >= week_ago)
        )
    ).scalar_one()

    compliant_total = (
        await db.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.user_id == principal.user_id)
            .where(Report.score >= 80)
        )
    ).scalar_one()

    compliant_recent = (
        await db.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.user_id == principal.user_id)
            .where(Report.score >= 80)
            .where(Report.signed_at >= month_ago)
        )
    ).scalar_one()

    return {
        "in_review": {"value": int(in_review), "trend_7d": int(in_review_recent)},
        "pending_approval": {
            "value": int(pending_total),
            "trend_7d": int(pending_recent),
        },
        "compliant": {
            "value": int(compliant_total),
            "trend_30d": int(compliant_recent),
        },
    }


@router.get("/workspace/active-policies")
async def workspace_active_policies(
    _: Principal = Depends(require("policy", "read")),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Latest active policies summary (id, version, scope, lang, title) limited to 6 entries."""
    rows = (
        (
            await db.execute(
                select(Policy)
                .where(Policy.active == 1)
                .order_by(desc(Policy.created_at))
                .limit(6)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": p.id,
            "version": p.version,
            "title": p.title,
            "scope": p.scope,
            "lang": p.lang,
        }
        for p in rows
    ]


@router.get("/workspace/recent-activity")
async def workspace_recent_activity(
    limit: int = 5,
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Last analyses by current user: doc filename, score, signed_at, report_id."""
    rows = (
        await db.execute(
            select(Report, Document)
            .join(Document, Document.id == Report.doc_id)
            .where(Report.user_id == principal.user_id)
            .order_by(desc(Report.signed_at))
            .limit(limit)
        )
    ).all()
    return [
        {
            "report_id": r.id,
            "doc_id": d.id,
            "filename": d.filename,
            "score": r.score,
            "signed_at": r.signed_at.isoformat(),
        }
        for r, d in rows
    ]
