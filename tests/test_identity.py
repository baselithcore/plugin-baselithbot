"""Unit tests for the central-identity → dbview gateway-identity bridge."""

from __future__ import annotations

import base64
import json
from unittest.mock import patch

import pytest

from core.auth.types import AuthRole, AuthUser
from plugins.dbview import identity
from plugins.dbview.identity import (
    build_gateway_user_header,
    is_effective_admin_cached,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_caches():
    identity._admin_cache.clear()
    identity._profile_cache.clear()
    yield
    identity._admin_cache.clear()
    identity._profile_cache.clear()


def _no_directory():
    """Header tests stay hermetic — no central auth store lookups."""
    return patch.object(identity, "lookup_central_profile", return_value=(None, None))


def _decode(header_value: str) -> dict:
    padded = header_value + "=" * (-len(header_value) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def _user(
    user_id: str = "u-1",
    roles: set[AuthRole] | None = None,
    email: str | None = "u1@example.com",
    metadata: dict | None = None,
) -> AuthUser:
    return AuthUser(
        user_id=user_id,
        roles=roles or {AuthRole.USER},
        email=email,
        metadata=metadata or {},
    )


def test_header_payload_shape_and_base64url_roundtrip():
    with (
        patch.object(identity, "is_effective_admin_cached", return_value=False),
        patch.object(identity, "resolve_tenant_key", return_value="tenant-x"),
        _no_directory(),
    ):
        header = build_gateway_user_header(_user())
    payload = _decode(header)
    assert payload == {
        "id": "u-1",
        "email": "u1@example.com",
        "displayName": None,
        "role": "user",
        "tenantKey": "tenant-x",
    }
    # base64url alphabet, unpadded — exactly what Node's Buffer 'base64url'
    # decoder and the Zod schema on the dbview side expect.
    assert "=" not in header
    assert "+" not in header and "/" not in header


def test_header_maps_effective_admin_and_display_name():
    user = _user(metadata={"display_name": "Giova"})
    with (
        patch.object(identity, "is_effective_admin_cached", return_value=True),
        patch.object(identity, "resolve_tenant_key", return_value="t"),
        _no_directory(),
    ):
        payload = _decode(build_gateway_user_header(user))
    assert payload["role"] == "admin"
    assert payload["displayName"] == "Giova"


def test_header_synthesizes_placeholder_email_when_missing():
    with (
        patch.object(identity, "is_effective_admin_cached", return_value=False),
        patch.object(identity, "resolve_tenant_key", return_value="t"),
        _no_directory(),
    ):
        payload = _decode(build_gateway_user_header(_user(email=None)))
    assert payload["email"] == "u-1@users.central.local"


def test_effective_admin_uses_rbac_service_and_caches():
    calls: list[str] = []

    def _fake_is_admin(user_id, roles):
        calls.append(user_id)
        return True

    with patch("plugins.auth.rbac.service.is_effective_admin", _fake_is_admin):
        user = _user()
        assert is_effective_admin_cached(user) is True
        assert is_effective_admin_cached(user) is True  # served from cache
    assert calls == ["u-1"], "second call must hit the TTL cache"


def test_header_prefers_central_directory_profile():
    with (
        patch.object(identity, "is_effective_admin_cached", return_value=False),
        patch.object(identity, "resolve_tenant_key", return_value="t"),
        patch.object(
            identity,
            "lookup_central_profile",
            return_value=("real@corp.example", "giova"),
        ),
    ):
        payload = _decode(build_gateway_user_header(_user(email=None)))
    assert payload["email"] == "real@corp.example"
    assert payload["displayName"] == "giova"


def test_lookup_central_profile_degrades_and_caches(monkeypatch):
    calls: list[str] = []

    class _Persistence:
        def get_user_by_id(self, user_id):
            calls.append(user_id)

            class _Rec:
                email = "dir@example.com"
                username = "dir-user"

            return _Rec()

    import plugins.auth.persistence as auth_persistence

    monkeypatch.setattr(
        auth_persistence, "get_auth_persistence", lambda: _Persistence()
    )
    assert identity.lookup_central_profile("u-9") == ("dir@example.com", "dir-user")
    assert identity.lookup_central_profile("u-9") == ("dir@example.com", "dir-user")
    assert calls == ["u-9"], "second call must hit the TTL cache"

    def _boom():
        raise RuntimeError("store down")

    monkeypatch.setattr(auth_persistence, "get_auth_persistence", _boom)
    assert identity.lookup_central_profile("u-10") == (None, None)


def test_effective_admin_falls_back_to_literal_role_on_rbac_outage():
    def _boom(user_id, roles):
        raise RuntimeError("rbac store down")

    with patch("plugins.auth.rbac.service.is_effective_admin", _boom):
        # Wildcard-only admins degrade closed (treated as user)…
        assert is_effective_admin_cached(_user()) is False
        # …but literal ADMIN role still resolves (fallback path).
        admin = _user(user_id="u-2", roles={AuthRole.ADMIN})
        assert is_effective_admin_cached(admin) is True
