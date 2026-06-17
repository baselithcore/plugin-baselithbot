"""Resilient RBAC guards for the BaselithTwin HTTP surface.

The twin acts on the owner's behalf — approving a queued reply *sends a WhatsApp
message as the owner*. Every control route must therefore be authenticated and
authorised, and the identity that decided must be captured for the audit trail
(never trusted from the request body).

These guards reuse the central ``auth`` plugin as the single source of truth for
identity/roles/permissions, but degrade gracefully — mirroring
``baselithcontrol``'s pattern — so a self-contained deployment (auth present but
not enforcing) stays usable without ever 503-ing on a half-initialised auth
subsystem:

* **reads** are open when auth is not enforced; when it is, the bearer/cookie is
  fully validated and the central per-tab policy applies;
* **mutations** (whitelist/facts/style/approval) require the matching twin
  permission slug (or admin) when auth is enforced; off-auth they honour a real
  logged-in session and otherwise fall back to the operator policy;
* **control** (pause/resume) always requires admin.

Permission slugs are granular and live in the central RBAC catalogue:
``twin.read``, ``twin.approve``, ``twin.manage``, ``twin.control``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth.types import AuthRole, AuthUser

if TYPE_CHECKING:
    from .config import TwinConfig

TAB_ID = "baselithtwin"
PERM_READ = "twin.read"
PERM_APPROVE = "twin.approve"
PERM_MANAGE = "twin.manage"
PERM_CONTROL = "twin.control"

_bearer = HTTPBearer(auto_error=False)


# -- Auth-subsystem probing (never raises) ---------------------------------


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

    Lets the twin honour a real session (your account) even when global
    ``auth_required`` is off, so audit actors are real identities. Never raises.
    """
    try:
        from core.auth import AuthManager
        from core.di.container import ServiceRegistry
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


def _has_permission(user: AuthUser, slug: str) -> bool:
    """Check a central RBAC permission slug for the user (admin wildcard passes)."""
    if user.has_role(AuthRole.ADMIN):
        return True
    try:
        from plugins.auth.rbac.permissions import has_permission
        from plugins.auth.rbac.service import get_rbac_service

        perms = get_rbac_service().effective_permissions(user.user_id, user.roles)
        return bool(has_permission(perms, slug))
    except Exception:  # noqa: BLE001 — no RBAC store ⇒ fall back to role check
        return user.has_role(AuthRole.USER)


def actor_label(user: AuthUser) -> str:
    """A stable, human-readable actor id for the audit trail."""
    return user.email or user.user_id or "unknown"


# -- Guards -----------------------------------------------------------------


def _forbidden(slug: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=f"requires permission '{slug}'"
    )


async def _read_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthUser:
    """Resolve the caller for a read; open off-auth, validated when enforced."""
    if not _auth_enforced():
        real = await _resolve_real_user(request, creds)
        return real or AuthUser(user_id="local", roles={AuthRole.USER})
    from plugins.auth.dependencies import get_current_user

    user = await get_current_user(request, creds)
    if not user.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def build_guards(config: "TwinConfig") -> Any:
    """Build config-bound RBAC dependencies for the router.

    Binding to the *plugin's* config (not a fresh env-only read) means the
    off-auth ``require_admin`` policy honours the ``plugins.yaml`` block.
    """
    require_admin = config.require_admin

    def _mutation(slug: str):
        async def _guard(
            request: Request,
            creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
        ) -> AuthUser:
            if not _auth_enforced():
                real = await _resolve_real_user(request, creds)
                if real is not None:
                    if not _has_permission(real, slug):
                        raise _forbidden(slug)
                    return real
                # No session: a local operator acts as admin only if the
                # deployment relaxed the admin requirement for the twin.
                if require_admin:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"requires '{slug}' (auth not configured)",
                    )
                return AuthUser(user_id="local", roles={AuthRole.ADMIN})

            user = await _read_principal(request, creds)
            if not _has_permission(user, slug):
                raise _forbidden(slug)
            return user

        return _guard

    return SimpleNamespace(
        read=_read_principal,
        approve=_mutation(PERM_APPROVE),
        manage=_mutation(PERM_MANAGE),
        control=_mutation(PERM_CONTROL),
    )


__all__ = [
    "TAB_ID",
    "PERM_READ",
    "PERM_APPROVE",
    "PERM_MANAGE",
    "PERM_CONTROL",
    "build_guards",
    "actor_label",
]
