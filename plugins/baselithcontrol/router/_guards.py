"""Resilient auth guards for the control-plane routes.

The bundled ``auth`` plugin's ``require_auth`` eagerly resolves the auth
persistence/manager layer, which 503s when auth runs self-contained (no
backing store). That would take the whole read-only dashboard down. These
guards therefore consult ``AuthConfig`` first and only touch the auth subsystem
when authentication is actually **enforced** (``auth_required=true``):

* reads are open when auth is not enforced, and require a presented credential
  when it is — never 503 on a half-initialized auth subsystem;
* mutations require the ``admin`` role when auth is enforced; when it is not,
  they are allowed only if the operator relaxed ``require_admin`` (else 403).

Full credential validation still runs through the auth plugin whenever auth is
enforced — the resilient path only covers the unauthenticated/self-contained
deployment so the control plane stays usable out of the box.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth.types import AuthRole, AuthUser

from ..config import ControlConfig

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
    """Whether the caller has full (admin) privileges.

    The built-in :data:`AuthRole.ADMIN` is not the only way to be an admin: the
    auth plugin's RBAC hub lets an admin be provisioned via a **custom role**
    granted the wildcard (``*``) permission, in which case the literal enum is
    absent from ``user.roles`` (unknown role strings are dropped when the token
    is decoded). The central gates (``require_permission``,
    ``PluginAccessMiddleware``) already key off the *effective permission set*,
    so this mirrors them — otherwise a wildcard-admin would pass every other
    guard yet be misread as a plain user here and lose sight of disabled/failed
    plugins (and the lifecycle controls). Falls back to the literal role when
    the RBAC service is unavailable, so nothing regresses without it.
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


def system_visibility(user: AuthUser) -> Callable[[str], bool] | None:
    """Decide which **system-tier** plugins (manifest ``system: true``) a caller sees.

    System plugins are platform infrastructure (auth, the control plane itself,
    …): privileged surfaces that are hidden from ordinary users by default and
    surfaced only when an admin explicitly grants them through the central
    Access Control matrix — least privilege, secure-by-default.

    * Admins get ``None`` — no gating; every system plugin is visible.
    * Otherwise a ``name -> bool`` predicate: a system plugin is visible only
      when the central RBAC policy grants the caller at least one of its tabs.
      It fails **closed** for the system tier — if the policy cannot be read the
      predicate denies every system plugin — so a degraded RBAC layer never
      leaks infrastructure. Ordinary ('application') plugins are untouched by
      this predicate and keep their default-allow visibility.
    """
    if is_admin(user):
        return None
    allowed: set[str] = set()
    try:
        from plugins.auth.rbac.service import get_rbac_service

        tabs = get_rbac_service().accessible_tabs(user.user_id, user.roles)
        allowed = {t["plugin"] for t in tabs if t.get("system") and t.get("allowed")}
    except Exception:  # noqa: BLE001 — fail closed for the system tier
        allowed = set()
    return lambda name: name in allowed


async def _resolve_real_user(
    request: Request, creds: HTTPAuthorizationCredentials | None
) -> AuthUser | None:
    """Best-effort resolution of the logged-in user from bearer/cookie.

    Lets the control plane honour a real session (e.g. an admin logged into the
    auth console, whose refresh cookie is sent same-origin) even when global
    ``auth_required`` is off — so access is driven by *your* account, not a
    synthetic local operator. Never raises (degrades to ``None``).
    """
    try:
        from core.di.container import ServiceRegistry
        from core.auth import AuthManager
        from plugins.auth.config import AuthConfig
        from plugins.auth.persistence import AuthPersistence

        manager = ServiceRegistry.get(AuthManager)
        if creds and manager is not None:
            user = await manager.authenticate(f"Bearer {creds.credentials}")
            if user.is_authenticated:
                return user

        cfg = ServiceRegistry.get(AuthConfig)
        cookie_name = getattr(cfg, "cookie_name", "refresh_token")
        token = request.cookies.get(cookie_name)
        if token:
            persistence = ServiceRegistry.get(AuthPersistence)
            user_id = persistence.validate_refresh_token(token) if persistence else None
            if user_id:
                db_user = persistence.get_user_by_id(user_id)
                if db_user and db_user.is_active and not db_user.is_locked():
                    return AuthUser(
                        user_id=db_user.id, email=db_user.email, roles=db_user.roles
                    )
    except Exception:  # noqa: BLE001 — identity is best-effort here
        return None
    return None


async def read_guard(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """Allow read-only access; when auth is enforced, fully validate the caller.

    Off-auth (self-contained) the read path stays open — and never touches the
    auth persistence layer that would 503. When auth is enforced the token is
    validated through the auth subsystem (presence alone is not sufficient), so
    a forged/expired bearer is rejected.
    """
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


async def current_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthUser:
    """Resolve the caller for identity/audit, degrading cleanly when auth is off.

    When auth is not enforced the caller is a local operator — reported as
    ``admin`` only if ``require_admin`` is relaxed, so the UI's controls match
    what the backend will actually permit.
    """
    if not _auth_enforced():
        # Prefer the real logged-in user (your account) when a session exists.
        real = await _resolve_real_user(request, creds)
        if real is not None:
            return real
        role = AuthRole.USER if ControlConfig().require_admin else AuthRole.ADMIN
        return AuthUser(user_id="local", roles={role})
    from plugins.auth.dependencies import get_current_user

    return await get_current_user(request, creds)


async def admin_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthUser:
    """Gate a mutation behind the ``admin`` role, without 503-ing on no-auth."""
    if not _auth_enforced():
        # Honour a real session first: a logged-in admin passes; a logged-in
        # non-admin is denied; only with no session do we fall back to the
        # operator policy.
        real = await _resolve_real_user(request, creds)
        if real is not None:
            if not is_admin(real):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="admin role required"
                )
            return real
        if ControlConfig().require_admin:
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


__all__ = [
    "read_guard",
    "current_principal",
    "admin_principal",
    "is_admin",
    "system_visibility",
]
