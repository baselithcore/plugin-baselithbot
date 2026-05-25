"""Report export endpoints. MD + JSON canonico (signed)."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import Principal
from ..db import get_session
from ..db.models import Report
from ..services.report_export import report_to_json, report_to_markdown
from .deps import require

router = APIRouter()


async def _latest_report(db: AsyncSession, doc_id: str) -> Report | None:
    return (
        await db.execute(select(Report).where(Report.doc_id == doc_id).order_by(desc(Report.signed_at)).limit(1))
    ).scalar_one_or_none()


@router.get("/reports/{doc_id}/export.md", response_class=PlainTextResponse)
async def export_md(
    doc_id: str,
    _: Principal = Depends(require("report", "export")),
    db: AsyncSession = Depends(get_session),
) -> str:
    rep = await _latest_report(db, doc_id)
    if not rep:
        raise HTTPException(404, "No report for document")
    payload = json.loads(rep.payload)
    payload["signature"] = rep.signature
    return report_to_markdown(payload)


@router.get("/reports/{doc_id}/export.json")
async def export_json(
    doc_id: str,
    _: Principal = Depends(require("report", "export")),
    db: AsyncSession = Depends(get_session),
) -> Response:
    rep = await _latest_report(db, doc_id)
    if not rep:
        raise HTTPException(404, "No report for document")
    payload = json.loads(rep.payload)
    payload["signature"] = rep.signature
    return Response(content=report_to_json(payload), media_type="application/json")
