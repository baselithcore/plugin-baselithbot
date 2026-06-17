"""Admin endpoints: permission catalog, roles, and user-role assignments."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import AuthUser
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import require_permission
from plugins.auth.rbac.permissions import Permission
from plugins.auth.rbac.service import RBACService, get_rbac_service
from plugins.auth.rbac_router._audit import audit_rbac
from plugins.auth.rbac_router._models import (
    AssignRole,
    PermissionOut,
    RoleCreate,
    RoleOut,
    RolePermissions,
    RoleUpdate,
)

router = APIRouter()


def _service() -> RBACService:
    return get_rbac_service()


@router.get("/permissions", response_model=List[PermissionOut])
async def list_permissions(
    user: AuthUser = Depends(require_permission(Permission.RBAC_READ)),
):
    """List the full permission catalog (built-in + discovered tab perms)."""
    return _service().store.list_permissions()


@router.get("/roles", response_model=List[RoleOut])
async def list_roles(
    user: AuthUser = Depends(require_permission(Permission.RBAC_READ)),
):
    """List all roles with their granted permissions."""
    return _service().store.list_roles()


@router.post("/roles", response_model=RoleOut, status_code=201)
async def create_role(
    body: RoleCreate,
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Create a custom role."""
    store = _service().store
    if store.get_role_by_slug(body.slug):
        raise HTTPException(status_code=409, detail="Role slug already exists")
    role = store.create_role(body.slug, body.name, body.description)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.ROLE_CREATED,
        target_id=role["id"],
        details={"slug": body.slug, "name": body.name},
    )
    return role


@router.patch("/roles/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: str,
    body: RoleUpdate,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Update a role's name/description."""
    role = _service().store.update_role(role_id, body.name, body.description)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(
    role_id: str,
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Delete a custom role (system roles are protected)."""
    if not _service().store.delete_role(role_id):
        raise HTTPException(
            status_code=409, detail="Role not found or is a protected system role"
        )
    audit_rbac(request, user.user_id, AuditAction.ROLE_DELETED, target_id=role_id)


@router.put("/roles/{role_id}/permissions", response_model=RoleOut)
async def set_role_permissions(
    role_id: str,
    body: RolePermissions,
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Replace the full permission set of a role."""
    store = _service().store
    if not store.get_role(role_id):
        raise HTTPException(status_code=404, detail="Role not found")
    store.set_role_permissions(role_id, body.permissions)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.ROLE_PERMISSIONS_CHANGED,
        target_id=role_id,
        details={"permissions": body.permissions},
    )
    return store.get_role(role_id)


@router.post("/roles/{role_id}/permissions/{slug:path}", status_code=204)
async def grant_role_permission(
    role_id: str,
    slug: str,
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Grant a single permission to a role (matrix cell on)."""
    store = _service().store
    if not store.get_role(role_id):
        raise HTTPException(status_code=404, detail="Role not found")
    store.grant_permission(role_id, slug)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.ROLE_PERMISSIONS_CHANGED,
        target_id=role_id,
        details={"grant": slug},
    )


@router.delete("/roles/{role_id}/permissions/{slug:path}", status_code=204)
async def revoke_role_permission(
    role_id: str,
    slug: str,
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Revoke a single permission from a role (matrix cell off)."""
    _service().store.revoke_permission(role_id, slug)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.ROLE_PERMISSIONS_CHANGED,
        target_id=role_id,
        details={"revoke": slug},
    )


@router.get("/users/{user_id}/roles", response_model=List[RoleOut])
async def get_user_roles(
    user_id: str,
    user: AuthUser = Depends(require_permission(Permission.RBAC_READ)),
):
    """Custom roles assigned to a user."""
    return _service().store.get_user_roles(user_id)


@router.post("/users/{user_id}/roles", status_code=204)
async def assign_user_role(
    user_id: str,
    body: AssignRole,
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Assign a custom role to a user."""
    _service().store.assign_user_role(user_id, body.role_id, granted_by=user.user_id)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.USER_ROLE_ASSIGNED,
        target_id=user_id,
        details={"role_id": body.role_id},
    )


@router.delete("/users/{user_id}/roles/{role_id}", status_code=204)
async def revoke_user_role(
    user_id: str,
    role_id: str,
    request: Request,
    user: AuthUser = Depends(require_permission(Permission.RBAC_MANAGE)),
):
    """Revoke a custom role from a user."""
    _service().store.revoke_user_role(user_id, role_id)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.USER_ROLE_REVOKED,
        target_id=user_id,
        details={"role_id": role_id},
    )
