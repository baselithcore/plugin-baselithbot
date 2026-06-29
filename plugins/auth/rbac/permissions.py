"""RBAC permission catalog and system-role defaults.

Pure module (no DB/IO). Single source of truth for the built-in permission
slugs, the dynamic tab-permission naming scheme, and the default permission
grants for each system role. The wildcard slug ``*`` grants everything and is
honoured by the resolver as a short-circuit (admin behaviour preserved).

Conventions (use constants, never bare string literals)
-------------------------------------------------------
* Naming is ``resource.action`` (singular resource). Add a built-in permission
  in three coordinated steps so the catalog, the DB seed and the aggregate stay
  in sync:
    1. a constant on :class:`Permission`;
    2. a row in :data:`BUILTIN_PERMISSIONS` (``slug -> (description, category)``);
    3. (if it should be granted by default) the relevant entry in
       :data:`SYSTEM_ROLE_DEFAULTS`.
  :data:`ALL_PERMISSIONS` is derived from :data:`BUILTIN_PERMISSIONS`, so it
  needs no manual update.
* Membership checks go through :func:`has_permission` / :func:`has_any` /
  :func:`has_all` — all wildcard-aware — never raw ``in`` against the slug set.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Dict, FrozenSet, List, Set

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
    SESSIONS_READ = "sessions.read"
    # Group administration (additive alternative to RBAC_MANAGE on group routes).
    GROUPS_MANAGE = "groups.manage"
    # Role-assignment gating (NIST RBAC2 hierarchy). Granting a role to a user
    # requires the matching assign permission — this is what closes privilege
    # escalation: an ``rbac.manage`` operator can no longer mint/assign admin
    # power without being an effective admin themselves. ``RBAC_ASSIGN_ROLE``
    # covers ordinary roles; ``RBAC_ASSIGN_ADMIN`` is required for any role that
    # carries the wildcard (i.e. full platform admin).
    RBAC_ASSIGN_ROLE = "rbac.assign.role"
    RBAC_ASSIGN_ADMIN = "rbac.assign.admin"
    # Platform settings: override a plugin's manifest-declared tenancy mode at
    # runtime (shared vs. personal data scoping). Sensitive — changes data
    # visibility — so it is its own grantable permission (wildcard satisfies it).
    PLUGINS_TENANCY_MANAGE = "plugins.tenancy.manage"


#: Catalogue of built-in permissions -> human description + category. Seeded
#: into ``auth_permissions`` on init alongside the wildcard.
BUILTIN_PERMISSIONS: Dict[str, tuple[str, str]] = {
    WILDCARD: ("Full access to everything", "system"),
    Permission.USERS_MANAGE: ("Create, edit, and delete users", "users"),
    Permission.USERS_READ: ("View users", "users"),
    Permission.GROUPS_MANAGE: ("Create, edit, and delete groups", "groups"),
    Permission.RBAC_MANAGE: ("Manage roles, permissions and access policy", "rbac"),
    Permission.RBAC_READ: ("View roles and permissions", "rbac"),
    Permission.RBAC_ASSIGN_ROLE: ("Assign ordinary roles to users", "rbac"),
    Permission.RBAC_ASSIGN_ADMIN: ("Assign admin (wildcard) roles to users", "rbac"),
    Permission.AUDIT_READ: ("Read the audit log", "audit"),
    Permission.SESSIONS_READ: ("View active sessions", "sessions"),
    Permission.SESSIONS_MANAGE: ("View and revoke sessions", "sessions"),
    Permission.PLUGINS_TENANCY_MANAGE: (
        "Override per-plugin tenancy mode (data scoping)",
        "system",
    ),
}


#: Every concrete, grantable built-in permission slug (the wildcard is an
#: authority short-circuit, not a grantable permission, so it is excluded).
#: Derived from :data:`BUILTIN_PERMISSIONS` to stay in sync automatically — use
#: it to validate incoming slugs or to express a "grant everything explicit"
#: set without listing the wildcard.
ALL_PERMISSIONS: FrozenSet[str] = frozenset(
    slug for slug in BUILTIN_PERMISSIONS if slug != WILDCARD
)


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


#: Predefined, **non-privileged** role bundles offered as starting points when
#: an admin creates a custom role ("create from template"). None carries the
#: wildcard or ``rbac.manage`` — templates can never escalate. Adapted from the
#: wiki-gen role hierarchy to the platform-admin domain. Each entry is
#: ``slug -> (display name, description, permission bundle)``. Templates are NOT
#: seeded as roles (so a deleted one never resurrects); they only pre-fill the
#: create-role form.
ROLE_TEMPLATES: Dict[str, tuple[str, str, List[str]]] = {
    "operator": (
        "Operator",
        "Manage users and their sessions; no access-control changes.",
        [
            Permission.USERS_READ,
            Permission.USERS_MANAGE,
            Permission.SESSIONS_READ,
            Permission.SESSIONS_MANAGE,
        ],
    ),
    "user-manager": (
        "User Manager",
        "Create and edit users and groups.",
        [
            Permission.USERS_READ,
            Permission.USERS_MANAGE,
            Permission.GROUPS_MANAGE,
        ],
    ),
    "auditor": (
        "Auditor",
        "Read-only oversight: users, roles, audit log and sessions.",
        [
            Permission.USERS_READ,
            Permission.RBAC_READ,
            Permission.AUDIT_READ,
            Permission.SESSIONS_READ,
        ],
    ),
    "support": (
        "Support",
        "Help-desk: view users and revoke their sessions.",
        [
            Permission.USERS_READ,
            Permission.SESSIONS_READ,
            Permission.SESSIONS_MANAGE,
        ],
    ),
}


def required_assign_permission(role: dict) -> str:
    """Permission an actor must hold to assign/revoke ``role`` to a user.

    A role that grants the wildcard — or the built-in ``admin`` system role —
    confers full platform admin, so handing it out requires
    :attr:`Permission.RBAC_ASSIGN_ADMIN`. Every other role only needs
    :attr:`Permission.RBAC_ASSIGN_ROLE`. The wildcard short-circuit in
    :func:`has_permission` means an effective admin always satisfies both.
    """
    perms = set(role.get("permissions") or [])
    is_admin_role = bool(role.get("is_system")) and role.get("slug") == "admin"
    if WILDCARD in perms or is_admin_role:
        return Permission.RBAC_ASSIGN_ADMIN
    return Permission.RBAC_ASSIGN_ROLE


def tab_permission(plugin: str, tab_id: str) -> str:
    """Return the permission slug gating a given plugin tab."""
    return f"{TAB_PREFIX}{plugin}:{tab_id}"


def is_tab_permission(slug: str) -> bool:
    """True if ``slug`` is a dynamically-derived tab permission."""
    return slug.startswith(TAB_PREFIX)


def has_permission(effective: Set[str], required: str) -> bool:
    """Check a required slug against a resolved permission set (wildcard-aware)."""
    return WILDCARD in effective or required in effective


def has_any(effective: Set[str], required: Iterable[str]) -> bool:
    """True if the holder satisfies AT LEAST ONE required slug (wildcard-aware).

    Empty ``required`` ⇒ ``False`` (nothing to satisfy). Mirrors the ``any``
    semantics of :func:`plugins.auth.dependencies.require_permission`.
    """
    required = list(required)
    if not required:
        return False
    return WILDCARD in effective or any(slug in effective for slug in required)


def has_all(effective: Set[str], required: Iterable[str]) -> bool:
    """True if the holder satisfies EVERY required slug (wildcard-aware).

    Empty ``required`` ⇒ ``True`` (vacuously satisfied), matching ``all([])``.
    """
    if WILDCARD in effective:
        return True
    return all(slug in effective for slug in required)


def system_role_slugs() -> List[str]:
    """Slugs of all system roles (matching AuthRole values)."""
    return [role.value for role in SYSTEM_ROLE_DEFAULTS]


__all__ = [
    "WILDCARD",
    "TAB_PREFIX",
    "Permission",
    "BUILTIN_PERMISSIONS",
    "ALL_PERMISSIONS",
    "SYSTEM_ROLE_DEFAULTS",
    "ROLE_TEMPLATES",
    "required_assign_permission",
    "tab_permission",
    "is_tab_permission",
    "has_permission",
    "has_any",
    "has_all",
    "system_role_slugs",
]
