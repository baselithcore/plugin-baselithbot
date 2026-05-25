"""User lifecycle endpoints (deactivate / hard delete).

Estratti da :mod:`llm_wiki.api.routers.rbac` per rispettare cap
500 LOC/file. Stesso prefix + stesso gating ``admin.user.manage``;
montato come router indipendente in :mod:`main` accanto a ``rbac``.

Guard cardinali (entrambi 403/409):

- Self-action vietata (no auto-deactivate, no auto-delete; per la
  self-delete c'è ``/api/gdpr/me`` con consent banner separato).
- Ultimo superuser attivo protetto via
  :func:`roles.is_last_active_superuser` — evita sysadmin lockout.

Audit kinds: ``admin.user.activate`` / ``admin.user.deactivate`` /
``admin.user.delete``.
"""

from __future__ import annotations

import logging
import secrets as _secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from llm_wiki.auth.audit import write_event
from llm_wiki.auth.dependencies import require_permission
from llm_wiki.auth.permissions import ROLE_ASSIGN_PERMISSION, Permission
from llm_wiki.db import roles as roles_db
from llm_wiki.db.tenants import create_tenant_with_owner, get_tenant_by_slug
from llm_wiki.db.users import (
    delete_user,
    get_user_by_id,
    hash_password,
    set_password_must_change,
    update_user,
)

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Lowercase + sostituisce non-alfanumerici con '-' (slug tenant)."""
    import re

    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:50] or "tenant"


class SetUserActiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool


class CreateUserRequest(BaseModel):
    """Admin-driven user creation. La password è impostata dall'admin
    + obbligatoriamente cambiata al primo login (``password_must_change=true``).

    ``role_slug`` opzionale: default ``user``. Per ``superuser``/``admin``/
    ``moderator`` l'actor deve possedere il corrispondente
    ``rbac.assign.<slug>`` — stesso guard di ``rbac.assign_role``.
    """

    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    display_name: str = Field(default="", max_length=120)
    role_slug: str | None = Field(default="user", max_length=50)
    tenant_name: str = Field(default="", max_length=120)


router = APIRouter(
    prefix="/api/admin/rbac",
    tags=["admin", "rbac", "users"],
    dependencies=[Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin"))],
)


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def _ensure_user_exists(user_id: str) -> dict:
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="utente non trovato")
    return target


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    body: CreateUserRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin")),
) -> dict:
    """Crea utente con password set dall'admin + ``password_must_change=true``.

    Equivalente admin-driven al ``/auth/register`` self-service: crea
    tenant + user atomicamente (1:1 invariant) via
    :func:`create_tenant_with_owner`. La differenza è il flag
    ``password_must_change`` settato subito dopo, che forza il primo
    login a passare per ``/auth/password`` prima di poter usare l'app
    (enforced sia lato BE — ``require_permission`` / ``require_admin``
    sollevano 403 con header ``X-Password-Must-Change`` — sia lato FE
    in ``App.tsx``).

    Guard:
    - ``rbac.assign.<role_slug>`` richiesto se ``role_slug`` system.
    - Email duplicata → 409.
    - Tenant slug auto-derivato dall'email; collision-suffix se occupato.
    """
    target_role = (body.role_slug or "user").strip()
    if target_role:
        required = ROLE_ASSIGN_PERMISSION.get(target_role)
        if not required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ruolo system non riconosciuto: '{target_role}'.",
            )
        if required not in (actor.get("perms") or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permesso richiesto per assegnare '{target_role}': {required}.",
            )

    # Auto-slug: local-part dell'email + suffix random se collisione.
    base_slug = _slugify(body.tenant_name or body.email.split("@")[0])
    tenant_slug = base_slug
    if get_tenant_by_slug(tenant_slug):
        tenant_slug = f"{base_slug}-{_secrets.token_hex(3)}"

    try:
        result = create_tenant_with_owner(
            tenant_name=body.tenant_name or body.display_name or body.email,
            tenant_slug=tenant_slug,
            user_email=str(body.email),
            user_password_hash=hash_password(body.password),
            user_display_name=body.display_name,
            plan="free",
            role=target_role,
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="email o slug tenant già esistenti",
            ) from exc
        logger.exception("[admin.create_user] failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="creazione utente fallita",
        ) from exc

    user = result["user"]
    tenant = result["tenant"]
    uid = str(user["id"])

    # Forza il cambio password al primo login.
    set_password_must_change(uid, True)

    # Se il role_slug è system → assegna anche il ruolo M:N (la colonna
    # users.role è legacy; il RBAC autoritativo è user_roles).
    if target_role:
        sys_role = next(
            (r for r in roles_db.list_roles() if r["slug"] == target_role and r["is_system"]),
            None,
        )
        if sys_role:
            roles_db.assign_role_to_user(uid, sys_role["id"], granted_by=actor["id"])

    write_event(
        "admin.user.create",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "target_user_id": uid,
            "target_email": user["email"],
            "tenant_id": str(tenant["id"]),
            "tenant_slug": tenant["slug"],
            "role_slug": target_role,
            "password_must_change": True,
        },
        ip_address=_client_ip(request),
    )

    return {
        "status": "ok",
        "user_id": uid,
        "tenant_id": str(tenant["id"]),
        "email": user["email"],
        "role_slug": target_role,
        "password_must_change": True,
    }


@router.patch("/users/{user_id}", status_code=status.HTTP_200_OK)
def set_user_active(
    user_id: str,
    body: SetUserActiveRequest,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin")),
) -> dict:
    """Attiva o disattiva un utente.

    Disattivazione preserva tutti i dati (conversations, memorie, ruoli);
    blocca solo il login (``users.is_active = FALSE`` + JWT esistenti
    invalidati al prossimo ``_resolve_user`` perché legge ``is_active``).
    Per cancellazione definitiva usare DELETE.
    """
    target = _ensure_user_exists(user_id)
    if user_id == actor["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auto-disattivazione non permessa.",
        )
    if not body.is_active and roles_db.is_last_active_superuser(user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossibile disattivare l'ultimo superuser attivo del sistema.",
        )
    updated = update_user(user_id, is_active=body.is_active)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="utente non trovato")
    write_event(
        "admin.user.activate" if body.is_active else "admin.user.deactivate",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "target_user_id": user_id,
            "target_email": target["email"],
            "is_active": body.is_active,
        },
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "is_active": body.is_active}


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user_endpoint(
    user_id: str,
    request: Request,
    actor: dict = Depends(require_permission(Permission.ADMIN_USER_MANAGE, rate_limit="admin")),
) -> dict:
    """Hard delete utente. CASCADE su refresh_tokens / conversations /
    memories / feedback / user_roles / user_domain_grants /
    group_members. ``audit_events.user_id`` ha SET NULL — traccia
    anonimizzata preservata per accountability log retention.

    Guard:
    - Auto-cancellazione vietata (passa da ``/api/gdpr/me`` self-delete
      con consent banner separato).
    - Cancellazione dell'ultimo superuser attivo vietata.
    """
    target = _ensure_user_exists(user_id)
    if user_id == actor["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auto-cancellazione non permessa via admin. Usa /gdpr/me.",
        )
    if roles_db.is_last_active_superuser(user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossibile cancellare l'ultimo superuser attivo del sistema.",
        )
    removed = delete_user(user_id)
    write_event(
        "admin.user.delete",
        tenant_id=actor.get("tenant_id"),
        user_id=actor["id"],
        payload={
            "target_user_id": user_id,
            "target_email": target["email"],
            "noop": not removed,
        },
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "removed": removed}


__all__ = ["router"]
