"""Tests for identity-derived tenancy: the tenant a session works in is
resolved from the authenticated user and embedded in the access token, never
taken from a client-supplied header."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Set

import pytest

from core.auth import AuthRole, AuthUser
from core.context import get_current_tenant_id, reset_tenant_context, set_tenant_context
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import _bind_tenant
from plugins.auth.impersonation import build_actor_claim, issue_impersonation_token
from plugins.auth.router._helpers import issue_tokens
from plugins.auth.tenancy import resolve_user_tenant


def _config(**overrides) -> AuthConfig:
    # Fields carry env aliases (no populate_by_name); override by attribute.
    cfg = AuthConfig()
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


# --- resolver ---------------------------------------------------------------


def test_default_tenant_is_the_user_id():
    """No deployment-wide tenant configured → each user gets a personal tenant."""
    assert resolve_user_tenant("user-123", _config(tenant_id=None)) == "user-123"


def test_two_users_get_isolated_tenants():
    cfg = _config(tenant_id=None)
    assert resolve_user_tenant("alice", cfg) != resolve_user_tenant("bob", cfg)


def test_pinned_deployment_tenant_wins():
    """AUTH_TENANT_ID pins the whole deployment to one shared tenant."""
    cfg = _config(tenant_id="acme")
    assert resolve_user_tenant("alice", cfg) == "acme"
    assert resolve_user_tenant("bob", cfg) == "acme"


def test_blank_pin_falls_back_to_per_user():
    assert resolve_user_tenant("alice", _config(tenant_id="   ")) == "alice"


# --- resolver: membership (enterprise org model) ----------------------------


class _FakeTenantPersistence:
    """Stub exposing only resolve_default_tenant (used by resolve_user_tenant)."""

    def __init__(self, mapping: Dict[str, Any], raises: bool = False):
        self._mapping = mapping
        self._raises = raises

    def resolve_default_tenant(self, user_id: str):
        if self._raises:
            raise RuntimeError("db down")
        return self._mapping.get(user_id)


def test_membership_default_tenant_wins_over_personal():
    """A user assigned to an org tenant lands on it, not their personal tenant."""
    p = _FakeTenantPersistence({"alice": "org-acme"})
    assert resolve_user_tenant("alice", _config(tenant_id=None), p) == "org-acme"


def test_no_membership_falls_back_to_personal_tenant():
    """Backward compatible: a user with no membership keeps tenant == user_id."""
    p = _FakeTenantPersistence({"alice": "org-acme"})
    assert resolve_user_tenant("bob", _config(tenant_id=None), p) == "bob"


def test_deployment_pin_overrides_membership():
    """AUTH_TENANT_ID is the hard override and beats any membership."""
    p = _FakeTenantPersistence({"alice": "org-acme"})
    assert resolve_user_tenant("alice", _config(tenant_id="global"), p) == "global"


def test_membership_read_failure_degrades_to_personal():
    """A tenancy-store error never blocks login — fall back to personal tenant."""
    p = _FakeTenantPersistence({"alice": "org-acme"}, raises=True)
    assert resolve_user_tenant("alice", _config(tenant_id=None), p) == "alice"


# --- context binding --------------------------------------------------------


def test_bind_tenant_sets_context_var():
    token = set_tenant_context("default")
    try:
        _bind_tenant(AuthUser(user_id="u1", tenant_id="tenant-u1"))
        assert get_current_tenant_id() == "tenant-u1"
    finally:
        reset_tenant_context(token)


# --- token issuance embeds the tenant claim ---------------------------------


@dataclass
class _CapturingManager:
    """Captures the kwargs passed to ``create_token``."""

    calls: list = field(default_factory=list)

    async def create_token(self, user_id, roles=None, scopes=None, **extra):
        self.calls.append({"user_id": user_id, "roles": roles, **extra})
        return "fake.jwt.token"


class _StubPersistence:
    def record_login_success(self, user_id):  # noqa: D401
        pass

    def revoke_all_user_tokens(self, user_id):
        return 0

    def store_refresh_token(self, user_id, token, expires_at):
        pass

    def resolve_default_tenant(self, user_id):
        return None  # no membership → personal tenant fallback


class _StubResponse:
    def set_cookie(self, **kwargs):
        pass


@pytest.mark.asyncio
async def test_issue_tokens_embeds_personal_tenant():
    mgr = _CapturingManager()
    await issue_tokens(
        "user-xyz",
        {AuthRole.USER},
        _StubResponse(),
        _StubPersistence(),
        mgr,
        _config(tenant_id=None),
    )
    assert mgr.calls[0]["tenant_id"] == "user-xyz"


@pytest.mark.asyncio
async def test_issue_tokens_honours_deployment_pin():
    mgr = _CapturingManager()
    await issue_tokens(
        "user-xyz",
        {AuthRole.USER},
        _StubResponse(),
        _StubPersistence(),
        mgr,
        _config(tenant_id="acme"),
    )
    assert mgr.calls[0]["tenant_id"] == "acme"


# --- impersonation carries the TARGET's tenant ------------------------------


@dataclass
class _Target:
    id: str
    roles: Set[AuthRole] = field(default_factory=lambda: {AuthRole.USER})


@pytest.mark.asyncio
async def test_impersonation_token_scoped_to_target_tenant():
    mgr = _CapturingManager()
    actor = build_actor_claim("admin-1", "admin@x.io")
    await issue_impersonation_token(
        mgr, _Target(id="target-9"), actor, lifetime=300, tenant_id="target-9"
    )
    claims: Dict[str, Any] = mgr.calls[0]
    assert claims["tenant_id"] == "target-9"


@pytest.mark.asyncio
async def test_impersonation_token_defaults_tenant_to_target_id():
    mgr = _CapturingManager()
    actor = build_actor_claim("admin-1", "admin@x.io")
    await issue_impersonation_token(mgr, _Target(id="target-9"), actor, lifetime=300)
    assert mgr.calls[0]["tenant_id"] == "target-9"
