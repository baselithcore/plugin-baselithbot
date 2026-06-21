"""Admin endpoints for tenant provisioning and membership management.

Two privilege tiers:

* **Platform admin** (effective wildcard / ``AuthRole.ADMIN``) — full control:
  create/list/suspend/delete tenants and manage any tenant's members.
* **Tenant admin** (``auth_user_tenants.role = 'admin'`` for a given tenant) —
  manages members of *that* tenant only, without platform-wide power.

Tenant *lifecycle* stays platform-only; *membership* is open to the tenant's
own admins. Every mutation is audited.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.admin_router._helpers import get_client_ip
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_persistence_dep,
    require_auth,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.rbac.service import is_effective_admin
from plugins.auth.router._models import MessageResponse
from plugins.auth.router._tenant_models import (
    AddMemberRequest,
    CreateTenantRequest,
    TenantMemberOut,
    TenantOut,
    TenantPurgeResult,
    TenantStatusRequest,
)

logger = get_logger(__name__)

router = APIRouter()

_VALID_STATUS = {"active", "suspended"}


def _ensure_platform_admin(user: AuthUser) -> None:
    """Gate tenant lifecycle (create/suspend/delete) to platform admins only."""
    if not is_effective_admin(user.user_id, user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires platform admin",
        )


def _ensure_can_manage_members(
    tenant_id: str, user: AuthUser, persistence: AuthPersistence
) -> None:
    """Allow a platform admin OR the tenant's own admin to manage its members."""
    if is_effective_admin(user.user_id, user.roles):
        return
    if persistence.is_member_admin(user.user_id, tenant_id):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Requires platform admin or tenant admin",
    )


def _tenant_out(row: dict) -> TenantOut:
    return TenantOut(
        id=str(row["id"]),
        slug=row["slug"],
        name=row["name"],
        status=row["status"],
        member_count=int(row.get("member_count", 0) or 0),
    )


@router.post("/tenants", response_model=TenantOut, status_code=201)
async def create_tenant(
    body: CreateTenantRequest,
    request: Request,
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> TenantOut:
    """Provision a new tenant. Slug must be unique. Platform admin only."""
    _ensure_platform_admin(user)
    row = persistence.create_tenant(body.slug.strip(), body.name.strip())
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists"
        )
    audit.log(
        action=AuditAction.TENANT_CREATED,
        actor_id=user.user_id,
        target_id=str(row["id"]),
        details={"slug": body.slug, "name": body.name},
        ip_address=get_client_ip(request),
    )
    return _tenant_out(row)


@router.get("/tenants", response_model=List[TenantOut])
async def list_tenants(
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> List[TenantOut]:
    """List every tenant with its member count. Platform admin only."""
    _ensure_platform_admin(user)
    return [_tenant_out(r) for r in persistence.list_tenants()]


@router.patch("/tenants/{tenant_id}/status", response_model=MessageResponse)
async def set_tenant_status(
    tenant_id: str,
    body: TenantStatusRequest,
    request: Request,
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> MessageResponse:
    """Activate or suspend a tenant. Suspending it drops its members off it at
    their next token refresh. Platform admin only."""
    _ensure_platform_admin(user)
    new_status = body.status.strip().lower()
    if new_status not in _VALID_STATUS:
        raise HTTPException(status_code=400, detail="status must be active|suspended")
    if not persistence.set_tenant_status(tenant_id, new_status):
        raise HTTPException(status_code=404, detail="Tenant not found")
    audit.log(
        action=AuditAction.TENANT_STATUS_CHANGED,
        actor_id=user.user_id,
        target_id=tenant_id,
        details={"status": new_status},
        ip_address=get_client_ip(request),
    )
    return MessageResponse(message=f"Tenant {new_status}")


@router.delete("/tenants/{tenant_id}", response_model=MessageResponse)
async def delete_tenant(
    tenant_id: str,
    request: Request,
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> MessageResponse:
    """Delete a tenant; membership cascades. Tenant-scoped data in other plugins
    is NOT purged here — see the tenant-lifecycle roadmap. Platform admin only."""
    _ensure_platform_admin(user)
    if not persistence.delete_tenant(tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    audit.log(
        action=AuditAction.TENANT_DELETED,
        actor_id=user.user_id,
        target_id=tenant_id,
        ip_address=get_client_ip(request),
    )
    return MessageResponse(message="Tenant deleted")


@router.post("/tenants/{tenant_id}/purge", response_model=TenantPurgeResult)
async def purge_tenant(
    tenant_id: str,
    request: Request,
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> TenantPurgeResult:
    """GDPR right-to-be-forgotten: delete ALL data scoped to this tenant across
    every store (core + plugins), without removing the tenant itself. Platform
    admin only; irreversible; audited with per-table row counts."""
    _ensure_platform_admin(user)
    if persistence.get_tenant(tenant_id) is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    from core.services.tenant import purge_tenant_data

    deleted = await purge_tenant_data(tenant_id)
    total = sum(deleted.values())
    audit.log(
        action=AuditAction.TENANT_PURGED,
        actor_id=user.user_id,
        target_id=tenant_id,
        details={"deleted": deleted, "total": total},
        ip_address=get_client_ip(request),
    )
    logger.warning(
        "Tenant %s data purged by %s: %s rows", tenant_id, user.user_id, total
    )
    return TenantPurgeResult(deleted=deleted, total=total)


@router.get("/tenants/{tenant_id}/members", response_model=List[TenantMemberOut])
async def list_members(
    tenant_id: str,
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> List[TenantMemberOut]:
    """Users assigned to a tenant. Platform admin or this tenant's admin."""
    _ensure_can_manage_members(tenant_id, user, persistence)
    if persistence.get_tenant(tenant_id) is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return [
        TenantMemberOut(
            user_id=str(m["user_id"]),
            email=m.get("email"),
            username=m.get("username"),
            role=m["role"],
            is_default=bool(m["is_default"]),
        )
        for m in persistence.list_members(tenant_id)
    ]


@router.post("/tenants/{tenant_id}/members", response_model=MessageResponse)
async def add_member(
    tenant_id: str,
    body: AddMemberRequest,
    request: Request,
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> MessageResponse:
    """Assign a user to a tenant (their first tenant becomes their default).
    Platform admin or this tenant's admin."""
    _ensure_can_manage_members(tenant_id, user, persistence)
    if persistence.get_tenant(tenant_id) is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if persistence.get_user_by_id(body.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not persistence.add_member(
        tenant_id, body.user_id, role=body.role, added_by=user.user_id
    ):
        raise HTTPException(status_code=400, detail="Could not add member")
    audit.log(
        action=AuditAction.TENANT_MEMBER_ADDED,
        actor_id=user.user_id,
        target_id=body.user_id,
        details={"tenant_id": tenant_id, "role": body.role},
        ip_address=get_client_ip(request),
    )
    return MessageResponse(message="Member added")


@router.delete("/tenants/{tenant_id}/members/{user_id}", response_model=MessageResponse)
async def remove_member(
    tenant_id: str,
    user_id: str,
    request: Request,
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> MessageResponse:
    """Remove a user from a tenant (their default is reassigned if needed).
    Platform admin or this tenant's admin."""
    _ensure_can_manage_members(tenant_id, user, persistence)
    if not persistence.remove_member(tenant_id, user_id):
        raise HTTPException(status_code=404, detail="Membership not found")
    audit.log(
        action=AuditAction.TENANT_MEMBER_REMOVED,
        actor_id=user.user_id,
        target_id=user_id,
        details={"tenant_id": tenant_id},
        ip_address=get_client_ip(request),
    )
    return MessageResponse(message="Member removed")
