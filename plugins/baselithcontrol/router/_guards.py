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
            if not real.has_role(AuthRole.ADMIN):
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
    if not user.has_role(AuthRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="admin role required"
        )
    return user


__all__ = ["read_guard", "current_principal", "admin_principal"]
