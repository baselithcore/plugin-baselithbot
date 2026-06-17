"""Admin endpoints: central per-plugin-tab access policy (the matrix)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request

from core.auth import AuthUser
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import require_permission
from plugins.auth.rbac.permissions import Permission
from plugins.auth.rbac.service import RBACService, get_rbac_service
from plugins.auth.rbac_router._audit import audit_rbac
from plugins.auth.rbac_router._models import TabPolicyOut, TabRestrict

router = APIRouter()


def _service() -> RBACService:
    return get_rbac_service()


def _registry(request: Request):
    """The live runtime plugin registry from app state, if present."""
    return getattr(request.app.state, "plugin_registry", None)


@router.get("/tabs", response_model=List[TabPolicyOut])
async def list_tabs(
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_READ)),
):
    """All known plugin tabs and their access policy (admin matrix source)."""
    return _service().list_tabs(registry=_registry(request))


@router.post("/tabs/refresh", response_model=List[TabPolicyOut])
async def refresh_tabs(
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Re-discover plugin tabs from the registry and return the refreshed list."""
    svc = _service()
    svc.refresh_tabs(registry=_registry(request))
    return svc.store.list_tab_policies()


@router.put("/tabs/{plugin}/{tab_id}/restricted", response_model=TabPolicyOut)
async def set_tab_restricted(
    plugin: str,
    tab_id: str,
    body: TabRestrict,
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Toggle whether a tab requires its permission to access."""
    store = _service().store
    store.set_tab_restricted(plugin, tab_id, body.restricted)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.TAB_POLICY_CHANGED,
        target_id=f"{plugin}:{tab_id}",
        details={"restricted": body.restricted},
    )
    policy = store.get_tab_policy(plugin, tab_id)
    return policy or {
        "plugin": plugin,
        "tab_id": tab_id,
        "label": tab_id,
        "restricted": body.restricted,
    }
