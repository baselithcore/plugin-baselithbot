"""Liveness + readiness checks for the Red Agent plugin.

`/red-agent/health` is a Kubernetes-style readiness probe — it reports
whether the plugin's required dependencies (registry, sandbox, graph,
persistence) are wired and reachable. The endpoint is unauthenticated
to keep it usable from cluster probes.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from core.di.container import ServiceRegistry
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.approvals import ApprovalRegistry
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.events import ScanEventBus
from plugins.red_agent.graph import VulnerabilityGraph
from plugins.red_agent.persistence import RedAgentPersistence
from plugins.red_agent.sandbox_runner import SandboxRunner

router = APIRouter(prefix="", tags=["red-agent"])


@router.get("/health")
async def health() -> JSONResponse:
    started = time.time()
    components: dict[str, dict[str, Any]] = {}

    for label, cls in (
        ("config", RedAgentConfig),
        ("agent", RedAgent),
        ("persistence", RedAgentPersistence),
        ("graph", VulnerabilityGraph),
        ("approvals", ApprovalRegistry),
        ("sandbox", SandboxRunner),
        ("events", ScanEventBus),
    ):
        instance = ServiceRegistry.get(cls)
        components[label] = {"registered": instance is not None}

    pending: int | None = None
    approvals = ServiceRegistry.get(ApprovalRegistry)
    if approvals is not None:
        try:
            pending = len(await approvals.list_pending())
        except Exception:  # noqa: BLE001
            pending = None

    ok = all(c["registered"] for c in components.values())
    body = {
        "status": "ok" if ok else "degraded",
        "components": components,
        "pending_approvals": pending,
        "elapsed_ms": int((time.time() - started) * 1000),
    }
    code = status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=body, status_code=code)
