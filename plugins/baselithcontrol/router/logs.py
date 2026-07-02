"""Read-only live log viewer route.

Serves a filtered, newest-first tail of the in-memory application-log ring
(:mod:`..service.logs`). Logs can contain sensitive operational detail, so this
is **admin-gated** (``admin_principal``) — unlike the open read endpoints — and
relies on the core log-masking layer upstream. Polled by the dashboard's Logs
tab; the backend retains the buffer so a reload keeps recent history.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from core.auth.types import AuthUser

from ..api_models import LogEntry, LogsView
from ..service.deps import get_config
from ..service.logs import get_log_buffer
from ._guards import admin_principal


def build_logs_router() -> APIRouter:
    """Build the live-log sub-router (admin-only reads)."""
    router = APIRouter(tags=["baselithcontrol:logs"])

    @router.get("/logs", response_model=LogsView)
    async def logs(
        request: Request,
        _user: AuthUser = Depends(admin_principal),
        limit: int = Query(default=200, ge=1, le=2000),
        level: str | None = Query(default=None),
        plugin: str | None = Query(default=None),
        q: str | None = Query(default=None),
    ) -> LogsView:
        """Filtered tail of captured logs (level = minimum severity, newest first)."""
        cfg = get_config(request.app)
        if not cfg.logs_enabled:
            return LogsView(enabled=False, capacity=0)
        buffer = get_log_buffer()
        rows = buffer.tail(limit=limit, level=level, plugin=plugin, query=q)
        return LogsView(
            enabled=True,
            capacity=buffer.capacity,
            count=len(rows),
            plugins=buffer.known_plugins(),
            entries=[LogEntry.model_validate(r) for r in rows],
        )

    return router


__all__ = ["build_logs_router"]
