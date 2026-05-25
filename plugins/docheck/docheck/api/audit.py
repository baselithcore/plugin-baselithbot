"""Audit log API: list with filters, chain verify, exports, detail.

Read access: `audit:read`. Export: `audit:export`.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import Principal
from ..core.tenant import current_tenant
from ..db import get_session
from ..db.models import AuditLog, User
from ..services.audit import verify_chain
from ..services.signing import public_key_hex, sign_bytes
from .deps import require

router = APIRouter()


# --------------------------- schemas ---------------------------


class AuditEntry(BaseModel):
    seq: int
    ts: str
    user_id: str | None
    user_email: str | None = None
    action: str
    resource: str | None
    payload_hash: str
    prev_hash: str
    entry_hash: str
    signature: str


class AuditEntryDetail(AuditEntry):
    valid: bool
    error: str | None = None


class ChainStatus(BaseModel):
    ok: bool
    broken_seq: int | None
    total_entries: int
    pubkey: str
    verified_at: str


class AuditUserOption(BaseModel):
    user_id: str
    email: str | None
    display_name: str | None


# --------------------------- helpers ---------------------------


def _parse_dt(s: str | None, name: str) -> datetime | None:
    if not s:
        return None
    try:
        # Accept "YYYY-MM-DD" or full ISO
        if len(s) == 10:
            return datetime.fromisoformat(s + "T00:00:00")
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(400, f"Invalid {name}: {s}") from exc


def _base_query(
    *,
    user_id: str | None,
    action: str | None,
    resource: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Any:
    stmt = select(AuditLog)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource:
        like = f"%{resource}%"
        stmt = stmt.where(AuditLog.resource.like(like))
    if date_from:
        stmt = stmt.where(AuditLog.ts >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.ts <= date_to)
    return stmt


async def _email_map(db: AsyncSession, user_ids: set[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    rows = (await db.execute(select(User.id, User.email).where(User.id.in_(user_ids)))).all()
    return dict(rows)  # type: ignore[arg-type]


# --------------------------- endpoints ---------------------------


@router.get("/audit/log")
async def list_audit(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    _: Principal = Depends(require("audit", "read")),
    db: AsyncSession = Depends(get_session),
) -> Response:
    df = _parse_dt(date_from, "date_from")
    dt_ = _parse_dt(date_to, "date_to")
    base = _base_query(
        user_id=user_id,
        action=action,
        resource=resource,
        date_from=df,
        date_to=dt_,
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(base.order_by(desc(AuditLog.seq)).limit(limit).offset(offset))).scalars().all()
    emails = await _email_map(db, {r.user_id for r in rows if r.user_id})
    items = [
        AuditEntry(
            seq=r.seq,
            ts=r.ts.isoformat(),
            user_id=r.user_id,
            user_email=emails.get(r.user_id) if r.user_id else None,
            action=r.action,
            resource=r.resource,
            payload_hash=r.payload_hash,
            prev_hash=r.prev_hash,
            entry_hash=r.entry_hash,
            signature=r.signature,
        ).model_dump()
        for r in rows
    ]
    return Response(
        content=json.dumps(items),
        media_type="application/json",
        headers={"X-Total-Count": str(total)},
    )


@router.get("/audit/actions", response_model=list[str])
async def list_actions(
    _: Principal = Depends(require("audit", "read")),
    db: AsyncSession = Depends(get_session),
) -> list[str]:
    rows = (await db.execute(select(AuditLog.action).distinct().order_by(AuditLog.action))).scalars().all()
    return list(rows)


@router.get("/audit/users", response_model=list[AuditUserOption])
async def list_audit_users(
    _: Principal = Depends(require("audit", "read")),
    db: AsyncSession = Depends(get_session),
) -> list[AuditUserOption]:
    sub = select(AuditLog.user_id).where(AuditLog.user_id.is_not(None)).distinct().subquery()
    rows = (
        await db.execute(
            select(User.id, User.email, User.display_name).join(sub, sub.c.user_id == User.id).order_by(User.email)
        )
    ).all()
    return [AuditUserOption(user_id=uid, email=em, display_name=dn) for uid, em, dn in rows]


@router.get("/audit/verify", response_model=ChainStatus)
async def verify_audit(
    _: Principal = Depends(require("audit", "read")),
    db: AsyncSession = Depends(get_session),
) -> ChainStatus:
    ok, broken = await verify_chain(db)
    total = (await db.execute(select(func.count(AuditLog.seq)))).scalar_one()
    return ChainStatus(
        ok=ok,
        broken_seq=broken,
        total_entries=int(total),
        pubkey=public_key_hex(),
        verified_at=datetime.utcnow().isoformat() + "Z",
    )


# --------------------------- export ---------------------------


def _filtered_rows_query(
    user_id: str | None,
    action: str | None,
    resource: str | None,
    date_from: str | None,
    date_to: str | None,
) -> Any:
    return _base_query(
        user_id=user_id,
        action=action,
        resource=resource,
        date_from=_parse_dt(date_from, "date_from"),
        date_to=_parse_dt(date_to, "date_to"),
    ).order_by(AuditLog.seq)


@router.get("/audit/export.csv")
async def export_csv(
    user_id: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    _: Principal = Depends(require("audit", "export")),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    stmt = _filtered_rows_query(user_id, action, resource, date_from, date_to)
    rows = (await db.execute(stmt)).scalars().all()
    emails = await _email_map(db, {r.user_id for r in rows if r.user_id})

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "seq",
            "ts",
            "user_id",
            "user_email",
            "action",
            "resource",
            "payload_hash",
            "prev_hash",
            "entry_hash",
            "signature",
        ]
    )
    for r in rows:
        w.writerow(
            [
                r.seq,
                r.ts.isoformat(),
                r.user_id or "",
                emails.get(r.user_id, "") if r.user_id else "",
                r.action,
                r.resource or "",
                r.payload_hash,
                r.prev_hash,
                r.entry_hash,
                r.signature,
            ]
        )
    data = buf.getvalue().encode()
    fname = f"audit-{current_tenant()}-{datetime.utcnow():%Y%m%dT%H%M%SZ}.csv"
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/audit/export.json")
async def export_json(
    user_id: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    _: Principal = Depends(require("audit", "export")),
    db: AsyncSession = Depends(get_session),
) -> Response:
    stmt = _filtered_rows_query(user_id, action, resource, date_from, date_to)
    rows = (await db.execute(stmt)).scalars().all()
    emails = await _email_map(db, {r.user_id for r in rows if r.user_id})
    ok, broken = await verify_chain(db)

    entries: list[dict[str, Any]] = [
        {
            "seq": r.seq,
            "ts": r.ts.isoformat(),
            "user_id": r.user_id,
            "user_email": emails.get(r.user_id) if r.user_id else None,
            "action": r.action,
            "resource": r.resource,
            "payload_hash": r.payload_hash,
            "prev_hash": r.prev_hash,
            "entry_hash": r.entry_hash,
            "signature": r.signature,
        }
        for r in rows
    ]
    body = {
        "tenant_id": current_tenant(),
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "pubkey": public_key_hex(),
        "chain": {"ok": ok, "broken_seq": broken, "total_entries": len(entries)},
        "filters": {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "date_from": date_from,
            "date_to": date_to,
        },
        "entries": entries,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["export_signature"] = sign_bytes(canonical)
    fname = f"audit-{current_tenant()}-{datetime.utcnow():%Y%m%dT%H%M%SZ}.json"
    return Response(
        content=json.dumps(body, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/audit/{seq}", response_model=AuditEntryDetail)
async def get_audit_entry(
    seq: int,
    _: Principal = Depends(require("audit", "read")),
    db: AsyncSession = Depends(get_session),
) -> AuditEntryDetail:
    row = (await db.execute(select(AuditLog).where(AuditLog.seq == seq))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Not found")
    ok, broken = await verify_chain(db)
    valid = ok or (broken is not None and seq < broken)
    err = None if valid else "Chain integrity broken at or before this entry"
    emails = await _email_map(db, {row.user_id} if row.user_id else set())
    return AuditEntryDetail(
        seq=row.seq,
        ts=row.ts.isoformat(),
        user_id=row.user_id,
        user_email=emails.get(row.user_id) if row.user_id else None,
        action=row.action,
        resource=row.resource,
        payload_hash=row.payload_hash,
        prev_hash=row.prev_hash,
        entry_hash=row.entry_hash,
        signature=row.signature,
        valid=valid,
        error=err,
    )
