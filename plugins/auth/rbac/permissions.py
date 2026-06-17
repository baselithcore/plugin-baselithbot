"""RBAC permission catalog and system-role defaults.

Pure module (no DB/IO). Single source of truth for the built-in permission
slugs, the dynamic tab-permission naming scheme, and the default permission
grants for each system role. The wildcard slug ``*`` grants everything and is
honoured by the resolver as a short-circuit (admin behaviour preserved).
"""

from __future__ import annotations

from typing import Dict, List, Set

from core.auth.types import AuthRole

#: Wildcard permission — holder may do anything. Granted to the admin role.
WILDCARD = "*"

#: Prefix for dynamically-derived per-plugin-tab permissions.
TAB_PREFIX = "tab:"


class Permission:
    """Built-in (non-tab) permission slugs, ``resource.action`` form."""

    # User & account administration (drives existing /admin/users endpoints).
    USERS_MANAGE = "users.manage"
    USERS_READ = "users.read"
    # RBAC administration: roles, permissions, assignments, tab policy.
    RBAC_MANAGE = "rbac.manage"
    RBAC_READ = "rbac.read"
    # Audit log access.
    AUDIT_READ = "audit.read"
    # Session administration.
    SESSIONS_MANAGE = "sessions.manage"


#: Catalogue of built-in permissions -> human description + category. Seeded
#: into ``auth_permissions`` on init alongside the wildcard.
BUILTIN_PERMISSIONS: Dict[str, tuple[str, str]] = {
    WILDCARD: ("Full access to everything", "system"),
    Permission.USERS_MANAGE: ("Create, edit, and delete users", "users"),
    Permission.USERS_READ: ("View users", "users"),
    Permission.RBAC_MANAGE: ("Manage roles, permissions and access policy", "rbac"),
    Permission.RBAC_READ: ("View roles and permissions", "rbac"),
    Permission.AUDIT_READ: ("Read the audit log", "audit"),
    Permission.SESSIONS_MANAGE: ("View and revoke sessions", "sessions"),
}


#: Business-facing system roles managed in the admin console. Admin gets the
#: wildcard; user/guest start with no explicit grants and rely on default-allow
#: tab policy until an admin restricts a tab. The remaining AuthRole values
#: (anonymous/service/job) are auth plumbing — never surfaced as manageable
#: roles and pruned from the catalog on seed.
SYSTEM_ROLE_DEFAULTS: Dict[AuthRole, Set[str]] = {
    AuthRole.ADMIN: {WILDCARD},
    AuthRole.USER: set(),
    AuthRole.GUEST: set(),
}

#: Internal plumbing roles: kept out of the RBAC management surface and removed
#: from auth_roles so the Roles screen only lists business roles + custom ones.
PLUMBING_ROLE_SLUGS: Set[str] = {
    AuthRole.ANONYMOUS.value,
    AuthRole.SERVICE.value,
    AuthRole.JOB.value,
}


def tab_permission(plugin: str, tab_id: str) -> str:
    """Return the permission slug gating a given plugin tab."""
    return f"{TAB_PREFIX}{plugin}:{tab_id}"


def is_tab_permission(slug: str) -> bool:
    """True if ``slug`` is a dynamically-derived tab permission."""
    return slug.startswith(TAB_PREFIX)


def has_permission(effective: Set[str], required: str) -> bool:
    """Check a required slug against a resolved permission set (wildcard-aware)."""
    return WILDCARD in effective or required in effective


def system_role_slugs() -> List[str]:
    """Slugs of all system roles (matching AuthRole values)."""
    return [role.value for role in SYSTEM_ROLE_DEFAULTS]


__all__ = [
    "WILDCARD",
    "TAB_PREFIX",
    "Permission",
    "BUILTIN_PERMISSIONS",
    "SYSTEM_ROLE_DEFAULTS",
    "tab_permission",
    "is_tab_permission",
    "has_permission",
    "system_role_slugs",
]
