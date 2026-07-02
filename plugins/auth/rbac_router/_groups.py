"""Admin endpoints: groups, membership, and group-role grants (wikigen-style)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import AuthUser
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import require_permission
from plugins.auth.rbac.permissions import Permission, required_assign_permission
from plugins.auth.rbac.service import RBACService, get_rbac_service
from plugins.auth.rbac_router._audit import audit_rbac
from plugins.auth.rbac_router._escalation import guard_role_assignment
from plugins.auth.rbac_router._models import (
    AddMember,
    AssignGroupRole,
    GroupCreate,
    GroupMember,
    GroupOut,
    GroupUpdate,
)

router = APIRouter()


def _service() -> RBACService:
    return get_rbac_service()


def _guard_group_membership(store, actor: AuthUser, group_id: str) -> None:
    """Gate membership changes on groups that confer admin.

    Adding/removing a member of a group that carries a wildcard/``admin`` role
    instantly makes (or unmakes) that user an admin — the same escalation vector
    as a direct user-role grant. ``assign_group_role`` was already gated but
    ``add_member`` was not, so an operator holding only ``groups.manage`` could
    add themselves to a pre-existing "Platform Admins" group and self-elevate.
    Require the admin assign-permission (``rbac.assign.admin``, which an
    effective admin always satisfies) whenever any of the group's roles is
    admin-conferring; ordinary groups are unaffected.
    """
    group = store.get_group(group_id)
    if not group:
        return
    for slug in group.get("roles", []):
        role = store.get_role_by_slug(slug)
        if role and required_assign_permission(role) == Permission.RBAC_ASSIGN_ADMIN:
            guard_role_assignment(actor, group_id, role)
            return


@router.get("/groups", response_model=List[GroupOut])
async def list_groups(
    user: AuthUser = Depends(
        require_permission(Permission.RBAC_READ, Permission.GROUPS_MANAGE)
    ),
):
    """All groups with member counts and granted roles."""
    return _service().store.list_groups()


@router.post("/groups", response_model=GroupOut, status_code=201)
async def create_group(
    body: GroupCreate,
    request: Request,
    user: AuthUser = Depends(
        require_permission(Permission.RBAC_MANAGE, Permission.GROUPS_MANAGE)
    ),
):
    """Create a custom group."""
    store = _service().store
    if store.get_group_by_slug(body.slug):
        raise HTTPException(status_code=409, detail="Group slug already exists")
    group = store.create_group(
        body.slug, body.name, body.description, body.mfa_required
    )
    audit_rbac(
        request,
        user.user_id,
        AuditAction.GROUP_CREATED,
        target_id=group["id"],
        details={
            "slug": body.slug,
            "name": body.name,
            "mfa_required": body.mfa_required,
        },
    )
    return group


@router.patch("/groups/{group_id}", response_model=GroupOut)
async def update_group(
    group_id: str,
    body: GroupUpdate,
    user: AuthUser = Depends(
        require_permission(Permission.RBAC_MANAGE, Permission.GROUPS_MANAGE)
    ),
):
    """Update a group's name/description and optional MFA mandate."""
    group = _service().store.update_group(
        group_id, body.name, body.description, body.mfa_required
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    request: Request,
    user: AuthUser = Depends(
        require_permission(Permission.RBAC_MANAGE, Permission.GROUPS_MANAGE)
    ),
):
    """Delete a custom group (system groups are protected)."""
    if not _service().store.delete_group(group_id):
        raise HTTPException(
            status_code=409, detail="Group not found or is a protected system group"
        )
    audit_rbac(request, user.user_id, AuditAction.GROUP_DELETED, target_id=group_id)


@router.get("/groups/{group_id}/members", response_model=List[GroupMember])
async def list_members(
    group_id: str,
    user: AuthUser = Depends(
        require_permission(Permission.RBAC_READ, Permission.GROUPS_MANAGE)
    ),
):
    """Members of a group."""
    return _service().store.list_members(group_id)


@router.post("/groups/{group_id}/members", status_code=204)
async def add_member(
    group_id: str,
    body: AddMember,
    request: Request,
    user: AuthUser = Depends(
        require_permission(Permission.RBAC_MANAGE, Permission.GROUPS_MANAGE)
    ),
):
    """Add a user to a group."""
    store = _service().store
    _guard_group_membership(store, user, group_id)
    store.add_member(group_id, body.user_id, added_by=user.user_id)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.GROUP_MEMBER_ADDED,
        target_id=group_id,
        details={"user_id": body.user_id},
    )


@router.delete("/groups/{group_id}/members/{user_id}", status_code=204)
async def remove_member(
    group_id: str,
    user_id: str,
    request: Request,
    user: AuthUser = Depends(
        require_permission(Permission.RBAC_MANAGE, Permission.GROUPS_MANAGE)
    ),
):
    """Remove a user from a group."""
    store = _service().store
    _guard_group_membership(store, user, group_id)
    store.remove_member(group_id, user_id)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.GROUP_MEMBER_REMOVED,
        target_id=group_id,
        details={"user_id": user_id},
    )


@router.post("/groups/{group_id}/roles", status_code=204)
async def assign_group_role(
    group_id: str,
    body: AssignGroupRole,
    request: Request,
    user: AuthUser = Depends(
        require_permission(Permission.RBAC_MANAGE, Permission.GROUPS_MANAGE)
    ),
):
    """Grant a role to a group."""
    store = _service().store
    role = store.get_role(body.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    # A group carrying a wildcard/admin role makes every member an admin — same
    # escalation vector as a direct user-role grant, so apply the same gate.
    guard_role_assignment(user, group_id, role)
    store.assign_group_role(group_id, body.role_id)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.GROUP_ROLE_CHANGED,
        target_id=group_id,
        details={"assign": body.role_id},
    )


@router.delete("/groups/{group_id}/roles/{role_id}", status_code=204)
async def revoke_group_role(
    group_id: str,
    role_id: str,
    request: Request,
    user: AuthUser = Depends(
        require_permission(Permission.RBAC_MANAGE, Permission.GROUPS_MANAGE)
    ),
):
    """Remove a role grant from a group."""
    store = _service().store
    role = store.get_role(role_id)
    if role:
        guard_role_assignment(user, group_id, role)
    store.revoke_group_role(group_id, role_id)
    audit_rbac(
        request,
        user.user_id,
        AuditAction.GROUP_ROLE_CHANGED,
        target_id=group_id,
        details={"revoke": role_id},
    )
