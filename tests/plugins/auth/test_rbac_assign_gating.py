"""Privilege-escalation gating for the RBAC admin surface.

Covers the wiki-gen-inspired hardening: an ``rbac.manage`` operator can no
longer mint or hand out wildcard (admin) power, role assignment is gated behind
the matching ``rbac.assign.*`` permission, and the predefined role templates
are non-privileged. Pure unit tests — the RBAC service is faked so no DB is
required.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from core.auth import AuthRole, AuthUser
from plugins.auth.rbac import permissions as perms_mod
from plugins.auth.rbac.permissions import (
    ROLE_TEMPLATES,
    WILDCARD,
    Permission,
    required_assign_permission,
)
from plugins.auth.rbac_router import _escalation


# --------------------------------------------------------------------------- #
# Fakes / fixtures
# --------------------------------------------------------------------------- #


class _FakeService:
    def __init__(self, effective: set[str]) -> None:
        self._effective = effective

    def effective_permissions(self, user_id: str, roles) -> set[str]:  # noqa: ANN001
        return set(self._effective)


@pytest.fixture
def patch_rbac(monkeypatch):
    """Patch the escalation module's RBAC hooks with controlled values."""

    def _apply(*, effective: set[str], is_admin: bool) -> None:
        monkeypatch.setattr(
            _escalation, "get_rbac_service", lambda: _FakeService(effective)
        )
        monkeypatch.setattr(
            _escalation, "is_effective_admin", lambda uid, roles: is_admin
        )

    return _apply


def _user(uid: str = "op") -> AuthUser:
    return AuthUser(user_id=uid, roles={AuthRole.USER})


def _role(slug: str, perms: list[str], *, is_system: bool = False) -> dict:
    return {"id": slug, "slug": slug, "is_system": is_system, "permissions": perms}


# --------------------------------------------------------------------------- #
# required_assign_permission
# --------------------------------------------------------------------------- #


def test_ordinary_role_needs_assign_role():
    role = _role("editor", [Permission.USERS_READ])
    assert required_assign_permission(role) == Permission.RBAC_ASSIGN_ROLE


def test_wildcard_role_needs_assign_admin():
    role = _role("superops", [WILDCARD])
    assert required_assign_permission(role) == Permission.RBAC_ASSIGN_ADMIN


def test_admin_system_role_needs_assign_admin():
    role = _role("admin", [], is_system=True)
    assert required_assign_permission(role) == Permission.RBAC_ASSIGN_ADMIN


# --------------------------------------------------------------------------- #
# guard_wildcard_grant
# --------------------------------------------------------------------------- #


def test_non_admin_cannot_grant_wildcard(patch_rbac):
    patch_rbac(effective={Permission.RBAC_MANAGE}, is_admin=False)
    with pytest.raises(HTTPException) as exc:
        _escalation.guard_wildcard_grant(_user(), [WILDCARD, Permission.USERS_READ])
    assert exc.value.status_code == 403


def test_admin_can_grant_wildcard(patch_rbac):
    patch_rbac(effective={WILDCARD}, is_admin=True)
    # Should not raise.
    _escalation.guard_wildcard_grant(_user(), [WILDCARD])


def test_grant_without_wildcard_is_unrestricted(patch_rbac):
    patch_rbac(effective={Permission.RBAC_MANAGE}, is_admin=False)
    # No wildcard in the set -> no escalation check at all.
    _escalation.guard_wildcard_grant(_user(), [Permission.USERS_READ])


# --------------------------------------------------------------------------- #
# guard_role_assignment
# --------------------------------------------------------------------------- #


def test_rbac_manage_can_assign_ordinary_role(patch_rbac):
    patch_rbac(effective={Permission.RBAC_MANAGE}, is_admin=False)
    role = _role("editor", [Permission.USERS_READ])
    # rbac.manage implicitly satisfies rbac.assign.role -> no raise.
    _escalation.guard_role_assignment(_user(), "target", role)


def test_rbac_manage_cannot_assign_wildcard_role(patch_rbac):
    patch_rbac(effective={Permission.RBAC_MANAGE}, is_admin=False)
    role = _role("superops", [WILDCARD])
    with pytest.raises(HTTPException) as exc:
        _escalation.guard_role_assignment(_user(), "target", role)
    assert exc.value.status_code == 403


def test_assign_admin_perm_allows_wildcard_role(patch_rbac):
    patch_rbac(effective={Permission.RBAC_ASSIGN_ADMIN}, is_admin=False)
    role = _role("superops", [WILDCARD])
    _escalation.guard_role_assignment(_user(), "target", role)


def test_cannot_self_assign_admin_role(patch_rbac):
    patch_rbac(effective={Permission.RBAC_ASSIGN_ADMIN}, is_admin=False)
    role = _role("admin", [], is_system=True)
    with pytest.raises(HTTPException) as exc:
        _escalation.guard_role_assignment(_user("self"), "self", role)
    assert exc.value.status_code == 403


def test_operator_without_any_assign_perm_is_blocked(patch_rbac):
    patch_rbac(effective={Permission.USERS_READ}, is_admin=False)
    role = _role("editor", [Permission.USERS_READ])
    with pytest.raises(HTTPException) as exc:
        _escalation.guard_role_assignment(_user(), "target", role)
    assert exc.value.status_code == 403


# --------------------------------------------------------------------------- #
# Role templates are non-privileged
# --------------------------------------------------------------------------- #


def test_role_templates_never_privileged():
    assert ROLE_TEMPLATES, "expected at least one starter template"
    for slug, (name, desc, bundle) in ROLE_TEMPLATES.items():
        assert name and desc
        assert WILDCARD not in bundle, f"{slug} leaks wildcard"
        assert Permission.RBAC_MANAGE not in bundle, f"{slug} leaks rbac.manage"
        assert Permission.RBAC_ASSIGN_ADMIN not in bundle, f"{slug} leaks assign.admin"
        # Every template permission is a real catalog slug.
        for slug_perm in bundle:
            assert slug_perm in perms_mod.BUILTIN_PERMISSIONS


def test_new_permissions_in_catalog_and_aggregate():
    new = [
        Permission.SESSIONS_READ,
        Permission.GROUPS_MANAGE,
        Permission.RBAC_ASSIGN_ROLE,
        Permission.RBAC_ASSIGN_ADMIN,
    ]
    for slug in new:
        assert slug in perms_mod.BUILTIN_PERMISSIONS
        assert slug in perms_mod.ALL_PERMISSIONS
    # Wildcard is never an ordinary grantable permission.
    assert WILDCARD not in perms_mod.ALL_PERMISSIONS
