"""Governance surface: the audit ledger and human-in-the-loop acknowledgements.

The audit ledger and ack listing are viewer-guarded and paged with an
``X-Total-Count`` header. Accepting or rejecting a recommendation is the
privileged HITL act, restricted by the approver guard, and is itself recorded in
the ledger by the session manager.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel

from ..session_models import AckStatus
from ._deps import Ctx, RouterContext, use_ctx


class AckRequest(BaseModel):
    """Request body for a strategist's verdict on a recommendation."""

    status: AckStatus
    note: str = ""


def register_governance(router: APIRouter, rc: RouterContext) -> None:
    """Attach the governance endpoints to ``router``."""
    viewer = Depends(rc.viewer())
    approver = Depends(rc.approver())

    @router.get("/audit", dependencies=[viewer])
    async def audit(
        response: Response,
        session_scope: bool = True,
        limit: int = 100,
        offset: int = 0,
        ctx: Ctx = use_ctx(rc),
    ) -> list[dict[str, Any]]:
        """Audit ledger (paged, newest first); tenant-wide when not scoped."""
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        session_id = ctx.session_id if session_scope else None
        items, total = await rc.plugin.store.list_audit(
            ctx.tenant, session_id=session_id, limit=limit, offset=offset
        )
        response.headers["X-Total-Count"] = str(total)
        return [r.model_dump(mode="json") for r in items]

    @router.get("/acks", dependencies=[viewer])
    async def acks(
        recommendation_id: str | None = None, ctx: Ctx = use_ctx(rc)
    ) -> list[dict[str, Any]]:
        """List HITL acknowledgements for the resolved session."""
        items = await rc.plugin.store.list_acks(
            ctx.tenant, ctx.session_id, recommendation_id=recommendation_id
        )
        return [a.model_dump(mode="json") for a in items]

    @router.post("/recommendations/{rec_id}/ack", dependencies=[approver])
    async def acknowledge(
        rec_id: str,
        body: AckRequest,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Record a strategist's accept/reject/defer verdict on a recommendation."""
        ack = await rc.plugin.manager.acknowledge(
            ctx.tenant,
            ctx.session_id,
            rec_id,
            body.status,
            actor=ctx.actor,
            note=body.note,
        )
        if ack is None:
            raise rc.error(404, "error.unknown_recommendation", accept_language)
        return ack.model_dump(mode="json")


__all__ = ["register_governance", "AckRequest"]
