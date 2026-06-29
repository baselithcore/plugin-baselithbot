"""Resilient auth guards for the compliance-console routes.

The bundled ``auth`` plugin's ``require_auth`` eagerly resolves the auth
persistence/manager layer, which 503s when auth runs self-contained (no backing
store). These guards consult ``AuthConfig`` first and only touch the auth
subsystem when authentication is actually **enforced** (``auth_required=true``):

* reads are open when auth is not enforced, and require a validated credential
  when it is — never 503 on a half-initialised auth subsystem;
* mutations require effective-admin when auth is enforced; when it is not, they
  are allowed only if the operator relaxed ``require_admin`` (else 403).

Admin is decided from the **effective permission set** (wildcard), not the
literal :data:`AuthRole.ADMIN` enum — mirroring the central gates, so a
custom-role wildcard admin is recognised. Degrades closed for elevation.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth.types import AuthRole, AuthUser

from ..config import ComplianceConfig

_bearer = HTTPBearer(auto_error=False)


def _auth_config() -> Any:
    """Return the registered AuthConfig, or None if the auth plugin is absent."""
    try:
        from core.di.container import ServiceRegistry
        from plugins.auth.config import AuthConfig

        return ServiceRegistry.get(AuthConfig)
    except Exception:  # noqa: BLE001 — auth optional; degrade gracefully
        return None


def _auth_enforced() -> bool:
    cfg = _auth_config()
    return bool(getattr(cfg, "auth_required", False)) if cfg is not None else False


def is_admin(user: AuthUser) -> bool:
    """Whether the caller has full (effective-wildcard) admin privileges.

    Mirrors the central gates: an admin can be provisioned via a custom RBAC
    role granted the wildcard (``*``) permission, in which case the literal
    :data:`AuthRole.ADMIN` is absent from ``user.roles``. Falls back to the
    literal role when the RBAC service is unavailable (degrade closed).
    """
    if user.has_role(AuthRole.ADMIN):
        return True
    try:
        from plugins.auth.rbac.permissions import WILDCARD, has_permission
        from plugins.auth.rbac.service import get_rbac_service

        perms = get_rbac_service().effective_permissions(user.user_id, user.roles)
        return has_permission(perms, WILDCARD)
    except Exception:  # noqa: BLE001 — RBAC optional; degrade to the role check
        return False


async def read_guard(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """Allow read-only access; when auth is enforced, fully validate the caller."""
    if not _auth_enforced():
        return
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    from plugins.auth.dependencies import get_current_user

    user = await get_current_user(request, creds)
    if not user.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def admin_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthUser:
    """Gate a mutation behind effective-admin, without 503-ing on no-auth."""
    if not _auth_enforced():
        if ComplianceConfig().require_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="admin role required (auth not configured)",
            )
        return AuthUser(user_id="local", roles={AuthRole.ADMIN})

    from plugins.auth.dependencies import get_current_user

    user = await get_current_user(request, creds)
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="admin role required"
        )
    return user


__all__ = ["read_guard", "admin_principal", "is_admin"]
