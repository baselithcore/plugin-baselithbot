"""System plugins (manifest ``system: true``) are admin-only & hidden from the
user-facing nav. Verifies the RBAC service flips their tabs from default-allow
to default-deny for non-admins while effective-admins (wildcard) still see them.
"""

from __future__ import annotations

from typing import Dict, List, Set

from core.auth import AuthRole
from plugins.auth.rbac.discovery import system_plugin_names
from plugins.auth.rbac.permissions import WILDCARD
from plugins.auth.rbac.service import RBACService


class _FakeStore:
    """In-memory stand-in for RBACStore (no DB)."""

    def __init__(self, policies: List[Dict], perms: Dict[str, Set[str]]):
        self._policies = policies
        self._perms = perms

    def list_tab_policies(self) -> List[Dict]:
        return self._policies

    def effective_permissions(self, user_id: str, roles) -> Set[str]:
        return self._perms.get(user_id, set())

    def can_access_tab(self, user_id, roles, plugin, tab_id) -> bool:
        # Non-system fallback: default-allow.
        return True


def _service() -> RBACService:
    policies = [
        {
            "plugin": "auth",
            "tab_id": "admin-users",
            "restricted": False,
            "label": "Users",
        },
        # A genuine feature plugin (not in system_plugin_names) — stays
        # default-allow. Uses a synthetic name so it is unaffected by which real
        # plugins are tagged ``system: true``.
        {"plugin": "feature_demo", "tab_id": "home", "restricted": False},
    ]
    perms = {"admin-1": {WILDCARD}, "user-1": set()}
    return RBACService(store=_FakeStore(policies, perms))


def test_auth_is_a_system_plugin():
    assert "auth" in system_plugin_names()


def test_non_admin_cannot_see_auth_tab():
    svc = _service()
    tabs = {t["tab_id"]: t for t in svc.accessible_tabs("user-1", {AuthRole.USER})}
    auth_tab = tabs["admin-users"]
    assert auth_tab["system"] is True
    assert auth_tab["restricted"] is True  # forced by system flag
    assert auth_tab["allowed"] is False  # hidden from a normal user's nav


def test_admin_can_see_auth_tab():
    svc = _service()
    tabs = {t["tab_id"]: t for t in svc.accessible_tabs("admin-1", {AuthRole.ADMIN})}
    assert tabs["admin-users"]["allowed"] is True  # wildcard holder sees it


def test_non_system_plugin_stays_default_allow_for_users():
    svc = _service()
    tabs = {t["tab_id"]: t for t in svc.accessible_tabs("user-1", {AuthRole.USER})}
    home = tabs["home"]
    assert home["system"] is False
    assert home["allowed"] is True  # ordinary plugins remain visible


def test_plugin_allowed_hides_auth_from_non_admin():
    svc = _service()
    assert svc.plugin_allowed("user-1", {AuthRole.USER}, "auth") is False
    assert svc.plugin_allowed("admin-1", {AuthRole.ADMIN}, "auth") is True


def test_can_access_tab_enforces_system_for_single_tab():
    svc = _service()
    assert svc.can_access_tab("user-1", {AuthRole.USER}, "auth", "admin-users") is False
    assert (
        svc.can_access_tab("admin-1", {AuthRole.ADMIN}, "auth", "admin-users") is True
    )
    # Non-system plugin still delegates to the store's default-allow.
    assert svc.can_access_tab("user-1", {AuthRole.USER}, "feature_demo", "home") is True
