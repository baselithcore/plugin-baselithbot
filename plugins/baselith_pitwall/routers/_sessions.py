"""Session lifecycle surface: create, list, start/pause/end, delete.

Reads are viewer-guarded; every state change is strategist-guarded and recorded
in the audit ledger by the session manager. Sessions are tenant-scoped — the
tenant comes from :class:`~._deps.Ctx` (header or JWT), the session id from the
path.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header

from ..session_models import SessionCreate
from ._deps import Ctx, RouterContext, use_ctx


def register_sessions(router: APIRouter, rc: RouterContext) -> None:
    """Attach the session lifecycle endpoints to ``router``."""
    viewer = Depends(rc.viewer())
    strategist = Depends(rc.strategist())

    @router.get("/sessions", dependencies=[viewer])
    async def list_sessions(ctx: Ctx = use_ctx(rc)) -> list[dict[str, Any]]:
        """List the tenant's race sessions, newest first."""
        sessions = await rc.plugin.manager.list_sessions(ctx.tenant)
        return [s.model_dump(mode="json") for s in sessions]

    @router.post("/sessions", dependencies=[strategist])
    async def create_session(
        spec: SessionCreate, ctx: Ctx = use_ctx(rc)
    ) -> dict[str, Any]:
        """Provision a new race session (status ``configuring``)."""
        session = await rc.plugin.manager.create_session(
            ctx.tenant, spec, actor=ctx.actor
        )
        return session.model_dump(mode="json")

    @router.get("/sessions/{session_id}", dependencies=[viewer])
    async def get_session(
        session_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Fetch a single session record."""
        session = await rc.plugin.manager.get_session(ctx.tenant, session_id)
        if session is None:
            raise rc.error(404, "error.unknown_session", accept_language)
        return session.model_dump(mode="json")

    @router.post("/sessions/{session_id}/start", dependencies=[strategist])
    async def start_session(
        session_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Build the engine, attach telemetry, and take the session live."""
        session = await rc.plugin.manager.start_session(
            ctx.tenant, session_id, actor=ctx.actor
        )
        if session is None:
            raise rc.error(404, "error.unknown_session", accept_language)
        return session.model_dump(mode="json")

    @router.post("/sessions/{session_id}/pause", dependencies=[strategist])
    async def pause_session(
        session_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Suspend ingestion without discarding the session."""
        session = await rc.plugin.manager.pause_session(
            ctx.tenant, session_id, actor=ctx.actor
        )
        if session is None:
            raise rc.error(404, "error.unknown_session", accept_language)
        return session.model_dump(mode="json")

    @router.post("/sessions/{session_id}/end", dependencies=[strategist])
    async def end_session(
        session_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Stop the engine and mark the session finished."""
        session = await rc.plugin.manager.end_session(
            ctx.tenant, session_id, actor=ctx.actor
        )
        if session is None:
            raise rc.error(404, "error.unknown_session", accept_language)
        return session.model_dump(mode="json")

    @router.delete("/sessions/{session_id}", dependencies=[strategist])
    async def delete_session(
        session_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Delete a session and its derived records (audit ledger retained)."""
        deleted = await rc.plugin.manager.delete_session(
            ctx.tenant, session_id, actor=ctx.actor
        )
        if not deleted:
            raise rc.error(404, "error.unknown_session", accept_language)
        return {"deleted": True, "session_id": session_id}


__all__ = ["register_sessions"]
