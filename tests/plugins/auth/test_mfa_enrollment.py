"""Unit tests for forced-MFA enrollment challenge building (no DB).

Exercises ``build_mfa_enrollment_challenge``: it must mint a pending TOTP secret
+ backup codes, stash them under the returned ``enroll_token`` (never touching
the database), and the stashed secret must verify the code the user will type.
"""

from __future__ import annotations

import pyotp

from core.di.container import ServiceRegistry
from plugins.auth.config import AuthConfig
from plugins.auth.models import User
from plugins.auth.router._mfa_enroll_routes import build_mfa_enrollment_challenge
from plugins.auth.security import mfa_token_store


def _user() -> User:
    return User(id="u-1", email="user@example.com", password_hash="x")


def test_enrollment_challenge_is_self_consistent():
    ServiceRegistry.register(AuthConfig, AuthConfig())  # provisioning_uri reads issuer
    challenge = build_mfa_enrollment_challenge(_user())

    assert challenge.mfa_enrollment_required is True
    assert challenge.enroll_token
    assert challenge.secret
    assert len(challenge.backup_codes) == 10
    assert challenge.provisioning_uri.startswith("otpauth://")

    # The pending secret is stashed under the enroll_token, not persisted.
    stored = mfa_token_store.get(challenge.enroll_token)
    assert stored is not None
    assert stored["user_id"] == "u-1"
    assert stored["secret"] == challenge.secret
    assert len(stored["backup_hashes"]) == 10

    # The stashed secret verifies a freshly-generated TOTP code (the user flow).
    code = pyotp.TOTP(challenge.secret).now()
    assert pyotp.TOTP(stored["secret"]).verify(code)

    mfa_token_store.delete(challenge.enroll_token)


def test_each_challenge_has_a_unique_token():
    ServiceRegistry.register(AuthConfig, AuthConfig())
    a = build_mfa_enrollment_challenge(_user())
    b = build_mfa_enrollment_challenge(_user())
    assert a.enroll_token != b.enroll_token
    assert a.secret != b.secret
    mfa_token_store.delete(a.enroll_token)
    mfa_token_store.delete(b.enroll_token)
