"""Runtime kill-switch endpoints.

A global pause/resume for autonomous sending: while paused, every drafted reply
is queued for human review regardless of autonomy mode or whitelist — the
operator's emergency brake. Guarded by the ``twin.control`` permission (admin by
default) and fully audited, since toggling autonomy is a privileged action.
"""

from __future__ import annotations

from typing import Any

from core.auth.types import AuthUser
from fastapi import Depends, Request

from .guards import actor_label
from .i18n import negotiate_locale, translate
from .service import TwinService


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def build_control_router(service: TwinService, guards: Any) -> Any:
    """Build the pause/resume control sub-router bound to the service."""
    from fastapi import APIRouter, Header

    router = APIRouter(prefix="/control", tags=["twin:control"])

    async def _toggle(
        paused: bool, request: Request, principal: AuthUser, locale: str | None
    ) -> dict[str, Any]:
        await service.set_paused(
            paused, actor=actor_label(principal), ip=_client_ip(request)
        )
        key = "twin.control.paused" if paused else "twin.control.resumed"
        return {
            "paused": paused,
            "message": translate(key, negotiate_locale(locale)),
        }

    @router.post("/pause")
    async def pause(
        request: Request,
        principal: AuthUser = Depends(guards.control),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Engage the kill-switch: suspend all autonomous sending."""
        return await _toggle(True, request, principal, accept_language)

    @router.post("/resume")
    async def resume(
        request: Request,
        principal: AuthUser = Depends(guards.control),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Release the kill-switch: restore the configured autonomy."""
        return await _toggle(False, request, principal, accept_language)

    return router


__all__ = ["build_control_router"]
