"""Regression tests for the 2026 auth security-hardening pass.

Covers the Tier-0/Tier-1 fixes: SAML signature enforcement, group-membership
escalation gating, trusted-proxy IP resolution, SSO email-verified linking,
TOTP replay/throttle, WebAuthn challenge single-use, and API-key scope capping.
All DB-free (fakes / no pool) — pure logic.
"""

from __future__ import annotations

import types

import pyotp
import pytest
from fastapi import HTTPException

from core.auth import AuthRole, AuthUser
from plugins.auth.rbac.permissions import Permission


def _user(uid: str = "op") -> AuthUser:
    return AuthUser(user_id=uid, roles={AuthRole.USER})


class _FakeService:
    def __init__(self, effective: set[str]) -> None:
        self._effective = effective

    def effective_permissions(self, user_id, roles) -> set[str]:  # noqa: ANN001
        return set(self._effective)


# --------------------------------------------------------------------------- #
# C1 — SAML requires signed assertions
# --------------------------------------------------------------------------- #


def test_saml_settings_require_signed_assertions():
    from plugins.auth.sso._saml import build_settings

    settings = build_settings({"slug": "idp", "config": {}}, "https://app.example")
    sec = settings["security"]
    assert sec["wantAssertionsSigned"] is True  # the anti-bypass gate
    assert sec["wantMessagesSigned"] is True
    assert sec["rejectDeprecatedAlgorithm"] is True


def test_saml_message_signing_is_overridable_but_assertions_not():
    from plugins.auth.sso._saml import build_settings

    settings = build_settings(
        {"slug": "idp", "config": {"want_messages_signed": False}},
        "https://app.example",
    )
    assert settings["security"]["wantMessagesSigned"] is False
    assert settings["security"]["wantAssertionsSigned"] is True


# --------------------------------------------------------------------------- #
# C3 — group membership escalation gating
# --------------------------------------------------------------------------- #


class _FakeGroupStore:
    def __init__(self, role_slugs, role_map):
        self._role_slugs = role_slugs
        self._role_map = role_map

    def get_group(self, group_id):
        return {"id": group_id, "roles": self._role_slugs}

    def get_role_by_slug(self, slug):
        return self._role_map.get(slug)


def test_admin_bearing_group_blocks_non_admin_membership(monkeypatch):
    from plugins.auth.rbac_router import _escalation, _groups

    monkeypatch.setattr(_escalation, "is_effective_admin", lambda uid, roles: False)
    monkeypatch.setattr(
        _escalation,
        "get_rbac_service",
        lambda: _FakeService({Permission.GROUPS_MANAGE}),
    )
    store = _FakeGroupStore(
        ["admin"],
        {"admin": {"slug": "admin", "is_system": True, "permissions": []}},
    )
    with pytest.raises(HTTPException) as exc:
        _groups._guard_group_membership(store, _user(), "g1")
    assert exc.value.status_code == 403


def test_ordinary_group_membership_allowed(monkeypatch):
    from plugins.auth.rbac_router import _escalation, _groups

    monkeypatch.setattr(_escalation, "is_effective_admin", lambda uid, roles: False)
    monkeypatch.setattr(
        _escalation,
        "get_rbac_service",
        lambda: _FakeService({Permission.GROUPS_MANAGE}),
    )
    store = _FakeGroupStore(
        ["editor"],
        {
            "editor": {
                "slug": "editor",
                "is_system": False,
                "permissions": [Permission.USERS_READ],
            }
        },
    )
    _groups._guard_group_membership(store, _user(), "g1")  # no raise


# --------------------------------------------------------------------------- #
# H1 — trusted-proxy IP
# --------------------------------------------------------------------------- #


def _req(peer, headers):
    return types.SimpleNamespace(
        client=types.SimpleNamespace(host=peer), headers=headers
    )


def test_xff_ignored_from_untrusted_peer():
    from plugins.auth.client_ip import trusted_client_ip

    req = _req("10.0.0.5", {"x-forwarded-for": "1.2.3.4"})
    # No DI config in test -> trusted list empty -> the socket peer wins.
    assert trusted_client_ip(req) == "10.0.0.5"


def test_xff_honored_from_trusted_proxy(monkeypatch):
    from core.di.container import ServiceRegistry
    from plugins.auth.client_ip import trusted_client_ip

    monkeypatch.setattr(
        ServiceRegistry,
        "get",
        staticmethod(lambda cls: types.SimpleNamespace(trusted_proxies=["10.0.0.5"])),
    )
    req = _req("10.0.0.5", {"x-forwarded-for": "1.2.3.4, 9.9.9.9"})
    assert trusted_client_ip(req) == "1.2.3.4"


# --------------------------------------------------------------------------- #
# H3 — SSO email-verified linking
# --------------------------------------------------------------------------- #


class _FakeSsoPersist:
    def __init__(self, existing):
        self._existing = existing
        self.linked = False

    def get_sso_identity(self, pid, subject):
        return None

    def get_user_by_email(self, email):
        return self._existing

    def link_sso_identity(self, *a, **k):
        self.linked = True


