"""HTTP-level guard tests: admin vs non-admin vs anonymous, enforced vs open.

Builds the real control router in a bare FastAPI app and exercises the guard
chain end-to-end (the historical regression: guards calling the auth plugin's
``get_current_user`` directly left its ``Depends`` defaults unresolved and
500'd every route the moment ``auth_required`` was flipped on).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.auth.types import AuthRole, AuthUser
from plugins.baselithcontrol.config import ControlConfig, set_runtime_config
from plugins.baselithcontrol.router import build_control_router

BASE = "/api/baselithcontrol"


@pytest.fixture(autouse=True)
def _reset_runtime_config():
    yield
    set_runtime_config(ControlConfig())


def _app(*, require_admin: bool) -> FastAPI:
    app = FastAPI()
    app.include_router(build_control_router(), prefix=BASE)
    app.state.plugin_registry = {}
    app.state.baselithcontrol_config = ControlConfig(require_admin=require_admin)
    return app


class _FakeManager:
    """Maps bearer tokens to users, like AuthManager.authenticate does."""

    def __init__(self, users: dict[str, AuthUser]) -> None:
        self._users = users

    async def authenticate(self, header: str) -> AuthUser:
        token = header.removeprefix("Bearer ").strip()
        return self._users.get(
            token, AuthUser(user_id="anonymous", roles={AuthRole.ANONYMOUS})
        )


def _enforce_auth(monkeypatch: pytest.MonkeyPatch, users: dict[str, AuthUser]) -> None:
    """Simulate an enforced-auth deployment with a registry-resolved manager."""
    from core.di.container import ServiceRegistry

    manager = _FakeManager(users)

    def fake_get(service_type: Any) -> Any:
        if getattr(service_type, "__name__", "") == "AuthManager":
            return manager
        return None

    monkeypatch.setattr(
        "plugins.baselithcontrol.router._guards._auth_enforced", lambda: True
    )
    monkeypatch.setattr(ServiceRegistry, "get", staticmethod(fake_get))


# ── open deployment (auth not enforced) ─────────────────────────────


def test_open_deployment_reads_allowed_mutations_denied() -> None:
    client = TestClient(_app(require_admin=True))
    me = client.get(f"{BASE}/me")
    assert me.status_code == 200
    body = me.json()
    assert body["authenticated"] is True and body["is_admin"] is False

    assert client.get(f"{BASE}/audit").status_code == 403
    assert client.post(f"{BASE}/actions/ghost/enable").status_code == 403
    # System Console reads are admin-only too (deployment topology).
    assert client.get(f"{BASE}/cli/devtools/jobs").status_code == 403


def test_relaxed_operator_gets_admin_and_localized_messages() -> None:
    client = TestClient(_app(require_admin=False))
    assert client.get(f"{BASE}/me").json()["is_admin"] is True

    res = client.post(f"{BASE}/actions/ghost/enable")
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is False
    assert "not registered" in payload["message"]

    res_it = client.post(
        f"{BASE}/actions/ghost/enable", headers={"Accept-Language": "it"}
    )
    assert "non è registrato" in res_it.json()["message"]

    assert client.get(f"{BASE}/audit").status_code == 200


# ── enforced deployment ──────────────────────────────────────────────


def _users() -> dict[str, AuthUser]:
    return {
        "admintok": AuthUser(user_id="admin-1", roles={AuthRole.ADMIN}),
        "usertok": AuthUser(user_id="user-1", roles={AuthRole.USER}),
    }


def test_enforced_anonymous_is_401_not_500(monkeypatch: pytest.MonkeyPatch) -> None:
    _enforce_auth(monkeypatch, _users())
    client = TestClient(_app(require_admin=True))
    for path in (f"{BASE}/audit", f"{BASE}/me", f"{BASE}/cli/devtools/jobs"):
        res = client.get(path)
        assert res.status_code == 401, f"{path} -> {res.status_code}"
    assert client.post(f"{BASE}/actions/ghost/enable").status_code == 401


def test_enforced_admin_bearer_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    _enforce_auth(monkeypatch, _users())
    client = TestClient(_app(require_admin=True))
    headers = {"Authorization": "Bearer admintok"}
    assert client.get(f"{BASE}/audit", headers=headers).status_code == 200
    me = client.get(f"{BASE}/me", headers=headers).json()
    assert me["user_id"] == "admin-1" and me["is_admin"] is True


def test_enforced_non_admin_is_403_on_mutations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enforce_auth(monkeypatch, _users())
    client = TestClient(_app(require_admin=True))
    headers = {"Authorization": "Bearer usertok"}
    assert client.get(f"{BASE}/me", headers=headers).status_code == 200
    assert client.get(f"{BASE}/audit", headers=headers).status_code == 403
    assert (
        client.post(f"{BASE}/actions/ghost/enable", headers=headers).status_code == 403
    )
    it = client.get(
        f"{BASE}/audit", headers={**headers, "Accept-Language": "it, en;q=0.5"}
    )
    assert it.json()["detail"] == "È richiesto il ruolo admin."


def test_enforced_query_token_authenticates_sse_style(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enforce_auth(monkeypatch, _users())
    client = TestClient(_app(require_admin=True))
    # EventSource cannot set headers — the guard accepts ?token= instead.
    res = client.get(f"{BASE}/audit", params={"token": "admintok"})
    assert res.status_code == 200


def test_enforced_forged_bearer_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _enforce_auth(monkeypatch, _users())
    client = TestClient(_app(require_admin=True))
    res = client.get(f"{BASE}/audit", headers={"Authorization": "Bearer forged"})
    assert res.status_code == 401


def test_audit_limit_is_validated() -> None:
    client = TestClient(_app(require_admin=False))
    assert client.get(f"{BASE}/audit", params={"limit": 0}).status_code == 422
    assert client.get(f"{BASE}/audit", params={"limit": 9999}).status_code == 422
