"""HITL e2e gates around the LLM-attack probe scanners.

Walks the full RedAgent.submit_scan path with a stubbed RoE engine
and stubbed persistence to verify that:

* engagements at autonomy_level=execute_active force the scan into
  AWAITING_APPROVAL even on probes that are technically just HTTP;
* HITL denial cancels the scan and the LLM probe never reaches the
  sandbox runner;
* engagement-level rate-limit + auth secret overrides land in the
  effective request's ``Target.metadata`` before scanner dispatch.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import pytest
from pydantic import SecretStr

from plugins.red_agent.agent import RedAgent
from plugins.red_agent.approvals import ApprovalRegistry
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.events import ScanEventBus
from plugins.red_agent.models import (
    AutonomyLevel,
    EngagementRecord,
    RulesOfEngagement,
    ScanIntensity,
    ScanRequest,
    ScanStatus,
    Target,
    TargetType,
)
from plugins.red_agent.rules_of_engagement import RuleOfEngagementEngine


# ---------- shared stubs ----------


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
        self.findings.setdefault(str(scan_id), []).extend(findings)

    async def get_scan(self, _scan_id: UUID) -> Any:
        return None


class _StubGraph:
    def upsert_target(self, target: Target, tenant_id: str | None) -> None:
        del target, tenant_id

    def upsert_scan(self, scan_id: UUID, request: ScanRequest) -> None:
        del scan_id, request

    def upsert_finding(self, scan_id: UUID, finding: Any) -> None:
        del scan_id, finding


class _StubAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def record(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


class _StubEngagementStore:
    def __init__(self, engagement: EngagementRecord) -> None:
        self.engagement = engagement

    async def get(self, engagement_id: UUID) -> EngagementRecord | None:
        if engagement_id == self.engagement.id:
            return self.engagement
        return None


def _make_engagement(rules: RulesOfEngagement) -> EngagementRecord:
    return EngagementRecord(name="llm-eng", objective="probe", rules=rules)


def _build_agent(
    *,
    engagement: EngagementRecord,
    monkeypatch: pytest.MonkeyPatch,
    captured_calls: list[ScanRequest],
) -> tuple[RedAgent, _StubPersistence, ApprovalRegistry]:
    cfg = RedAgentConfig(
        scope_allowlist=["example.com"],
        bug_bounty_mode=False,
        require_hitl_for_active=True,
        max_concurrent_scans=2,
        allow_internal_targets=True,
    )
    persistence = _StubPersistence()
    approvals = ApprovalRegistry()
    audit = _StubAudit()
    events = ScanEventBus()
    roe = RuleOfEngagementEngine(store=_StubEngagementStore(engagement))  # type: ignore[arg-type]

    agent = RedAgent(
        config=cfg,
        persistence=persistence,  # type: ignore[arg-type]
        graph=_StubGraph(),  # type: ignore[arg-type]
        audit=audit,  # type: ignore[arg-type]
        sandbox=object(),  # type: ignore[arg-type]
        events=events,
        approvals=approvals,
        approval_timeout=2,
        roe=roe,
    )

    async def fake_run_one(self: RedAgent, name: str, req: ScanRequest) -> list[Any]:
        captured_calls.append(req)
        return []

    monkeypatch.setattr(RedAgent, "_run_one_scanner", fake_run_one)
    return agent, persistence, approvals


def _llm_probe_request(
    *, engagement_id: UUID, intensity: ScanIntensity = ScanIntensity.ACTIVE
) -> ScanRequest:
    return ScanRequest(
        target=Target(
            type=TargetType.URL,
            value="https://example.com/v1/chat",
            metadata={
                "chat_endpoint": "https://example.com/v1/chat",
                "request_template": {
                    "model": "x",
                    "messages": [{"role": "user", "content": "{prompt}"}],
                },
                "system_prompt_sentinel": "ENG-9001",
            },
        ),
        scanners=["llm_prompt_injection"],
        intensity=intensity,
        requested_by="op",
        engagement_id=engagement_id,
    )


# ---------- tests ----------


@pytest.mark.asyncio
async def test_hitl_denial_blocks_llm_probe_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engagement = _make_engagement(
        RulesOfEngagement(
            scope_allowlist=["example.com"],
            autonomy_level=AutonomyLevel.EXECUTE_ACTIVE,
            max_intensity=ScanIntensity.ACTIVE,
            require_human_approval=True,
        )
    )
    captured: list[ScanRequest] = []
    agent, persistence, approvals = _build_agent(
        engagement=engagement, monkeypatch=monkeypatch, captured_calls=captured
    )

    scan_id = await agent.submit_scan(_llm_probe_request(engagement_id=engagement.id))

    # Wait for AWAITING_APPROVAL.
    for _ in range(50):
        if persistence.scans[str(scan_id)]["status"] == ScanStatus.AWAITING_APPROVAL:
            break
        await asyncio.sleep(0.02)
    assert persistence.scans[str(scan_id)]["status"] == ScanStatus.AWAITING_APPROVAL

    # Deny.
    await approvals.resolve(scan_id, approved=False, actor="op")
    for _ in range(50):
        if persistence.scans[str(scan_id)]["status"] == ScanStatus.CANCELLED:
            break
        await asyncio.sleep(0.02)
    assert persistence.scans[str(scan_id)]["status"] == ScanStatus.CANCELLED
    assert captured == [], "scanner must not run after HITL denial"


@pytest.mark.asyncio
async def test_hitl_approval_lets_llm_probe_dispatch_with_roe_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engagement = _make_engagement(
        RulesOfEngagement(
            scope_allowlist=["example.com"],
            autonomy_level=AutonomyLevel.EXECUTE_ACTIVE,
            max_intensity=ScanIntensity.ACTIVE,
            require_human_approval=True,
            llm_probe_rate_limit_seconds=2.5,
            llm_auth_secret=SecretStr("Bearer engagement-token"),
        )
    )
    captured: list[ScanRequest] = []
    agent, persistence, approvals = _build_agent(
        engagement=engagement, monkeypatch=monkeypatch, captured_calls=captured
    )

    scan_id = await agent.submit_scan(_llm_probe_request(engagement_id=engagement.id))
    for _ in range(50):
        if persistence.scans[str(scan_id)]["status"] == ScanStatus.AWAITING_APPROVAL:
            break
        await asyncio.sleep(0.02)
    await approvals.resolve(scan_id, approved=True, actor="op")
    for _ in range(50):
        if persistence.scans[str(scan_id)]["status"] == ScanStatus.COMPLETED:
            break
        await asyncio.sleep(0.02)
    assert persistence.scans[str(scan_id)]["status"] == ScanStatus.COMPLETED
    assert captured, "scanner must run after HITL approval"
    metadata = captured[0].target.metadata
    assert metadata["rate_limit_seconds"] == 2.5
    assert metadata["auth_token"] == "Bearer engagement-token"


@pytest.mark.asyncio
async def test_engagement_below_execute_active_downgrades_intensity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Passive autonomy → request capped to PASSIVE before scanner sees it.

    The probe scanner enforces ``intensity not in supports_intensity →
    return []`` internally, but the RoE engine is the upstream guard
    that prevents the scan from ever asking for ACTIVE in the first
    place.
    """
    engagement = _make_engagement(
        RulesOfEngagement(
            scope_allowlist=["example.com"],
            autonomy_level=AutonomyLevel.EXECUTE_PASSIVE,
            max_intensity=ScanIntensity.PASSIVE,
            require_human_approval=False,
        )
    )
    captured: list[ScanRequest] = []
    agent, persistence, _ = _build_agent(
        engagement=engagement, monkeypatch=monkeypatch, captured_calls=captured
    )

    scan_id = await agent.submit_scan(_llm_probe_request(engagement_id=engagement.id))
    for _ in range(50):
        if persistence.scans[str(scan_id)]["status"] in (
            ScanStatus.COMPLETED,
            ScanStatus.FAILED,
        ):
            break
        await asyncio.sleep(0.02)
    assert persistence.scans[str(scan_id)]["status"] == ScanStatus.COMPLETED
    assert captured, "scanner runner must still be invoked"
    assert captured[0].intensity == ScanIntensity.PASSIVE
