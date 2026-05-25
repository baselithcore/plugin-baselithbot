"""Smoke test minimo per primitive auth (no DB required).

Copre:

- ``hash_password`` produce hash PBKDF2-SHA256 nel formato canonico.
- ``verify_password`` round-trip + costante-time mismatch.
- JWT access token issue → decode → claim integri.
- JWT scaduto rifiutato.
- Replay detection mock-friendly: il modulo `tokens.rotate_refresh_token`
  richiede DB live → skippato qui (covered da integration tests).

Tests che richiedono Postgres (CRUD users/tenants/conversations,
TenantMiddleware DB verify) → file separato `test_auth_db.py` (TODO,
quando si setta postgres in CI).
"""

from __future__ import annotations

import datetime
import time

import pytest

# --- password hashing -------------------------------------------------------


def test_hash_password_format() -> None:
    from llm_wiki.db.users import hash_password

    h = hash_password("test-password-12chars")
    parts = h.split("$")
    assert len(parts) == 4
    assert parts[0] == "pbkdf2_sha256"
    assert int(parts[1]) >= 200_000  # iterations OWASP-aligned
    assert len(parts[2]) == 32  # salt 16 byte → 32 hex
    assert len(parts[3]) == 64  # SHA-256 → 64 hex


def test_verify_password_roundtrip() -> None:
    from llm_wiki.db.users import hash_password, verify_password

    h = hash_password("S3cur3P4ssw0rd!")
    assert verify_password(h, "S3cur3P4ssw0rd!")
    assert not verify_password(h, "wrong")
    # Hash modificato → mismatch
    tampered = h[:-1] + ("a" if h[-1] != "a" else "b")
    assert not verify_password(tampered, "S3cur3P4ssw0rd!")


def test_verify_password_malformed_hash() -> None:
    from llm_wiki.db.users import verify_password

    assert not verify_password("garbage", "anything")
    assert not verify_password("", "")
    assert not verify_password("scheme$only", "x")


# --- JWT roundtrip ---------------------------------------------------------


@pytest.fixture
def secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """SECRET_KEY override + reload config + tokens module per pickup."""
    import importlib

    monkeypatch.setenv("SECRET_KEY", "test-secret-key-min-32-bytes-long-yes")
    monkeypatch.setenv("ACCESS_TOKEN_TTL_MINUTES", "60")

    import llm_wiki.config as cfg

    importlib.reload(cfg)
    return cfg.SECRET_KEY  # type: ignore[return-value]


def test_jwt_issue_and_decode(secret: str) -> None:
    from llm_wiki.auth.tokens import decode_access_token, issue_access_token

    assert secret  # fixture ha settato la env
    token, exp = issue_access_token(user_id="u-1", tenant_id="t-1", role="admin")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "u-1"
    assert payload["uid"] == "u-1"
    assert payload["tenant_id"] == "t-1"
    assert payload["role"] == "admin"
    assert payload["typ"] == "access"
    # exp coerente con TTL_MINUTES=60
    delta = exp - datetime.datetime.now(datetime.timezone.utc)
    assert 55 * 60 <= delta.total_seconds() <= 65 * 60


def test_jwt_decode_invalid_signature_returns_none(secret: str) -> None:
    # Token firmato con secret diverso
    import jwt as pyjwt

    from llm_wiki.auth.tokens import decode_access_token

    bad = pyjwt.encode(
        {"sub": "x", "exp": int(time.time()) + 60}, "other-secret", algorithm="HS256"
    )
    assert decode_access_token(bad) is None


def test_jwt_decode_expired_returns_none(secret: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Access token con exp nel passato → None."""
    import jwt as pyjwt

    from llm_wiki.auth.tokens import decode_access_token

    expired = pyjwt.encode(
        {
            "sub": "u-1",
            "tenant_id": "t-1",
            "role": "user",
            "typ": "access",
            "exp": int(time.time()) - 10,
        },
        secret,
        algorithm="HS256",
    )
    assert decode_access_token(expired) is None


def test_jwt_no_secret_raises() -> None:
    """Issuance senza SECRET_KEY → RuntimeError chiaro (non firma con default)."""
    import importlib

    import llm_wiki.config as cfg

    # Drop secret e reload module fields.
    cfg.SECRET_KEY = None  # type: ignore[assignment]
    importlib.reload(__import__("llm_wiki.auth.tokens", fromlist=["_"]))
    from llm_wiki.auth.tokens import issue_access_token

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        issue_access_token(user_id="x", tenant_id="y", role="user")


# --- tenant context contextvar --------------------------------------------


def test_tenant_contextvar_isolated() -> None:
    """get/set/reset round-trip — coda di chiamate non leak fra test."""
    from llm_wiki.auth.tenant_context import (
        TenantInfo,
        get_current_tenant_id,
        require_tenant_id,
        reset_tenant,
        set_current_tenant,
    )

    assert get_current_tenant_id() is None
    with pytest.raises(RuntimeError):
        require_tenant_id()

    token = set_current_tenant(TenantInfo(tenant_id="abc-123"))
    try:
        assert get_current_tenant_id() == "abc-123"
        assert require_tenant_id() == "abc-123"
    finally:
        reset_tenant(token)

    assert get_current_tenant_id() is None
