"""Auth integration helpers for the BaselithMed router.

The plugin gates clinical endpoints behind RBAC. Two roles map to two
clinical personas:

    * ``CLINICAL_USER_ROLES`` — patient-facing and read-only flows (session
      creation, interview turn, triage finalize). Any authenticated user can
      drive an anamnesis.
    * ``CLINICAL_VALIDATOR_ROLES`` — clinician-only validation surface
      (``POST /triage/{id}/validate``). Restricted to ADMIN/SERVICE because
      :mod:`core.auth.types.AuthRole` does not yet define a dedicated
      ``CLINICIAN`` role; rolling our own here would split the enum.

The ``require_roles`` factory lives in the :mod:`plugins.auth` plugin. When
that plugin is not loaded (typical dev setup), we fall back to a no-op
dependency that emits a single warning per process so tests keep running
without changing security posture in production deployments where the auth
plugin is mandatory.
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
    CLINICAL_USER_ROLES: tuple[Any, ...] = (
        _AuthRole.USER,
        _AuthRole.ADMIN,
        _AuthRole.SERVICE,
    )
    CLINICAL_VALIDATOR_ROLES: tuple[Any, ...] = (
        _AuthRole.ADMIN,
        _AuthRole.SERVICE,
    )
    _AUTH_AVAILABLE = True
except Exception as exc:  # noqa: BLE001 — soft-fail when auth plugin absent
    logger.debug("BaselithMed auth gating disabled: %s", exc)
    _require_roles = None
    CLINICAL_USER_ROLES = ()
    CLINICAL_VALIDATOR_ROLES = ()
    _AUTH_AVAILABLE = False


def require_clinical_user() -> Callable[..., Any]:
    """Dependency permitting any authenticated user to drive the anamnesis."""
    global _AUTH_WARNING_EMITTED
    if not _AUTH_AVAILABLE or _require_roles is None:
        if not _AUTH_WARNING_EMITTED:
            logger.warning(
                "BaselithMed clinical endpoints are UNGUARDED: auth plugin "
                "not available. Load `plugins.auth` to enable RBAC."
            )
            _AUTH_WARNING_EMITTED = True
        return _noop_dependency()
    return _require_roles(*CLINICAL_USER_ROLES)


def require_clinical_validator() -> Callable[..., Any]:
    """Dependency restricting validation to clinician/service callers."""
    global _AUTH_WARNING_EMITTED
    if not _AUTH_AVAILABLE or _require_roles is None:
        if not _AUTH_WARNING_EMITTED:
            logger.warning(
                "BaselithMed /validate endpoint is UNGUARDED: auth plugin "
                "not available. Load `plugins.auth` to enable RBAC."
            )
            _AUTH_WARNING_EMITTED = True
        return _noop_dependency()
    return _require_roles(*CLINICAL_VALIDATOR_ROLES)
