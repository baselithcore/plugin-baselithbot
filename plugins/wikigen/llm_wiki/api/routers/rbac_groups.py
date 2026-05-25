"""Groups management endpoints (mig 015).

Surface
-------

``GET    /api/admin/rbac/groups``                       — list (tenant del caller)
``POST   /api/admin/rbac/groups``                       — create
``GET    /api/admin/rbac/groups/{gid}``                 — detail + members + roles
``PATCH  /api/admin/rbac/groups/{gid}``                 — rename / desc
``DELETE /api/admin/rbac/groups/{gid}``                 — delete (rifiuta is_system)
``POST   /api/admin/rbac/groups/{gid}/members``         — bulk add { user_ids }
``DELETE /api/admin/rbac/groups/{gid}/members/{uid}``   — remove
``POST   /api/admin/rbac/groups/{gid}/roles``           — assign { role_id }
``DELETE /api/admin/rbac/groups/{gid}/roles/{rid}``     — revoke

Gating: ``admin.group.manage`` (mig 015 seed superuser+admin).
Role-assign aggiuntivo: chi associa un ruolo a un gruppo deve possedere
anche il corrispondente ``rbac.assign.<slug>`` — stesso guard anti-
escalation di :mod:`llm_wiki.api.routers.rbac` ``assign_role``: un
moderator non può iniettare ``admin`` su un gruppo per scalare via
membership.

Audit: ``group.{created,updated,deleted,member.added,member.removed,
role.granted,role.revoked}`` su ``audit_events``.

Cross-tenant: ogni mutation valida ``target.tenant_id ==
actor.tenant_id`` (oltre alla RLS che già nega la lettura cross-tenant).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from llm_wiki.auth.audit import write_event
from llm_wiki.auth.dependencies import require_permission
from llm_wiki.auth.permissions import (
    ROLE_ASSIGN_PERMISSION,
    Permission,
)
from llm_wiki.db import groups as groups_db
from llm_wiki.db import roles as roles_db

logger = logging.getLogger(__name__)


# --- models ---------------------------------------------------------------


class GroupSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    slug: str
    name: str
    description: str = ""
    is_system: bool
    tenant_id: str
    member_count: int = 0
    role_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class GroupMember(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    email: str
    display_name: str = ""
    role: str
    is_active: bool
    added_at: str | None = None
    added_by: str | None = None


class GroupRoleEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    slug: str
    name: str
    description: str = ""
    is_system: bool
    tenant_id: str | None = None
    granted_at: str | None = None
    granted_by: str | None = None


class GroupDetail(GroupSummary):
    members: list[GroupMember] = Field(default_factory=list)
    roles: list[GroupRoleEntry] = Field(default_factory=list)


class CreateGroupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class UpdateGroupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class AddMembersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_ids: list[str] = Field(min_length=1, max_length=200)


class AssignGroupRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_id: str


# --- router ---------------------------------------------------------------


router = APIRouter(
    prefix="/api/admin/rbac/groups",
    tags=["admin", "rbac", "groups"],
    dependencies=[Depends(require_permission(Permission.ADMIN_GROUP_MANAGE, rate_limit="admin"))],
)


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def _ensure_group(group_id: str, actor: dict) -> dict:
    group = groups_db.get_group_by_id(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="gruppo non trovato")
    # Cross-tenant guard: anche se RLS è OFF (superuser bypass), un admin
    # tenant A non deve poter agire su gruppi tenant B.
    actor_tid = actor.get("tenant_id")
    if actor_tid and group["tenant_id"] != actor_tid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="gruppo non trovato",
        )
    return group


@router.get("", response_model=list[GroupSummary])
def list_groups_endpoint(
    actor: dict = Depends(require_permission(Permission.ADMIN_GROUP_MANAGE, rate_limit="admin")),
) -> list[GroupSummary]:
    tenant_id = actor["tenant_id"]
    rows = groups_db.list_groups(tenant_id)
    return [GroupSummary(**r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=GroupSummary)
def create_group_endpoint(
    body: CreateGroupRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_GROUP_MANAGE, rate_limit="admin")),
) -> GroupSummary:
    tenant_id = actor["tenant_id"]
    try:
        created = groups_db.create_group(
            tenant_id=tenant_id,
            slug=body.slug,
            name=body.name,
            description=body.description,
        )
    except Exception as exc:
        # Slug duplicato → IntegrityError (psycopg.errors.UniqueViolation).
        # Risposta 409 invece del 500 generico per UX admin chiara.
        if "uq_groups_tenant_slug" in str(exc) or "duplicate key" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"slug '{body.slug}' già usato in questo tenant",
            ) from exc
        raise
    write_event(
        "group.created",
        tenant_id=tenant_id,
        user_id=actor["id"],
        payload={"group_id": created["id"], "slug": created["slug"], "name": created["name"]},
        ip_address=_client_ip(request),
    )
    return GroupSummary(**created)


@router.get("/{group_id}", response_model=GroupDetail)
def get_group_endpoint(
    group_id: str,
    actor: dict = Depends(require_permission(Permission.ADMIN_GROUP_MANAGE, rate_limit="admin")),
) -> GroupDetail:
    group = _ensure_group(group_id, actor)
    members = [GroupMember(**m) for m in groups_db.get_group_members(group_id)]
    roles = [GroupRoleEntry(**r) for r in groups_db.get_group_roles(group_id)]
    return GroupDetail(**group, members=members, roles=roles)


@router.patch("/{group_id}", response_model=GroupSummary)
def update_group_endpoint(
    group_id: str,
    body: UpdateGroupRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_GROUP_MANAGE, rate_limit="admin")),
) -> GroupSummary:
    group = _ensure_group(group_id, actor)
    updated = groups_db.update_group(
        group_id,
        name=body.name,
        description=body.description,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="gruppo non trovato")
    write_event(
        "group.updated",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "group_id": group_id,
            "slug": group["slug"],
            "fields": {k: v for k, v in body.model_dump(exclude_none=True).items()},
        },
        ip_address=_client_ip(request),
    )
    return GroupSummary(**updated)


@router.delete("/{group_id}", status_code=status.HTTP_200_OK)
def delete_group_endpoint(
    group_id: str,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_GROUP_MANAGE, rate_limit="admin")),
) -> dict:
    group = _ensure_group(group_id, actor)
    try:
        removed = groups_db.delete_group(group_id)
    except groups_db.SystemGroupProtected as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    write_event(
        "group.deleted",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={"group_id": group_id, "slug": group["slug"], "noop": not removed},
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "removed": removed}


@router.post("/{group_id}/members", status_code=status.HTTP_201_CREATED)
def add_members_endpoint(
    group_id: str,
    body: AddMembersRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_GROUP_MANAGE, rate_limit="admin")),
) -> dict:
    group = _ensure_group(group_id, actor)
    result = groups_db.add_members_bulk(group_id, body.user_ids, added_by=actor["id"])
    write_event(
        "group.member.added",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "group_id": group_id,
            "slug": group["slug"],
            "added": result["added"],
            "skipped": result["skipped"],
        },
        ip_address=_client_ip(request),
    )
    return {"status": "ok", **result}


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_200_OK)
def remove_member_endpoint(
    group_id: str,
    user_id: str,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_GROUP_MANAGE, rate_limit="admin")),
) -> dict:
    group = _ensure_group(group_id, actor)
    removed = groups_db.remove_member(group_id, user_id)
    write_event(
        "group.member.removed",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "group_id": group_id,
            "slug": group["slug"],
            "target_user_id": user_id,
            "noop": not removed,
        },
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "removed": removed}


@router.post("/{group_id}/roles", status_code=status.HTTP_201_CREATED)
def assign_role_endpoint(
    group_id: str,
    body: AssignGroupRoleRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_GROUP_MANAGE, rate_limit="admin")),
) -> dict:
    group = _ensure_group(group_id, actor)
    role = next(
        (
            r
            for r in roles_db.list_roles(tenant_id=actor.get("tenant_id"))
            if r["id"] == body.role_id
        ),
        None,
    )
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ruolo non trovato")

    # Anti-escalation: chi associa il ruolo deve avere lo stesso permesso
    # richiesto per assegnarlo a un utente direttamente. Senza questo,
    # un moderator con admin.group.manage potrebbe creare un gruppo
    # con ruolo admin e auto-aggiungersi.
    if role.get("is_system"):
        required = ROLE_ASSIGN_PERMISSION.get(role["slug"], Permission.RBAC_ASSIGN_ADMIN)
    else:
        required = Permission.RBAC_ASSIGN_ADMIN
    if required not in (actor.get("perms") or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permesso richiesto per associare '{role['slug']}': {required}.",
        )

    try:
        inserted = groups_db.assign_role(group_id, body.role_id, granted_by=actor["id"])
    except groups_db.CrossTenantError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    write_event(
        "group.role.granted",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "group_id": group_id,
            "slug": group["slug"],
            "role_id": body.role_id,
            "role_slug": role["slug"],
            "noop": not inserted,
        },
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "noop": not inserted}


@router.delete("/{group_id}/roles/{role_id}", status_code=status.HTTP_200_OK)
def revoke_role_endpoint(
    group_id: str,
    role_id: str,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_GROUP_MANAGE, rate_limit="admin")),
) -> dict:
    group = _ensure_group(group_id, actor)
    # Anti-escalation simmetrico: revocare un ruolo da un gruppo richiede
    # il permesso `rbac.assign.<slug>` corrispondente.
    role = next(
        (r for r in roles_db.list_roles(tenant_id=actor.get("tenant_id")) if r["id"] == role_id),
        None,
    )
    if role:
        if role.get("is_system"):
            required = ROLE_ASSIGN_PERMISSION.get(role["slug"], Permission.RBAC_ASSIGN_ADMIN)
        else:
            required = Permission.RBAC_ASSIGN_ADMIN
        if required not in (actor.get("perms") or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permesso richiesto per revocare '{role['slug']}': {required}.",
            )
    removed = groups_db.revoke_role(group_id, role_id)
    write_event(
        "group.role.revoked",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "group_id": group_id,
            "slug": group["slug"],
            "role_id": role_id,
            "role_slug": role["slug"] if role else None,
            "noop": not removed,
        },
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "removed": removed}


__all__ = ["router"]
