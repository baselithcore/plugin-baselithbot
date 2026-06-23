"""Privilege-escalation guards for the RBAC admin surface.

These close the one escalation hole in the flat (admin = wildcard) model: an
operator holding only ``rbac.manage`` could previously mint a custom role with
the wildcard and assign it to anyone — instantly manufacturing a platform
admin. The checks here require an actor to *already be* an effective admin to
hand out wildcard power, and gate every role→user assignment behind the
matching ``rbac.assign.*`` permission (NIST RBAC2 hierarchy, adapted).

All helpers are wildcard-aware via :func:`has_permission`, so a real admin
always passes; they only ever restrict non-admins. Keeping them here (instead
of inline in the route handlers) means the assign/grant endpoints stay small.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from core.auth import AuthUser
from plugins.auth.rbac.permissions import (
    WILDCARD,
    Permission,
    has_any,
    has_permission,
    required_assign_permission,
)
from plugins.auth.rbac.service import get_rbac_service, is_effective_admin


def _actor_permissions(actor: AuthUser) -> set[str]:
    return get_rbac_service().effective_permissions(actor.user_id, actor.roles)


def guard_wildcard_grant(actor: AuthUser, slugs: list[str]) -> None:
    """Refuse to grant the wildcard to a role unless the actor is an admin.

    Only an effective admin (literal admin role or a wildcard-bearing custom
    role) may confer ``*`` on any role. A plain ``rbac.manage`` operator is
    blocked — this is the core anti-escalation rule.
    """
    if WILDCARD not in slugs:
        return
    if not is_effective_admin(actor.user_id, actor.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an administrator may grant the '*' (full access) permission",
        )


def guard_role_assignment(actor: AuthUser, target_user_id: str, role: dict) -> None:
    """Enforce assign-permission gating + self-escalation guard for a role grant.

    The actor must hold the permission returned by
    :func:`required_assign_permission` for ``role`` (an ordinary role needs
    ``rbac.assign.role``; a wildcard/admin role needs ``rbac.assign.admin``).
    ``rbac.manage`` implicitly satisfies the ordinary-role requirement so
    existing operators keep working — but it never satisfies the admin-role
    requirement, which is what blocks escalation. A non-admin may never assign
    a wildcard/admin role to *themselves*.
    """
    required = required_assign_permission(role)
    perms = _actor_permissions(actor)
    if required == Permission.RBAC_ASSIGN_ADMIN:
        allowed = has_permission(perms, Permission.RBAC_ASSIGN_ADMIN)
        if target_user_id == actor.user_id and not is_effective_admin(
            actor.user_id, actor.roles
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot grant yourself an administrator role",
            )
    else:
        # rbac.manage holders could already assign ordinary roles — preserve it.
        allowed = has_any(perms, [Permission.RBAC_ASSIGN_ROLE, Permission.RBAC_MANAGE])
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires permission to assign this role: {required}",
        )


__all__ = ["guard_wildcard_grant", "guard_role_assignment"]
