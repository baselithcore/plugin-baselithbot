"""Gated lifecycle routes — admin only.

The ``admin`` role check is the primary gate (an optional autonomy policy and an
append-only audit sit behind it in :class:`ControlService`). The auth dependency
is imported from the bundled ``auth`` plugin, which is a declared dependency.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Body, Depends, Request

from core.auth.types import AuthUser

from ..api_models import ActionRequest, ActionResult, AuditEntryView, ConfigRequest
from ..service import get_control_service
from ..service.audit import get_audit_sink
from ._guards import admin_principal


def build_actions_router() -> APIRouter:
    """Build the gated actions sub-router (admin role required by default)."""
    router = APIRouter(tags=["baselithcontrol:actions"])
    admin = admin_principal

    @router.post("/actions/{plugin}/{op}", response_model=ActionResult)
    async def act(
        plugin: str,
        op: Literal["enable", "disable", "reload"],
        request: Request,
        body: ActionRequest = Body(default_factory=ActionRequest),
        user: AuthUser = Depends(admin),
    ) -> ActionResult:
        """Enable, disable, or reload a plugin (governed + audited)."""
        service = get_control_service(request.app)
        return await service.run(
            plugin=plugin, op=op, actor=user.user_id, reason=body.reason
        )

    @router.post("/config/{plugin}", response_model=ActionResult)
    async def set_config(
        plugin: str,
        request: Request,
        body: ConfigRequest,
        user: AuthUser = Depends(admin),
    ) -> ActionResult:
        """Persist a plugin's ``enabled`` flag in plugins.yaml (admin, audited)."""
        service = get_control_service(request.app)
        return await service.set_config_enabled(
            plugin=plugin, enabled=body.enabled, actor=user.user_id, reason=body.reason
        )

    @router.get("/audit", response_model=list[AuditEntryView])
    async def audit_tail(
        limit: int = 50,
        user: AuthUser = Depends(admin),
    ) -> list[AuditEntryView]:
        """Recent governed-action audit records (admin only)."""
        return get_audit_sink().tail(limit=limit)

    return router


__all__ = ["build_actions_router"]
