"""Unit tests for the RBAC permission catalog helpers (pure, no DB).

Covers the additive organization layer: the ``ALL_PERMISSIONS`` aggregate and
the wildcard-aware ``has_any`` / ``has_all`` helpers that
``require_permission`` now delegates to.
"""

from __future__ import annotations

from plugins.auth.rbac.permissions import (
    ALL_PERMISSIONS,
    BUILTIN_PERMISSIONS,
    WILDCARD,
    Permission,
    has_all,
    has_any,
    has_permission,
)


def test_all_permissions_is_builtins_minus_wildcard() -> None:
    assert WILDCARD not in ALL_PERMISSIONS
    assert ALL_PERMISSIONS == {s for s in BUILTIN_PERMISSIONS if s != WILDCARD}
    assert Permission.USERS_MANAGE in ALL_PERMISSIONS


def test_has_permission_wildcard_short_circuit() -> None:
    assert has_permission({WILDCARD}, Permission.AUDIT_READ)
    assert not has_permission({Permission.USERS_READ}, Permission.AUDIT_READ)


def test_has_any_semantics() -> None:
    perms = {Permission.USERS_READ}
    assert has_any(perms, [Permission.USERS_READ, Permission.RBAC_MANAGE])
    assert not has_any(perms, [Permission.RBAC_MANAGE, Permission.AUDIT_READ])
    # Wildcard satisfies any non-empty requirement.
    assert has_any({WILDCARD}, [Permission.AUDIT_READ])
    # Empty requirement → False (nothing to satisfy), matching prior behaviour.
    assert not has_any(perms, [])
    assert not has_any({WILDCARD}, [])


def test_has_all_semantics() -> None:
    perms = {Permission.USERS_READ, Permission.USERS_MANAGE}
    assert has_all(perms, [Permission.USERS_READ, Permission.USERS_MANAGE])
    assert not has_all(perms, [Permission.USERS_READ, Permission.AUDIT_READ])
    # Wildcard satisfies every requirement.
    assert has_all({WILDCARD}, [Permission.AUDIT_READ, Permission.RBAC_MANAGE])
    # Empty requirement → True (vacuous), matching ``all([])``.
    assert has_all(perms, [])


def test_helpers_match_legacy_any_all_logic() -> None:
    """has_any/has_all must equal the list-comprehension logic they replaced."""
    perms = {Permission.RBAC_READ}
    for slugs in ([], [Permission.RBAC_READ], [Permission.RBAC_READ, Permission.AUDIT_READ]):
        checks = [has_permission(perms, s) for s in slugs]
        assert has_any(perms, slugs) == (any(checks))
        assert has_all(perms, slugs) == (all(checks))
