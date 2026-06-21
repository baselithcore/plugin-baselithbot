"""Tenant-admin governance: a tenant's own admin manages ITS members but has no
platform power and cannot touch other tenants; a plain member is refused."""

from __future__ import annotations

from typing import Dict, Optional, Set

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.auth import AuthRole, AuthUser
import plugins.auth.admin_router._tenants as tenants_mod
from plugins.auth.admin_router._tenants import router as tenants_router
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_persistence_dep,
    require_auth,
)


class _FakeAudit:
    def log(self, **kwargs):  # noqa: D401
        pass


class _FakePersistence:
    """t-acme has tenant-admin 'ta'; t-globex is separate."""

    def __init__(self) -> None:
        self._admins: Dict[str, Set[str]] = {"t-acme": {"ta"}}
        self._tenants = {
            "t-acme": {
                "id": "t-acme",
                "slug": "acme",
                "name": "Acme",
                "status": "active",
                "member_count": 1,
            },
            "t-globex": {
                "id": "t-globex",
                "slug": "globex",
                "name": "Globex",
                "status": "active",
                "member_count": 0,
            },
        }

    def is_member_admin(self, user_id: str, tenant_id: str) -> bool:
        return user_id in self._admins.get(tenant_id, set())

    def get_tenant(self, tenant_id: str) -> Optional[dict]:
        return self._tenants.get(tenant_id)

    def get_user_by_id(self, user_id: str):
        return object()  # any non-None: the target user exists

    def add_member(self, tenant_id, user_id, role="member", added_by=None) -> bool:
        return True

    def create_tenant(self, slug, name):
        return {
            "id": "new",
            "slug": slug,
            "name": name,
            "status": "active",
            "member_count": 0,
        }

    def list_members(self, tenant_id):
        return []


def _client(user_id: str, roles: Set[AuthRole], monkeypatch) -> TestClient:
    # Keep is_effective_admin DB-free & deterministic: admin iff literal ADMIN role.
    monkeypatch.setattr(
        tenants_mod, "is_effective_admin", lambda uid, rs: AuthRole.ADMIN in rs
    )
    app = FastAPI()
    app.include_router(tenants_router, prefix="/admin")
    app.dependency_overrides[require_auth] = lambda: AuthUser(
        user_id=user_id, roles=roles
    )
    app.dependency_overrides[get_auth_persistence_dep] = lambda: _FakePersistence()
    app.dependency_overrides[get_audit_logger_dep] = lambda: _FakeAudit()
    return TestClient(app)


def test_platform_admin_can_create_and_manage_any(monkeypatch):
    c = _client("root", {AuthRole.ADMIN}, monkeypatch)
    assert c.post("/admin/tenants", json={"slug": "x", "name": "X"}).status_code == 201
    assert (
        c.post("/admin/tenants/t-globex/members", json={"user_id": "u1"}).status_code
        == 200
    )


def test_tenant_admin_manages_own_tenant_members(monkeypatch):
    c = _client("ta", {AuthRole.USER}, monkeypatch)  # tenant-admin of t-acme
    assert (
        c.post("/admin/tenants/t-acme/members", json={"user_id": "u1"}).status_code
        == 200
    )
    assert c.get("/admin/tenants/t-acme/members").status_code == 200


def test_tenant_admin_cannot_touch_other_tenant(monkeypatch):
    c = _client("ta", {AuthRole.USER}, monkeypatch)  # admin of t-acme only
    assert (
        c.post("/admin/tenants/t-globex/members", json={"user_id": "u1"}).status_code
        == 403
    )


def test_tenant_admin_cannot_create_tenant(monkeypatch):
    c = _client("ta", {AuthRole.USER}, monkeypatch)
    assert c.post("/admin/tenants", json={"slug": "x", "name": "X"}).status_code == 403


def test_plain_member_refused(monkeypatch):
    c = _client("bob", {AuthRole.USER}, monkeypatch)  # not admin anywhere
    assert (
        c.post("/admin/tenants/t-acme/members", json={"user_id": "u1"}).status_code
        == 403
    )


def test_tenant_admin_cannot_purge(monkeypatch):
    # GDPR purge is platform-only; a tenant-admin of t-acme is refused (403)
    # before any data deletion runs.
    c = _client("ta", {AuthRole.USER}, monkeypatch)
    assert c.post("/admin/tenants/t-acme/purge").status_code == 403
