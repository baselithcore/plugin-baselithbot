"""End-to-end isolation tests for the self-service tenancy routes.

Proves the cross-tenant boundary at the API: a user sees only the tenants they
belong to, can switch into a tenant they are a member of, and is REFUSED (403)
when trying to switch into a tenant they do not belong to — so the switch
endpoint can never be a path to another tenant's data.
"""

from __future__ import annotations

from typing import Dict, List, Set

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.auth import AuthRole, AuthUser
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import (
    get_auth_config_dep,
    get_auth_manager_dep,
    get_auth_persistence_dep,
    require_auth,
)
from plugins.auth.router._tenant_routes import router as tenant_router


class _FakePersistence:
    """In-memory membership store for two isolated tenants."""

    def __init__(self) -> None:
        # alice ∈ {t-acme(default)}, bob ∈ {t-globex(default)}
        self._members: Dict[str, Set[str]] = {
            "alice": {"t-acme"},
            "bob": {"t-globex"},
        }
        self._tenants = {
            "t-acme": {"slug": "acme", "name": "Acme"},
            "t-globex": {"slug": "globex", "name": "Globex"},
        }
        self.default_set: List[tuple] = []

    def list_user_tenants(self, user_id: str) -> List[Dict]:
        out = []
        for tid in self._members.get(user_id, set()):
            t = self._tenants[tid]
            out.append(
                {
                    "id": tid,
                    "slug": t["slug"],
                    "name": t["name"],
                    "status": "active",
                    "role": "member",
                    "is_default": True,
                }
            )
        return out

    def is_member(self, user_id: str, tenant_id: str) -> bool:
        return tenant_id in self._members.get(user_id, set())

    def set_default_tenant(self, user_id: str, tenant_id: str) -> bool:
        self.default_set.append((user_id, tenant_id))
        return True


class _FakeManager:
    def __init__(self) -> None:
        self.minted: List[Dict] = []

    async def create_token(self, user_id, roles=None, scopes=None, **extra):
        self.minted.append({"user_id": user_id, **extra})
        return f"token-for-{extra.get('tenant_id')}"


def _client(user_id: str) -> tuple[TestClient, _FakeManager]:
    app = FastAPI()
    app.include_router(tenant_router, prefix="/auth")
    persistence = _FakePersistence()
    manager = _FakeManager()
    app.dependency_overrides[require_auth] = lambda: AuthUser(
        user_id=user_id, roles={AuthRole.USER}
    )
    app.dependency_overrides[get_auth_persistence_dep] = lambda: persistence
    app.dependency_overrides[get_auth_manager_dep] = lambda: manager
    app.dependency_overrides[get_auth_config_dep] = lambda: AuthConfig()
    return TestClient(app), manager


def test_my_tenants_lists_only_own():
    client, _ = _client("alice")
    resp = client.get("/auth/tenants")
    assert resp.status_code == 200
    slugs = {t["slug"] for t in resp.json()}
    assert slugs == {"acme"}  # alice never sees globex


def test_switch_into_own_tenant_succeeds():
    client, manager = _client("alice")
    resp = client.post("/auth/tenants/switch", json={"tenant_id": "t-acme"})
    assert resp.status_code == 200
    # token minted carrying alice's tenant
    assert manager.minted[0]["tenant_id"] == "t-acme"


def test_switch_into_foreign_tenant_is_forbidden():
    """The crux: alice cannot switch into bob's tenant — 403, no token minted."""
    client, manager = _client("alice")
    resp = client.post("/auth/tenants/switch", json={"tenant_id": "t-globex"})
    assert resp.status_code == 403
    assert manager.minted == []  # no access token for a foreign tenant


@pytest.mark.parametrize("user_id,allowed", [("alice", "t-acme"), ("bob", "t-globex")])
def test_each_user_isolated_to_their_tenant(user_id, allowed):
    client, manager = _client(user_id)
    # own tenant works
    assert (
        client.post("/auth/tenants/switch", json={"tenant_id": allowed}).status_code
        == 200
    )
    # the other user's tenant is refused
    foreign = "t-globex" if allowed == "t-acme" else "t-acme"
    assert (
        client.post("/auth/tenants/switch", json={"tenant_id": foreign}).status_code
        == 403
    )
