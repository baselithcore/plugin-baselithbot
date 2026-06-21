"""RBAC orchestration: seeding, tab discovery, and access queries."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set

from core.auth.types import AuthRole
from core.observability.logging import get_logger
from plugins.auth.rbac.discovery import discover_plugin_tabs, system_plugin_names
from plugins.auth.rbac.permissions import WILDCARD, has_permission, tab_permission
from plugins.auth.rbac.store import RBACStore, get_rbac_store

logger = get_logger(__name__)


def is_effective_admin(user_id: str, roles: Iterable[AuthRole]) -> bool:
    """Whether the identity has full (platform) admin power.

    Admin is an **effective** privilege, not a literal role (per the project
    conventions): a custom RBAC role granted the wildcard (``*``) is admin even
    when :class:`AuthRole.ADMIN` is absent. The literal role is checked first as
    a cheap, DB-free fast path; the wildcard lookup degrades **closed** (returns
    ``False``) if the RBAC store is unavailable, so a transient outage never
    silently elevates a non-admin.
    """
    roles = list(roles)
    if AuthRole.ADMIN in roles:
        return True
    try:
        perms = get_rbac_service().effective_permissions(user_id, roles)
        return has_permission(perms, WILDCARD)
    except Exception:  # noqa: BLE001 — degrade closed for elevation
        return False


class RBACService:
    """High-level facade over the RBAC store used by routers and guards."""

    def __init__(self, store: Optional[RBACStore] = None) -> None:
        self.store = store or get_rbac_store()
        self._discovered = False

    def bootstrap(self) -> None:
        """Seed built-in permissions/roles and register discovered tabs.

        Idempotent; safe to call on every startup. Never raises — a missing
        database must not crash plugin initialisation.
        """
        try:
            self.store.seed_builtin()
            self.refresh_tabs()
            logger.info("RBAC bootstrap complete")
        except Exception as exc:  # noqa: BLE001
            logger.error("RBAC bootstrap failed: %s", exc)

    def refresh_tabs(self, registry: Optional[object] = None) -> int:
        """Re-discover plugin tabs and register them. Returns tab count.

        ``_discovered`` only latches once tabs are actually found, so an early
        startup scan (before plugins/registry are ready) never permanently
        caches an empty result.
        """
        tabs = discover_plugin_tabs(registry)
        self.store.register_tabs(tabs)
        if tabs:
            self._discovered = True
        return len(tabs)

    def list_tabs(self, registry: Optional[object] = None) -> List[Dict]:
        """All tab policies, auto-discovering if none are registered yet.

        Plugin discovery at startup can run before the registry is ready; reads
        lazily re-scan (using the live registry when provided) so the matrix is
        never empty by accident.
        """
        self._ensure_discovered(registry)
        return self.store.list_tab_policies()

    def _ensure_discovered(self, registry: Optional[object] = None) -> None:
        if self._discovered:
            return
        try:
            existing = self.store.list_tab_policies()
            if existing:
                self._discovered = True
            else:
                self.refresh_tabs(registry)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Lazy tab discovery skipped: %s", exc)

    def effective_permissions(
        self, user_id: str, system_roles: Iterable[AuthRole]
    ) -> Set[str]:
        """Resolved permission slugs for a user."""
        return self.store.effective_permissions(user_id, system_roles)

    def accessible_tabs(
        self,
        user_id: str,
        system_roles: Iterable[AuthRole],
        registry: Optional[object] = None,
    ) -> List[Dict]:
        """Known tabs annotated with whether this user may access each.

        Unmanaged / unrestricted tabs are allowed for everyone (default-allow).
        """
        roles = list(system_roles)
        self._ensure_discovered(registry)
        perms = self.effective_permissions(user_id, roles)
        system = system_plugin_names()
        out: List[Dict] = []
        for policy in self.store.list_tab_policies():
            plugin = policy["plugin"]
            tab_id = policy["tab_id"]
            is_system = plugin in system
            # System plugins (auth, …) are admin-only by default: their tabs are
            # treated as restricted regardless of the stored policy, so they stay
            # hidden from the user-facing nav and only effective-admins (wildcard)
            # — or an explicit tab grant — may see them.
            restricted = bool(policy.get("restricted")) or is_system
            allowed = (not restricted) or has_permission(
                perms, tab_permission(plugin, tab_id)
            )
            out.append(
                {
                    "plugin": plugin,
                    "tab_id": tab_id,
                    "label": policy.get("label", tab_id),
                    "restricted": restricted,
                    "allowed": allowed,
                    "system": is_system,
                }
            )
        return out

    def can_access_tab(
        self,
        user_id: str,
        system_roles: Iterable[AuthRole],
        plugin: str,
        tab_id: str,
    ) -> bool:
        """Enforcement check for a single tab.

        System-plugin tabs (manifest ``system: true``) are admin-only
        regardless of the stored policy: access requires the tab permission
        (effective-admin / wildcard always passes). All other tabs follow the
        store's default-allow rule.
        """
        if plugin in system_plugin_names():
            perms = self.effective_permissions(user_id, system_roles)
            return has_permission(perms, tab_permission(plugin, tab_id))
        return self.store.can_access_tab(user_id, system_roles, plugin, tab_id)

    def plugin_allowed(
        self,
        user_id: str,
        system_roles: Iterable[AuthRole],
        plugin: str,
        registry: Optional[object] = None,
    ) -> bool:
        """Plugin-level gate used by the gateway middleware.

        A plugin is reachable unless it is known AND every one of its tabs is
        restricted-and-denied for this user (default-allow / fail-open for
        unknown plugins). Admins always pass (wildcard).
        """
        tabs = [
            t
            for t in self.accessible_tabs(user_id, system_roles, registry)
            if t["plugin"] == plugin
        ]
        if not tabs:
            return True
        return any(t.get("allowed") for t in tabs)


_service: Optional[RBACService] = None


def get_rbac_service() -> RBACService:
    """Get or create the global RBAC service instance."""
    global _service
    if _service is None:
        _service = RBACService()
    return _service


__all__ = ["RBACService", "get_rbac_service"]
