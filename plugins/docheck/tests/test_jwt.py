"""Local JWT issue/verify roundtrip + tampering rejection."""

import time

import pytest
from jose.exceptions import JWTError

from docheck.core.jwt import issue_token, verify_local_token


def test_issue_and_verify_roundtrip() -> None:
    tok = issue_token(
        user_id="u-1",
        email="a@b.local",
        roles=["admin"],
        tenant_id="acme",
        ttl=60,
    )
    claims = verify_local_token(tok)
    assert claims["sub"] == "u-1"
    assert claims["email"] == "a@b.local"
    assert claims["roles"] == ["admin"]
    assert claims["tid"] == "acme"


def test_expired_token_rejected() -> None:
    tok = issue_token(user_id="u-1", email="a@b.local", roles=[], ttl=-10)
    with pytest.raises(JWTError):
        verify_local_token(tok)


def test_tampered_token_rejected() -> None:
    tok = issue_token(user_id="u-1", email="a@b.local", roles=[], ttl=60)
    parts = tok.split(".")
    tampered = ".".join([parts[0], parts[1] + "X", parts[2]])
    with pytest.raises(JWTError):
        verify_local_token(tampered)


def test_wrong_audience_rejected() -> None:
    from jose import jwt

    from docheck.core.jwt import _private_pem

    bad = jwt.encode(
        {"sub": "u", "iss": "docheck-local", "aud": "other", "exp": int(time.time()) + 60},
        _private_pem(),
        algorithm="EdDSA",
    )
    with pytest.raises(JWTError):
        verify_local_token(bad)
