"""Tests for /red-agent/health readiness probe."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.di.container import ServiceRegistry
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.approvals import ApprovalRegistry
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.events import ScanEventBus
from plugins.red_agent.graph import VulnerabilityGraph
from plugins.red_agent.persistence import RedAgentPersistence
from plugins.red_agent.routers import health_router
from plugins.red_agent.sandbox_runner import SandboxRunner


def _app() -> TestClient:
    app = FastAPI()
    app.include_router(health_router, prefix="/red-agent")
    return TestClient(app)


def _clear_registry() -> None:
    for cls in (
        RedAgentConfig,
        RedAgent,
        RedAgentPersistence,
        VulnerabilityGraph,
        ApprovalRegistry,
        SandboxRunner,
        ScanEventBus,
    ):
        try:
            ServiceRegistry.register(cls, None)
        except Exception:  # noqa: BLE001
            pass


def test_health_degraded_when_components_missing() -> None:
    _clear_registry()
    client = _app()
    resp = client.get("/red-agent/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert all(c["registered"] is False for c in body["components"].values())


def test_health_ok_when_all_registered() -> None:
    ServiceRegistry.register(RedAgentConfig, RedAgentConfig())
    ServiceRegistry.register(RedAgent, MagicMock(spec=RedAgent))
    ServiceRegistry.register(RedAgentPersistence, MagicMock(spec=RedAgentPersistence))
    ServiceRegistry.register(VulnerabilityGraph, MagicMock(spec=VulnerabilityGraph))
    ServiceRegistry.register(ApprovalRegistry, ApprovalRegistry())
    ServiceRegistry.register(SandboxRunner, MagicMock(spec=SandboxRunner))
    ServiceRegistry.register(ScanEventBus, ScanEventBus())

    client = _app()
    resp = client.get("/red-agent/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["pending_approvals"] == 0
    assert all(c["registered"] is True for c in body["components"].values())

    _clear_registry()


@pytest.mark.asyncio
async def test_health_pending_approvals_count() -> None:
    _clear_registry()
    ServiceRegistry.register(RedAgentConfig, RedAgentConfig())
    ServiceRegistry.register(RedAgent, MagicMock(spec=RedAgent))
    ServiceRegistry.register(RedAgentPersistence, MagicMock(spec=RedAgentPersistence))
    ServiceRegistry.register(VulnerabilityGraph, MagicMock(spec=VulnerabilityGraph))
    ServiceRegistry.register(SandboxRunner, MagicMock(spec=SandboxRunner))
    ServiceRegistry.register(ScanEventBus, ScanEventBus())

    registry = ApprovalRegistry()
    ServiceRegistry.register(ApprovalRegistry, registry)
    from uuid import uuid4

    await registry.open(uuid4(), reason="x", requested_by="op")
    await registry.open(uuid4(), reason="y", requested_by="op")

    client = _app()
    resp = client.get("/red-agent/health")
    assert resp.status_code == 200
    assert resp.json()["pending_approvals"] == 2

    _clear_registry()
