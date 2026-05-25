"""RBAC management endpoints (Fase 7).

Surface
-------

``GET    /api/admin/rbac/permissions``           — catalogo permessi.
``GET    /api/admin/rbac/roles``                 — lista ruoli (globali +
                                                   tenant del caller).
``GET    /api/admin/rbac/roles/{role_id}``       — dettaglio + permessi.
``GET    /api/admin/rbac/users``                 — utenti + loro ruoli.
``POST   /api/admin/rbac/users/{uid}/roles``     — assegna ruolo.
``DELETE /api/admin/rbac/users/{uid}/roles/{rid}``— revoca ruolo.
``POST   /api/admin/rbac/users/{uid}/domains``   — grant domain.
``DELETE /api/admin/rbac/users/{uid}/domains/{slug}`` — revoca domain.

Gating: tutti gli endpoint richiedono ``admin.user.manage``. È un
permesso granulare, non `require_admin` legacy — un futuro ruolo
"user-admin" (gestisce utenti senza accesso a scaffold/runtime) lo
ottiene senza diventare full admin.

Audit: ogni mutation scrive ``rbac.role.assign`` / ``rbac.role.revoke``
/ ``rbac.domain.grant`` / ``rbac.domain.revoke`` su ``audit_events``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from llm_wiki.auth.audit import write_event
from llm_wiki.auth.dependencies import require_permission
from llm_wiki.auth.permissions import (
    ALL_PERMISSIONS,
    ROLE_ASSIGN_PERMISSION,
    Permission,
)
from llm_wiki.db import roles as roles_db
from llm_wiki.db.users import get_user_by_id, list_users

logger = logging.getLogger(__name__)


# --- request/response models ----------------------------------------------


class PermissionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    description: str = ""


class RoleSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    slug: str
    name: str
    description: str = ""
    is_system: bool
    tenant_id: str | None = None


class RoleDetail(RoleSummary):
    permissions: list[str] = Field(default_factory=list)


class DomainGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain_slug: str
    role_id: str | None = None
    role_slug: str | None = None


class UserWithRoles(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    email: str
    display_name: str = ""
    tenant_id: str
    role: str  # legacy
    is_active: bool
    roles: list[RoleSummary] = Field(default_factory=list)
    # Slug-only per back-compat / componenti consumer esistenti.
    domains: list[str] = Field(default_factory=list)
    # Nuovo: dettaglio per UI admin (slug + ruolo per-dominio).
    domain_grants: list[DomainGrant] = Field(default_factory=list)


class SetRolePermissionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    permissions: list[str]


class AssignRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_id: str


class GrantDomainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain_slug: str
    role_id: str | None = None


# --- router ----------------------------------------------------------------


router = APIRouter(
    prefix="/api/admin/rbac",
    tags=["admin", "rbac"],
    dependencies=[Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin"))],
)


@router.get("/permissions", response_model=list[PermissionEntry])
def list_permissions() -> list[PermissionEntry]:
    """Catalogo statico — proviene da :mod:`llm_wiki.auth.permissions`.

    Esposto via API per popolare la UI admin senza cablare le stringhe
    nel frontend.
    """
    return [PermissionEntry(slug=slug, description="") for slug in sorted(ALL_PERMISSIONS)]


@router.get("/roles", response_model=list[RoleSummary])
def list_roles_endpoint(
    user: dict = Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin")),
) -> list[RoleSummary]:
    rows = roles_db.list_roles(tenant_id=user.get("tenant_id"))
    return [RoleSummary(**r) for r in rows]


@router.get("/roles/{role_id}", response_model=RoleDetail)
def get_role(role_id: str) -> RoleDetail:
    rows = roles_db.list_roles()
    match = next((r for r in rows if r["id"] == role_id), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ruolo non trovato")
    perms = roles_db.get_role_permissions(role_id)
    return RoleDetail(**match, permissions=perms)


@router.put("/roles/{role_id}/permissions", response_model=RoleDetail)
def update_role_permissions(
    role_id: str,
    body: SetRolePermissionsRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin")),
) -> RoleDetail:
    """Sostituisce i permessi di un ruolo.

    Guard:
    - Solo chi possiede ``rbac.assign.admin`` può modificare ruoli — è il
      permesso più alto delegabile via UI.
    - Slug invalidi → 400.
    - Ruolo system ``superuser`` deve sempre conservare TUTTI i permessi
      (invariante: il bootstrap admin parte da quel ruolo).
    - Ruoli system non-superuser modificabili: scelta esplicita per
      rendere la matrice ruolo×permesso self-service.
    """
    role = _ensure_role_exists(role_id)
    actor_perms = set(actor.get("perms") or [])
    if Permission.RBAC_ASSIGN_ADMIN not in actor_perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permesso richiesto per modificare i permessi dei ruoli: rbac.assign.admin.",
        )
    requested = set(body.permissions)
    invalid = sorted(requested - ALL_PERMISSIONS)
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Permessi sconosciuti: {', '.join(invalid)}",
        )
    if role.get("is_system") and role["slug"] == "superuser":
        if requested != ALL_PERMISSIONS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Il ruolo superuser deve conservare tutti i permessi.",
            )
    diff = roles_db.set_role_permissions(role_id, sorted(requested))
    write_event(
        "rbac.role.permissions.update",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "role_id": role_id,
            "role_slug": role["slug"],
            "added": diff["added"],
            "removed": diff["removed"],
        },
        ip_address=_client_ip(request),
    )
    perms = roles_db.get_role_permissions(role_id)
    return RoleDetail(**role, permissions=perms)


@router.get("/users", response_model=list[UserWithRoles])
def list_users_with_roles() -> list[UserWithRoles]:
    """Bypassa RLS: richiede di girare come superuser o role con
    BYPASSRLS. Vedi :func:`llm_wiki.db.users.list_users`."""
    out: list[UserWithRoles] = []
    for u in list_users():
        uid = u["id"]
        roles = [RoleSummary(**r) for r in roles_db.get_user_roles(uid)]
        grants_detailed = [DomainGrant(**g) for g in roles_db.get_user_domain_grants_detailed(uid)]
        domains = [g.domain_slug for g in grants_detailed]
        out.append(
            UserWithRoles(
                id=uid,
                email=u["email"],
                display_name=u.get("display_name", ""),
                tenant_id=u["tenant_id"],
                role=u["role"],
                is_active=u.get("is_active", True),
                roles=roles,
                domains=domains,
                domain_grants=grants_detailed,
            )
        )
    return out


def _ensure_user_exists(user_id: str) -> dict:
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="utente non trovato")
    return target


def _ensure_role_exists(role_id: str) -> dict:
    rows = roles_db.list_roles()
    match = next((r for r in rows if r["id"] == role_id), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ruolo non trovato")
    return match


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/users/{user_id}/roles", status_code=status.HTTP_201_CREATED)
def assign_role(
    user_id: str,
    body: AssignRoleRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin")),
) -> dict:
    target = _ensure_user_exists(user_id)
    role = _ensure_role_exists(body.role_id)

    # Self-escalation guard: un actor non può modificare i propri ruoli.
    # Anche con `admin.user.manage` + `rbac.assign.X` un admin con
    # `rbac.assign.moderator` potrebbe auto-assegnarsi `moderator` e via
    # via accumulare permessi attraverso revoche/riassegnazioni. Niente
    # self-mutation — chi vuole promozioni passa da un ruolo superiore.
    if user_id == actor["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autoassegnazione dei ruoli non permessa.",
        )

    # Hierarchy enforcement (008): l'actor deve possedere il permesso
    # `rbac.assign.<slug>` corrispondente al ruolo target. Esempio:
    # - admin (con `rbac.assign.moderator`) può assegnare `moderator` ✓
    # - admin NON può assegnare `admin` o `superuser` ✗
    # - moderator (con `rbac.assign.user`) può solo creare user
    # Per ruoli custom (tenant-scoped, non system) richiediamo il
    # permesso più alto `rbac.assign.admin` — il sistema non sa a priori
    # quanto siano potenti.
    if role.get("is_system"):
        required = ROLE_ASSIGN_PERMISSION.get(role["slug"], Permission.RBAC_ASSIGN_ADMIN)
    else:
        required = Permission.RBAC_ASSIGN_ADMIN
    actor_perms = set(actor.get("perms") or [])
    if required not in actor_perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permesso richiesto per assegnare '{role['slug']}': {required}.",
        )

    inserted = roles_db.assign_role_to_user(user_id, body.role_id, granted_by=actor["id"])
    write_event(
        "rbac.role.assign",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "target_user_id": user_id,
            "target_email": target["email"],
            "role_id": body.role_id,
            "role_slug": role["slug"],
            "noop": not inserted,
        },
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "noop": not inserted}


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_200_OK)
def revoke_role(
    user_id: str,
    role_id: str,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin")),
) -> dict:
    target = _ensure_user_exists(user_id)
    role = _ensure_role_exists(role_id)

    # Self-escalation guard simmetrico ad assign_role.
    if user_id == actor["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autorevoca dei ruoli non permessa.",
        )

    # Hierarchy: chi revoca deve avere il permesso di assegnare lo
    # stesso ruolo (simmetria). Un moderatore con rbac.assign.user può
    # quindi anche degradare un user, ma non un admin.
    if role.get("is_system"):
        required = ROLE_ASSIGN_PERMISSION.get(role["slug"], Permission.RBAC_ASSIGN_ADMIN)
    else:
        required = Permission.RBAC_ASSIGN_ADMIN
    actor_perms = set(actor.get("perms") or [])
    if required not in actor_perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permesso richiesto per revocare '{role['slug']}': {required}.",
        )
    try:
        removed = roles_db.revoke_role_from_user(user_id, role_id)
    except roles_db.LastSuperuserError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    write_event(
        "rbac.role.revoke",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "target_user_id": user_id,
            "target_email": target["email"],
            "role_id": role_id,
            "role_slug": role["slug"],
            "noop": not removed,
        },
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "removed": removed}


@router.post("/users/{user_id}/domains", status_code=status.HTTP_201_CREATED)
def grant_domain(
    user_id: str,
    body: GrantDomainRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin")),
) -> dict:
    target = _ensure_user_exists(user_id)
    if user_id == actor["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autograntazione dominio non permessa.",
        )
    if body.role_id:
        _ensure_role_exists(body.role_id)
    ok = roles_db.grant_domain_access(
        user_id,
        body.domain_slug,
        role_id=body.role_id,
        granted_by=actor["id"],
    )
    write_event(
        "rbac.domain.grant",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "target_user_id": user_id,
            "target_email": target["email"],
            "domain_slug": body.domain_slug,
            "role_id": body.role_id,
        },
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "applied": ok}


@router.delete("/users/{user_id}/domains/{domain_slug}", status_code=status.HTTP_200_OK)
def revoke_domain(
    user_id: str,
    domain_slug: str,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin")),
) -> dict:
    target = _ensure_user_exists(user_id)
    if user_id == actor["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autorevoca dominio non permessa.",
        )
    removed = roles_db.revoke_domain_access(user_id, domain_slug)
    write_event(
        "rbac.domain.revoke",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "target_user_id": user_id,
            "target_email": target["email"],
            "domain_slug": domain_slug,
            "noop": not removed,
        },
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "removed": removed}


__all__ = ["router"]
