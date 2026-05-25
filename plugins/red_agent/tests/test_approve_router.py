"""HTTP tests for /red-agent/scans/{id}/approve|reject endpoints."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.di.container import ServiceRegistry
from plugins.red_agent import dependencies as deps
from plugins.red_agent.approvals import ApprovalRegistry
from plugins.red_agent.routers import approve_router


def _build_app() -> tuple[FastAPI, ApprovalRegistry]:
    registry = ApprovalRegistry()
    ServiceRegistry.register(ApprovalRegistry, registry)
    app = FastAPI()
    app.include_router(approve_router, prefix="/red-agent")

    # Bypass auth-plugin gating: tests run without the auth plugin
    # installed. Override the inner dep callables so the router's
    # `Depends(_security_operator_dep)` resolves to a no-op.
    async def _allow() -> None:
        return None

    app.dependency_overrides[deps._security_operator_dep] = _allow
    app.dependency_overrides[deps._viewer_dep] = _allow
    return app, registry


@pytest.fixture()
def client() -> TestClient:
    app, _ = _build_app()
    return TestClient(app)


def test_approve_unknown_scan_returns_409(client: TestClient) -> None:
    resp = client.post(f"/red-agent/scans/{uuid4()}/approve")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "no pending approval for scan"


def test_reject_unknown_scan_returns_409(client: TestClient) -> None:
    resp = client.post(f"/red-agent/scans/{uuid4()}/reject")
    assert resp.status_code == 409


def test_pending_list_empty_initially(client: TestClient) -> None:
    resp = client.get("/red-agent/scans/pending-approvals")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_approve_resolves_open_future() -> None:
    app, registry = _build_app()
    client = TestClient(app)

    scan_id = uuid4()
    fut = await registry.open(scan_id, reason="test", requested_by="ci")

    resp = client.post(f"/red-agent/scans/{scan_id}/approve")
    assert resp.status_code == 200
    assert resp.json() == {"status": "approved"}

    assert fut.done()
    assert fut.result() is True

    # Second approve has no pending future left.
    resp2 = client.post(f"/red-agent/scans/{scan_id}/approve")
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_reject_resolves_open_future_false() -> None:
    app, registry = _build_app()
    client = TestClient(app)

    scan_id = uuid4()
    fut = await registry.open(scan_id, reason="test", requested_by="ci")

    resp = client.post(f"/red-agent/scans/{scan_id}/reject")
    assert resp.status_code == 200
    assert resp.json() == {"status": "rejected"}
    assert fut.done()
    assert fut.result() is False
