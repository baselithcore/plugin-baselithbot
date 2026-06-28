"""Admin exemption for cost governance.

Admins have **no spend limit** — never metered against a cap, never blocked.
"Admin" is an *effective* privilege (per the platform convention), not a literal
role: a user provisioned via a custom RBAC role granted the wildcard (``*``)
permission counts too, even without the built-in ``AuthRole.ADMIN``. We mirror
the central gates — effective permission set + wildcard — and fall back to the
literal role when the RBAC service is unavailable (degrades cost-safe: built-in
admins stay unlimited; only an offline RBAC layer could momentarily cap a
wildcard-only admin).
"""

from __future__ import annotations

from core.observability.logging import get_logger

logger = get_logger(__name__)


def is_unlimited_user(user_id: str) -> bool:
    """True when the user is an (effective) admin and therefore uncapped."""
    if not user_id:
        return False
    try:
        from core.auth.types import AuthRole
        from plugins.auth.persistence import get_auth_persistence

        user = get_auth_persistence().get_user_by_id(user_id)
        roles = set(getattr(user, "roles", None) or [])
    except Exception:  # noqa: BLE001 — no user / DB down → treat as limited
        return False

    # Literal built-in admin.
    if AuthRole.ADMIN in roles or "admin" in {
        str(getattr(r, "value", r)) for r in roles
    }:
        return True

    # Effective admin via the RBAC wildcard, mirroring the central gates.
    try:
        from plugins.auth.rbac.permissions import WILDCARD, has_permission
        from plugins.auth.rbac.service import get_rbac_service

        perms = get_rbac_service().effective_permissions(user_id, roles)
        return bool(has_permission(perms, WILDCARD))
    except Exception:  # noqa: BLE001 — RBAC offline → fall back to the role check
        return False


__all__ = ["is_unlimited_user"]
