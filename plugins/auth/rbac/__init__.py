"""Granular RBAC layer for the auth plugin.

Adds a permission catalog, custom roles, role/user grants and a central
per-plugin-tab access policy on top of the legacy ``AuthRole`` model. The
``AuthRole`` enum and ``require_roles`` keep working unchanged (system roles
are mirrored as RBAC roles), so existing consumer plugins are unaffected.
"""

from __future__ import annotations

from plugins.auth.rbac.permissions import (
    BUILTIN_PERMISSIONS,
    Permission,
    WILDCARD,
    has_permission,
    tab_permission,
)
from plugins.auth.rbac.service import RBACService, get_rbac_service
from plugins.auth.rbac.store import RBACStore, get_rbac_store

__all__ = [
    "Permission",
    "WILDCARD",
    "BUILTIN_PERMISSIONS",
    "has_permission",
    "tab_permission",
    "RBACService",
    "get_rbac_service",
    "RBACStore",
    "get_rbac_store",
]
