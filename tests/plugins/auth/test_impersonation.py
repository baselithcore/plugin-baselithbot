"""Unit tests for the admin impersonation primitives (pure logic, no DB)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Set

import pytest
from fastapi import HTTPException

from core.auth import AuthRole, AuthUser
from plugins.auth.config import AuthConfig
from plugins.auth.impersonation import (
    ACT_CLAIM,
    IMP_CLAIM,
    assert_target_impersonatable,
    build_actor_claim,
    extract_actor,
    is_impersonating,
)


@dataclass
class FakeUser:
    """Minimal stand-in for ``plugins.auth.models.User``."""

    id: str
    email: str = "user@example.com"
    is_active: bool = True
    roles: Set[AuthRole] = field(default_factory=lambda: {AuthRole.USER})
    locked: bool = False

    def is_locked(self) -> bool:
        return self.locked


def _admin(user_id: str = "admin-1", **meta) -> AuthUser:
    return AuthUser(user_id=user_id, roles={AuthRole.ADMIN}, metadata=meta)


def _config(**overrides) -> AuthConfig:
    # Fields carry env aliases (no populate_by_name), so override by attribute
    # after constructing from defaults rather than via constructor kwargs.
    cfg = AuthConfig()
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


# --- actor claim round-trip -------------------------------------------------


def test_build_actor_claim_includes_admin_and_reason():
    claim = build_actor_claim("admin-1", "admin@x.io", reason="support ticket 42")
    assert claim["sub"] == "admin-1"
    assert claim["email"] == "admin@x.io"
    assert claim["reason"] == "support ticket 42"
    assert isinstance(claim["ts"], int)


def test_build_actor_claim_truncates_long_reason():
    claim = build_actor_claim("admin-1", None, reason="x" * 500)
    assert len(claim["reason"]) == 280
    assert "email" not in claim


def test_extract_actor_requires_both_imp_and_act():
    actor = {"sub": "admin-1", "email": "a@x.io"}
    full = AuthUser(
        user_id="target", roles={AuthRole.USER}, metadata={IMP_CLAIM: True, ACT_CLAIM: actor}
    )
    assert extract_actor(full) == actor
    assert is_impersonating(full) is True

    # Marker without an actor object -> not impersonation.
    no_act = AuthUser(user_id="target", roles={AuthRole.USER}, metadata={IMP_CLAIM: True})
    assert extract_actor(no_act) is None

    # Actor without the imp marker -> not impersonation.
    no_marker = AuthUser(user_id="target", roles={AuthRole.USER}, metadata={ACT_CLAIM: actor})
    assert extract_actor(no_marker) is None
    assert is_impersonating(no_marker) is False


def test_extract_actor_rejects_actor_without_sub():
    bad = AuthUser(
        user_id="target",
        roles={AuthRole.USER},
        metadata={IMP_CLAIM: True, ACT_CLAIM: {"email": "a@x.io"}},
    )
    assert extract_actor(bad) is None


# --- eligibility ------------------------------------------------------------


def test_eligibility_allows_a_normal_active_user():
    assert_target_impersonatable(_admin(), FakeUser(id="u1"), _config())


def test_eligibility_blocks_when_feature_disabled():
    with pytest.raises(HTTPException) as exc:
        assert_target_impersonatable(
            _admin(), FakeUser(id="u1"), _config(impersonation_enabled=False)
        )
    assert exc.value.status_code == 403


def test_eligibility_blocks_self_impersonation():
    with pytest.raises(HTTPException) as exc:
        assert_target_impersonatable(_admin("u1"), FakeUser(id="u1"), _config())
    assert exc.value.status_code == 400


def test_eligibility_blocks_inactive_target():
    with pytest.raises(HTTPException) as exc:
        assert_target_impersonatable(_admin(), FakeUser(id="u1", is_active=False), _config())
    assert exc.value.status_code == 409


def test_eligibility_blocks_locked_target():
    with pytest.raises(HTTPException) as exc:
        assert_target_impersonatable(_admin(), FakeUser(id="u1", locked=True), _config())
    assert exc.value.status_code == 409


def test_eligibility_blocks_admin_target_by_default():
    target = FakeUser(id="u1", roles={AuthRole.ADMIN})
    with pytest.raises(HTTPException) as exc:
        assert_target_impersonatable(_admin(), target, _config())
    assert exc.value.status_code == 403


def test_eligibility_allows_admin_target_when_enabled():
    target = FakeUser(id="u1", roles={AuthRole.ADMIN})
    assert_target_impersonatable(_admin(), target, _config(allow_impersonate_admins=True))


def test_eligibility_blocks_nested_impersonation():
    nested_admin = _admin(**{IMP_CLAIM: True, ACT_CLAIM: {"sub": "root"}})
    with pytest.raises(HTTPException) as exc:
        assert_target_impersonatable(nested_admin, FakeUser(id="u1"), _config())
    assert exc.value.status_code == 409
