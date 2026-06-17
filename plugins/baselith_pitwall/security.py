"""Optional RBAC for the pit-wall routers.

Role-based access control is **opt-in** and decoupled from the auth plugin: the
pit wall carries no hard dependency on it. By default (``auth_enabled`` False)
every endpoint is open — identical to the prototype. Set the plugin config flag
``auth_enabled: true`` to gate endpoints via the shared guards from
:mod:`plugins.auth.dependencies` (``require_roles``). If the flag is on but the
auth plugin is absent, endpoints fall back to a warned no-op so the service still
runs rather than hard-failing.

Three privilege tiers map onto :class:`core.auth.AuthRole`:

    * ``VIEWER_ROLES`` — read-only surface (status/cars/stints/recs/stream/intel).
    * ``STRATEGIST_ROLES`` — mutating surface (session create/start, telemetry,
      radio, race-control, weather, rivals). Excludes GUEST.
    * ``APPROVER_ROLES`` — the HITL decision surface (accept / reject a
      recommendation). Restricted to ADMIN/SERVICE — deliberately narrower.

Tenant isolation is a separate, always-on concern handled in :mod:`.tenancy`.
"""

from __future__ import annotations

from typing import Any, Callable

from core.observability.logging import get_logger

logger = get_logger(__name__)

_AUTH_WARNING_EMITTED = False


def _noop_dependency() -> Callable[..., Any]:
    """Return a no-op FastAPI dependency used when the auth plugin is absent."""

    async def _allow() -> None:
        return None

    return _allow


_require_roles: Callable[..., Callable[..., Any]] | None
try:
    from core.auth import AuthRole as _AuthRole
    from plugins.auth.dependencies import require_roles as _require_roles_impl

    _require_roles = _require_roles_impl
    VIEWER_ROLES: tuple[Any, ...] = (
        _AuthRole.USER,
        _AuthRole.ADMIN,
        _AuthRole.SERVICE,
        _AuthRole.GUEST,
    )
    STRATEGIST_ROLES: tuple[Any, ...] = (
        _AuthRole.USER,
        _AuthRole.ADMIN,
        _AuthRole.SERVICE,
    )
    APPROVER_ROLES: tuple[Any, ...] = (
        _AuthRole.ADMIN,
        _AuthRole.SERVICE,
    )
    _AUTH_AVAILABLE = True
except Exception as exc:  # noqa: BLE001 — soft-fail when auth plugin absent
    logger.debug("pitwall auth gating disabled: %s", exc)
    _require_roles = None
    VIEWER_ROLES = ()
    STRATEGIST_ROLES = ()
    APPROVER_ROLES = ()
    _AUTH_AVAILABLE = False


def _gate(roles: tuple[Any, ...], enabled: bool) -> Callable[..., Any]:
    """Build a role dependency.

    Returns a no-op when RBAC is disabled (the default). When enabled but the
    auth plugin is missing, returns a warned no-op so the service keeps serving
    rather than 500-ing on a misconfiguration.
    """
    global _AUTH_WARNING_EMITTED
    if not enabled:
        return _noop_dependency()
    if not _AUTH_AVAILABLE or _require_roles is None:
        if not _AUTH_WARNING_EMITTED:
            logger.warning(
                "pitwall auth_enabled=true but the auth plugin is not available; "
                "endpoints remain UNGUARDED. Load `plugins.auth` to enable RBAC."
            )
            _AUTH_WARNING_EMITTED = True
        return _noop_dependency()
    return _require_roles(*roles)


def require_viewer(enabled: bool = False) -> Callable[..., Any]:
    """Dependency for read-only endpoints (RBAC applied only when enabled)."""
    return _gate(VIEWER_ROLES, enabled)


def require_strategist(enabled: bool = False) -> Callable[..., Any]:
    """Dependency for mutating endpoints (RBAC applied only when enabled)."""
    return _gate(STRATEGIST_ROLES, enabled)


def require_approver(enabled: bool = False) -> Callable[..., Any]:
    """Dependency for the HITL accept/reject surface (RBAC only when enabled)."""
    return _gate(APPROVER_ROLES, enabled)


__all__ = [
    "require_viewer",
    "require_strategist",
    "require_approver",
    "VIEWER_ROLES",
    "STRATEGIST_ROLES",
    "APPROVER_ROLES",
]
