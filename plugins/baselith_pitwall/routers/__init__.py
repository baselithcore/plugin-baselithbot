"""FastAPI surface for the digital pit wall (REST + SSE), assembled from groups.

A fully-async API mounted under ``/api/baselith_pitwall``. The surface is split
by responsibility into four guarded, tenant- and session-scoped endpoint groups
(read / sessions / context / governance) so no single module nears the size cap.
Every response carries an ``X-API-Version`` header; mutating endpoints honour
RBAC, rate limiting, and idempotency (see :mod:`._deps`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Response

from ._context import register_context
from ._deps import API_VERSION, RouterContext
from ._governance import register_governance
from ._read import register_read
from ._sessions import register_sessions

if TYPE_CHECKING:
    from ..plugin import BaselithPitwallPlugin


async def _stamp_version(response: Response) -> None:
    """Router-level dependency that stamps the API version on every response."""
    response.headers["X-API-Version"] = API_VERSION


def build_pitwall_router(plugin: "BaselithPitwallPlugin") -> APIRouter:
    """Build the plugin router bound to the live session manager."""
    from fastapi import Depends

    router = APIRouter(tags=["pitwall"], dependencies=[Depends(_stamp_version)])
    rc = RouterContext(plugin)
    register_read(router, rc)
    register_sessions(router, rc)
    register_context(router, rc)
    register_governance(router, rc)
    return router


__all__ = ["build_pitwall_router", "API_VERSION"]
