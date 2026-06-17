"""Self-service endpoints: the caller's own permissions and accessible tabs.

Any plugin UI (and the control plane) can call these to hide surfaces the
current user is not allowed to access.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request

from core.auth import AuthUser
from plugins.auth.dependencies import require_auth
from plugins.auth.rbac.service import get_rbac_service
from plugins.auth.rbac_router._models import AccessibleTab, MePermissions

router = APIRouter()


@router.get("/permissions", response_model=MePermissions)
async def my_permissions(user: AuthUser = Depends(require_auth)):
    """Effective permission slugs for the current user."""
    if not user.is_authenticated or user.user_id == "anonymous":
        return MePermissions(permissions=[])
    perms = get_rbac_service().effective_permissions(user.user_id, user.roles)
    return MePermissions(permissions=sorted(perms))


@router.get("/tabs", response_model=List[AccessibleTab])
async def my_tabs(request: Request, user: AuthUser = Depends(require_auth)):
    """Known tabs annotated with whether the current user may access each."""
    if not user.is_authenticated or user.user_id == "anonymous":
        return []
    registry = getattr(request.app.state, "plugin_registry", None)
    return get_rbac_service().accessible_tabs(
        user.user_id, user.roles, registry=registry
    )