def _existing_user():
    return types.SimpleNamespace(id="u1", is_active=True)


def test_sso_refuses_link_to_unverified_email():
    from plugins.auth.sso._provisioning import ProvisioningError, provision_sso_user

    persist = _FakeSsoPersist(_existing_user())
    with pytest.raises(ProvisioningError):
        provision_sso_user(
            persist,
            {"id": "pid", "slug": "idp", "config": {}},
            "sub",
            "victim@corp.com",
            None,
            allow_signup=True,
            email_verified=False,
        )
    assert persist.linked is False


def test_sso_links_when_email_verified():
    from plugins.auth.sso._provisioning import provision_sso_user

    persist = _FakeSsoPersist(_existing_user())
    user = provision_sso_user(
        persist,
        {"id": "pid", "slug": "idp", "config": {}},
        "sub",
        "user@corp.com",
        None,
        allow_signup=True,
        email_verified=True,
    )
    assert user.id == "u1" and persist.linked is True


def test_sso_links_when_provider_trusts_email():
    from plugins.auth.sso._provisioning import provision_sso_user

    persist = _FakeSsoPersist(_existing_user())
    user = provision_sso_user(
        persist,
        {"id": "pid", "slug": "idp", "config": {"trusted_email": True}},
        "sub",
        "user@corp.com",
        None,
        allow_signup=True,
        email_verified=False,
    )
    assert user.id == "u1" and persist.linked is True


def test_oidc_extract_identity_coerces_email_verified():
    from plugins.auth.sso._oidc import extract_identity

    assert extract_identity({"sub": "x", "email_verified": True})[3] is True
    assert extract_identity({"sub": "x", "email_verified": "true"})[3] is True
    assert extract_identity({"sub": "x"})[3] is False


# --------------------------------------------------------------------------- #
# H4 — TOTP replay detection + per-challenge throttle
# --------------------------------------------------------------------------- #


def test_totp_step_is_stable_for_replay_detection():
    secret = pyotp.random_base32()
    from plugins.auth.mfa import verify_totp_with_step

    code = pyotp.TOTP(secret).now()
    step = verify_totp_with_step(secret, code)
    assert step is not None
    # Same code resolves to the same step, so a caller recording the last
    # accepted step can reject a replay (step not strictly greater).
    assert verify_totp_with_step(secret, code) == step


def test_totp_wrong_code_returns_none():
    secret = pyotp.random_base32()
    from plugins.auth.mfa import verify_totp_with_step

    wrong = "000000" if pyotp.TOTP(secret).now() != "000000" else "111111"
    assert verify_totp_with_step(secret, wrong) is None


def test_mfa_challenge_burns_after_max_attempts():
    from plugins.auth.security import SecureTokenStore

    store = SecureTokenStore()
    store.store("tok", {"user_id": "u"}, ttl_seconds=300)
    assert store.register_failure("tok", max_attempts=3) is False
    assert store.register_failure("tok", max_attempts=3) is False
    assert store.register_failure("tok", max_attempts=3) is True
    assert store.get("tok") is None


def test_consume_totp_step_degrades_open_without_db(monkeypatch):
    from core.db import connection
    from plugins.auth.persistence._users import UserPersistenceMixin

    monkeypatch.setattr(connection, "_POOL", None, raising=False)
    assert UserPersistenceMixin().consume_totp_step("u", 123) is True


# --------------------------------------------------------------------------- #
# H6 — WebAuthn challenge single-use + TTL
# --------------------------------------------------------------------------- #


def test_webauthn_challenge_is_single_use():
    from plugins.auth.webauthn_challenges import WebAuthnChallengeStore

    store = WebAuthnChallengeStore()
    store.put("key", b"challenge-bytes")
    assert store.take("key") == b"challenge-bytes"
    assert store.take("key") is None  # popped on first take


def test_webauthn_challenge_expires():
    from plugins.auth.webauthn_challenges import WebAuthnChallengeStore

    store = WebAuthnChallengeStore(ttl_seconds=-1)  # already expired
    store.put("key", b"x")
    assert store.take("key") is None


# --------------------------------------------------------------------------- #
# H7 — API-key scope capping
# --------------------------------------------------------------------------- #


def test_api_key_without_admin_scope_drops_admin():
    from plugins.auth.api_key_auth import scoped_roles

    roles = {AuthRole.ADMIN, AuthRole.USER}
    assert scoped_roles(roles, []) == {AuthRole.USER}
    assert scoped_roles(roles, ["read", "write"]) == {AuthRole.USER}


def test_api_key_with_admin_scope_keeps_admin():
    from plugins.auth.api_key_auth import scoped_roles

    roles = {AuthRole.ADMIN, AuthRole.USER}
    assert scoped_roles(roles, ["admin"]) == roles
    assert scoped_roles(roles, ["*"]) == roles
