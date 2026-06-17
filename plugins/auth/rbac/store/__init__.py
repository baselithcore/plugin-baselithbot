"""RBAC persistence store composed from cohesive mixins."""

from __future__ import annotations

from typing import Optional

from plugins.auth.rbac.store._access import AccessStoreMixin
from plugins.auth.rbac.store._groups import GroupStoreMixin
from plugins.auth.rbac.store._roles import RoleStoreMixin


class RBACStore(RoleStoreMixin, GroupStoreMixin, AccessStoreMixin):
    """PostgreSQL persistence for roles, permissions, groups, grants and tabs."""


_store: Optional[RBACStore] = None


def get_rbac_store() -> RBACStore:
    """Get or create the global RBAC store instance."""
    global _store
    if _store is None:
        _store = RBACStore()
    return _store


__all__ = ["RBACStore", "get_rbac_store"]
