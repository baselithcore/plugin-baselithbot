"""Tests for the central-auth bridge that replaced the wiki's own auth.

Covers the seam in isolation (no DB / no Redis): central JWT claims → engine
user-dict, the permission mapping (admin ⇒ all, user ⇒ default + central∩wiki),
synchronous token verification, and best-effort JIT provisioning.
"""

from __future__ import annotations

from types import SimpleNamespace

import jwt
import pytest

from plugins.baselithwiki import _bootstrap

_bootstrap.ensure_ready()

from llm_wiki.auth import _core_bridge  # noqa: E402
from llm_wiki.auth._core_bridge import (  # noqa: E402
    DEFAULT_USER_PERMS,
    build_user_dict,
    decode_core_token,
    ensure_mirror_rows,
)
from llm_wiki.auth.permissions import ALL_PERMISSIONS  # noqa: E402


def test_admin_claims_get_all_permissions() -> None:
    user = build_user_dict({"sub": "u-admin", "roles": ["admin"], "email": "a@x.io"})
    assert user["role"] == "admin"
    assert user["tenant_id"] == "u-admin"  # 1 tenant = 1 user
    assert set(user["perms"]) == set(ALL_PERMISSIONS)


def test_plain_user_gets_default_permissions() -> None:
    user = build_user_dict({"sub": "u-1", "roles": ["user"], "email": "b@x.io"})
    assert user["role"] == "user"
    assert user["tenant_id"] == "u-1"
    assert user["email"] == "b@x.io"
    assert set(user["perms"]) == set(DEFAULT_USER_PERMS)


def test_default_user_excludes_elevated_but_keeps_interactive() -> None:
    perms = set(build_user_dict({"sub": "u-2", "roles": ["user"]})["perms"])
    # Own private data + shared KB read are allowed…
    assert {"conversation.write", "memory.write", "chat.use", "wiki.read"} <= perms
    # …elevated/admin surfaces are not handed out by default.
    assert "ingest.run" not in perms
    assert "admin.user.manage" not in perms
    assert "feedback.triage" not in perms


def test_missing_email_is_synthesised_from_user_id() -> None:
    user = build_user_dict({"sub": "u-3", "roles": ["user"]})
    assert user["email"] == "u-3@core.local"
    assert user["display_name"] == "u-3"


def test_decode_core_token_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "unit-test-secret-key-0123456789"
    monkeypatch.setattr(
        _core_bridge,
        "get_security_config",
        lambda: SimpleNamespace(secret_key=secret),
    )
    token = jwt.encode(
        {"sub": "u-9", "roles": ["user"], "tenant_id": "u-9", "exp": 9_999_999_999},
        secret,
        algorithm="HS256",
    )
    claims = decode_core_token(token)
    assert claims is not None
    assert claims["sub"] == "u-9"
    assert claims["roles"] == ["user"]


def test_decode_rejects_garbage_and_wrong_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _core_bridge,
        "get_security_config",
        lambda: SimpleNamespace(secret_key="the-real-secret"),
    )
    assert decode_core_token(None) is None
    assert decode_core_token("not-a-jwt") is None
    forged = jwt.encode(
        {"sub": "x", "exp": 9_999_999_999}, "other-secret", algorithm="HS256"
    )
    assert decode_core_token(forged) is None


def test_decode_requires_exp(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "s3cr3t"
    monkeypatch.setattr(
        _core_bridge,
        "get_security_config",
        lambda: SimpleNamespace(secret_key=secret),
    )
    no_exp = jwt.encode({"sub": "u"}, secret, algorithm="HS256")
    assert decode_core_token(no_exp) is None


def test_ensure_mirror_rows_is_best_effort_without_db() -> None:
    # No Postgres configured → get_connection raises → swallowed, never crashes
    # the request path.
    ensure_mirror_rows(
        {"id": "u-x", "email": "u-x@core.local", "display_name": "x", "role": "user"}
    )
