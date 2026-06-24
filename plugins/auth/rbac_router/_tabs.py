"""Admin endpoints: central per-plugin-tab access policy (the matrix)."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.auth import AuthUser
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import require_permission
from plugins.auth.rbac.discovery import system_plugin_names
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


def _annotate(policies: List[Dict]) -> List[Dict]:
    """Tag each policy with its ``system`` flag for the admin matrix.

    A system plugin (manifest ``system: true``) is admin-only by default, so its
    tabs are always presented as ``restricted`` regardless of the stored flag —
    the matrix can only grant them per role, never open them to everyone. This
    keeps the displayed policy consistent with what the RBAC service actually
    enforces (``accessible_tabs`` / ``can_access_tab``).
    """
    system = system_plugin_names()
    out: List[Dict] = []
    for policy in policies:
        is_system = policy.get("plugin") in system
        out.append(
            {
                **policy,
                "system": is_system,
                "restricted": bool(policy.get("restricted")) or is_system,
            }
        )
    return out


@router.get("/tabs", response_model=List[TabPolicyOut])
async def list_tabs(
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_READ)),
):
    """All known plugin tabs and their access policy (admin matrix source)."""
    return _annotate(_service().list_tabs(registry=_registry(request)))


@router.post("/tabs/refresh", response_model=List[TabPolicyOut])
async def refresh_tabs(
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Re-discover plugin tabs from the registry and return the refreshed list."""
    svc = _service()
    svc.refresh_tabs(registry=_registry(request))
    return _annotate(svc.store.list_tab_policies())


@router.put("/tabs/{plugin}/{tab_id}/restricted", response_model=TabPolicyOut)
async def set_tab_restricted(
    plugin: str,
    tab_id: str,
    body: TabRestrict,
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Toggle whether a tab requires its permission to access.

    System / infrastructure tabs cannot be opened to everyone: they are
    admin-only by design and may only be granted to specific roles, so a request
    to un-restrict one is rejected (secure-by-default).
    """
    if plugin in system_plugin_names() and not body.restricted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="system plugin tabs are admin-only and cannot be opened; "
            "grant access per role instead",
        )
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
