"""End-to-end orchestrator flow with mocked persistence/sandbox/graph.

Exercises the path: submit → guardrails (passive) → run scanner (mocked
SandboxRunner) → publish events → upsert graph → persist findings.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import pytest

from plugins.red_agent.approvals import ApprovalRegistry
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.events import ScanEventBus
from plugins.red_agent.models import (
    ScanIntensity,
    ScanRequest,
    ScanStatus,
    Target,
    TargetType,
)


class _StubPersistence:
    def __init__(self) -> None:
        self.scans: dict[str, dict[str, Any]] = {}
        self.findings: dict[str, list[Any]] = {}

    async def insert_scan(self, scan_id: UUID, request: ScanRequest) -> None:
        self.scans[str(scan_id)] = {
            "status": ScanStatus.QUEUED,
            "request": request,
            "error": None,
        }

    async def update_status(
        self, scan_id: UUID, status: ScanStatus, error: str | None = None
    ) -> None:
        self.scans[str(scan_id)]["status"] = status
        self.scans[str(scan_id)]["error"] = error

    async def insert_findings(self, scan_id: UUID, findings: list[Any]) -> None:
        # Mirrors the real Postgres INSERT semantics: append to the
        # scan's growing list rather than overwriting on each call.
        self.findings.setdefault(str(scan_id), []).extend(findings)

    async def get_scan(self, _scan_id: UUID) -> Any:
        return None


class _StubGraph:
    def __init__(self) -> None:
        self.targets: list[tuple[str, str | None]] = []
        self.scans: list[UUID] = []
        self.findings: list[UUID] = []

    def upsert_target(self, target: Target, tenant_id: str | None) -> None:
        self.targets.append((target.value, tenant_id))

    def upsert_scan(self, scan_id: UUID, _request: ScanRequest) -> None:
        self.scans.append(scan_id)

    def upsert_finding(self, scan_id: UUID, _finding: Any) -> None:
        self.findings.append(scan_id)


class _StubAudit:
    def __init__(self) -> None:
        self.events: list[str] = []

    async def record(self, **kwargs: Any) -> None:
        self.events.append(kwargs.get("event", ""))


class _StubSandbox:
    pass


@pytest.fixture()
def harness(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    cfg = RedAgentConfig(
        scope_allowlist=["example.com"],
        bug_bounty_mode=False,
        require_hitl_for_active=True,
        max_concurrent_scans=2,
        allow_internal_targets=True,  # bypass DNS lookups for the stub host
    )
    persistence = _StubPersistence()
    graph = _StubGraph()
    audit = _StubAudit()
    events = ScanEventBus()
    approvals = ApprovalRegistry()
    sandbox = _StubSandbox()

    agent = RedAgent(
        config=cfg,
        persistence=persistence,  # type: ignore[arg-type]
        graph=graph,  # type: ignore[arg-type]
        audit=audit,  # type: ignore[arg-type]
        sandbox=sandbox,  # type: ignore[arg-type]
        events=events,
        approvals=approvals,
        approval_timeout=2,
    )

    return {
        "agent": agent,
        "persistence": persistence,
        "graph": graph,
        "audit": audit,
        "approvals": approvals,
    }


@pytest.mark.asyncio
async def test_passive_scan_runs_to_completion(
    harness: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    agent: RedAgent = harness["agent"]
    persistence: _StubPersistence = harness["persistence"]
    graph: _StubGraph = harness["graph"]

    async def fake_run_one(self: RedAgent, name: str, req: ScanRequest) -> list[Any]:
        from plugins.red_agent.models import Finding, Severity

        return [
            Finding(
                scanner=name,
                title=f"{name} test finding",
                description="d",
                severity=Severity.LOW,
                target=req.target.value,
            )
        ]

    monkeypatch.setattr(RedAgent, "_run_one_scanner", fake_run_one)

    scan_id = await agent.submit_scan(
        ScanRequest(
            target=Target(type=TargetType.HOSTNAME, value="example.com"),
            scanners=["nmap", "nuclei"],
            intensity=ScanIntensity.PASSIVE,
            requested_by="ci",
        )
    )

    # Wait for the background task to settle.
    for _ in range(50):
        if persistence.scans[str(scan_id)]["status"] in (
            ScanStatus.COMPLETED,
            ScanStatus.FAILED,
        ):
            break
        await asyncio.sleep(0.02)

    assert persistence.scans[str(scan_id)]["status"] == ScanStatus.COMPLETED
    assert len(persistence.findings[str(scan_id)]) == 2
    assert graph.findings == [scan_id, scan_id]


@pytest.mark.asyncio
async def test_active_scan_awaits_approval_then_runs(
    harness: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    agent: RedAgent = harness["agent"]
    persistence: _StubPersistence = harness["persistence"]
    approvals: ApprovalRegistry = harness["approvals"]

    async def fake_run_one(self: RedAgent, name: str, req: ScanRequest) -> list[Any]:
        from plugins.red_agent.models import Finding, Severity

        return [
            Finding(
                scanner=name,
                title="x",
                description="x",
                severity=Severity.MEDIUM,
                target=req.target.value,
            )
        ]

    monkeypatch.setattr(RedAgent, "_run_one_scanner", fake_run_one)

    scan_id = await agent.submit_scan(
        ScanRequest(
            target=Target(type=TargetType.HOSTNAME, value="example.com"),
            scanners=["nmap"],
            intensity=ScanIntensity.ACTIVE,
            requested_by="ci",
        )
    )

    # Should be awaiting approval.
    await asyncio.sleep(0.05)
    assert persistence.scans[str(scan_id)]["status"] == ScanStatus.AWAITING_APPROVAL

    # Approve and let it complete.
    await approvals.resolve(scan_id, approved=True, actor="ci")

    for _ in range(50):
        if persistence.scans[str(scan_id)]["status"] == ScanStatus.COMPLETED:
            break
        await asyncio.sleep(0.02)
    assert persistence.scans[str(scan_id)]["status"] == ScanStatus.COMPLETED


@pytest.mark.asyncio
async def test_active_scan_rejected_marks_cancelled(harness: dict[str, Any]) -> None:
    agent: RedAgent = harness["agent"]
    persistence: _StubPersistence = harness["persistence"]
    approvals: ApprovalRegistry = harness["approvals"]

    scan_id = await agent.submit_scan(
        ScanRequest(
            target=Target(type=TargetType.HOSTNAME, value="example.com"),
            scanners=["nmap"],
            intensity=ScanIntensity.ACTIVE,
            requested_by="ci",
        )
    )
    await asyncio.sleep(0.05)
    await approvals.resolve(scan_id, approved=False, actor="ci")
    await asyncio.sleep(0.05)
    assert persistence.scans[str(scan_id)]["status"] == ScanStatus.CANCELLED
