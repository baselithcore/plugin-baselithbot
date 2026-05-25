"""HITL approve / reject / list-pending endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.di.container import ServiceRegistry
from plugins.red_agent.approvals import ApprovalRegistry
from plugins.red_agent.dependencies import (
    require_security_operator,
    require_viewer,
)

router = APIRouter(prefix="/scans", tags=["red-agent"])


def _get_registry() -> ApprovalRegistry:
    reg = ServiceRegistry.get(ApprovalRegistry)
    if reg is None:
        raise HTTPException(503, "ApprovalRegistry not registered")
    return reg


@router.post("/{scan_id}/approve", dependencies=[require_security_operator()])
async def approve(
    scan_id: UUID,
    registry: ApprovalRegistry = Depends(_get_registry),
) -> dict[str, str]:
    ok = await registry.resolve(scan_id, approved=True, actor="api-caller")
    if not ok:
        raise HTTPException(409, "no pending approval for scan")
    return {"status": "approved"}


@router.post("/{scan_id}/reject", dependencies=[require_security_operator()])
async def reject(
    scan_id: UUID,
    registry: ApprovalRegistry = Depends(_get_registry),
) -> dict[str, str]:
    ok = await registry.resolve(scan_id, approved=False, actor="api-caller")
    if not ok:
        raise HTTPException(409, "no pending approval for scan")
    return {"status": "rejected"}


@router.get("/pending-approvals", dependencies=[require_viewer()])
async def list_pending(
    registry: ApprovalRegistry = Depends(_get_registry),
) -> list[dict[str, Any]]:
    return await registry.list_pending()
