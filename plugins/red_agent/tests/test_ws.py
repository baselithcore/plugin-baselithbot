"""WebSocket auth-gate test for /red-agent/ws/scans/{id}.

End-to-end streaming is exercised via the in-process ScanEventBus tests
in test_events.py — that path is fully async-safe. The WS handler thin
wrapper is covered here only for the missing-token rejection rule, which
is the security-critical branch.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.di.container import ServiceRegistry
from plugins.red_agent.events import ScanEventBus
from plugins.red_agent.routers import ws_router


@pytest.fixture()
def app() -> FastAPI:
    bus = ScanEventBus()
    ServiceRegistry.register(ScanEventBus, bus)
    fastapi_app = FastAPI()
    fastapi_app.include_router(ws_router)
    return fastapi_app


def test_ws_rejects_missing_token(app: FastAPI) -> None:
    client = TestClient(app)
    scan_id = uuid4()
    with pytest.raises(Exception):
        with client.websocket_connect(f"/red-agent/ws/scans/{scan_id}"):
            pass
