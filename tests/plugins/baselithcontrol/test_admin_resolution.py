"""Admin resolution for the control plane is RBAC-aware, not enum-literal.

Regression: an admin provisioned via a *custom* RBAC role (granted the wildcard
``*`` permission) carries no built-in :data:`AuthRole.ADMIN` in ``user.roles``
— the unknown role string is dropped when the token is decoded. Such a user
passes every central RBAC gate yet, under a literal ``has_role(ADMIN)`` check,
was misread as an ordinary user in baselithcontrol and lost sight of disabled /
failed plugins. :func:`is_admin` must mirror the RBAC source of truth.
"""

from __future__ import annotations

from core.auth.types import AuthRole, AuthUser
from plugins.baselithcontrol.router._guards import is_admin


class _FakeRBAC:
    def __init__(self, perms: set[str]) -> None:
        self._perms = perms

    def effective_permissions(self, user_id: str, roles) -> set[str]:  # noqa: ANN001
        return set(self._perms)


def _patch_rbac(monkeypatch, service) -> None:
    monkeypatch.setattr(
        "plugins.auth.rbac.service.get_rbac_service", lambda: service
    )


def test_literal_admin_role_is_admin(monkeypatch) -> None:
    # Built-in admin short-circuits before RBAC is even consulted.
    def _boom():
        raise AssertionError("RBAC must not be consulted for a literal admin")

    monkeypatch.setattr("plugins.auth.rbac.service.get_rbac_service", _boom)
    user = AuthUser(user_id="u1", roles={AuthRole.ADMIN})
    assert is_admin(user) is True


def test_wildcard_custom_role_is_admin(monkeypatch) -> None:
    # No built-in admin role, but the effective permission set holds the wildcard.
    _patch_rbac(monkeypatch, _FakeRBAC({"*"}))
    user = AuthUser(user_id="u2", roles={AuthRole.USER})
    assert is_admin(user) is True


def test_plain_user_is_not_admin(monkeypatch) -> None:
    _patch_rbac(monkeypatch, _FakeRBAC({"plugins:read"}))
    user = AuthUser(user_id="u3", roles={AuthRole.USER})
    assert is_admin(user) is False


def test_rbac_unavailable_falls_back_to_role(monkeypatch) -> None:
    def _boom():
        raise RuntimeError("rbac down")

    monkeypatch.setattr("plugins.auth.rbac.service.get_rbac_service", _boom)
    # Non-admin with RBAC down → not elevated (fail closed for elevation).
    assert is_admin(AuthUser(user_id="u4", roles={AuthRole.USER})) is False
    # Literal admin still works without RBAC.
    assert is_admin(AuthUser(user_id="u5", roles={AuthRole.ADMIN})) is True
