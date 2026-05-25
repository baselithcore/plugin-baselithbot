"""Unit tests for the RoE engine."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from plugins.red_agent.guardrails import GuardrailViolation
from plugins.red_agent.models import (
    AutonomyLevel,
    EngagementRecord,
    RulesOfEngagement,
    ScanIntensity,
    ScanRequest,
    Target,
    TargetType,
)
from plugins.red_agent.rules_of_engagement import RuleOfEngagementEngine


class _StubStore:
    def __init__(self, rows: dict[UUID, EngagementRecord] | None = None) -> None:
        self.rows = rows or {}

    @property
    def available(self) -> bool:
        return True

    async def get(self, engagement_id: UUID) -> EngagementRecord | None:
        return self.rows.get(engagement_id)


def _request(
    *,
    target: str = "https://example.com/api",
    intensity: ScanIntensity = ScanIntensity.PASSIVE,
    engagement_id: UUID | None = None,
) -> ScanRequest:
    return ScanRequest(
        target=Target(type=TargetType.URL, value=target),
        engagement_id=engagement_id,
        scanners=["nuclei"],
        intensity=intensity,
        requested_by="op",
    )


def _engagement(rules: RulesOfEngagement) -> EngagementRecord:
    return EngagementRecord(name="eng", objective="obj", rules=rules)


@pytest.mark.asyncio
async def test_no_engagement_passthrough() -> None:
    engine = RuleOfEngagementEngine(store=_StubStore())  # type: ignore[arg-type]
    decision = await engine.evaluate(_request())
    assert decision.effective_request.intensity == ScanIntensity.PASSIVE
    assert decision.force_hitl is False
    assert decision.adjustments == []


@pytest.mark.asyncio
async def test_missing_engagement_raises() -> None:
    engine = RuleOfEngagementEngine(store=_StubStore())  # type: ignore[arg-type]
    with pytest.raises(GuardrailViolation) as exc:
        await engine.evaluate(_request(engagement_id=uuid4()))
    assert exc.value.code == "ENGAGEMENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_excluded_target_blocked() -> None:
    eng = _engagement(
        RulesOfEngagement(
            scope_allowlist=["example.com"],
            excluded_targets=["api.example.com"],
            max_intensity=ScanIntensity.ACTIVE,
            autonomy_level=AutonomyLevel.EXECUTE_ACTIVE,
        )
    )
    store = _StubStore({eng.id: eng})
    engine = RuleOfEngagementEngine(store=store)  # type: ignore[arg-type]
    with pytest.raises(GuardrailViolation) as exc:
        await engine.evaluate(
            _request(
                target="https://api.example.com/v1",
                engagement_id=eng.id,
            )
        )
    assert exc.value.code == "EXCLUDED_BY_ENGAGEMENT"


@pytest.mark.asyncio
async def test_intensity_capped_by_max_intensity() -> None:
    eng = _engagement(
        RulesOfEngagement(
            max_intensity=ScanIntensity.PASSIVE,
            autonomy_level=AutonomyLevel.EXECUTE_INTRUSIVE,
        )
    )
    engine = RuleOfEngagementEngine(store=_StubStore({eng.id: eng}))  # type: ignore[arg-type]
    decision = await engine.evaluate(
        _request(intensity=ScanIntensity.INTRUSIVE, engagement_id=eng.id)
    )
    assert decision.effective_request.intensity == ScanIntensity.PASSIVE
    assert any("intensity downgraded intrusive" in a for a in decision.adjustments)


@pytest.mark.asyncio
async def test_autonomy_caps_intensity_below_max() -> None:
    eng = _engagement(
        RulesOfEngagement(
            max_intensity=ScanIntensity.INTRUSIVE,
            autonomy_level=AutonomyLevel.EXECUTE_PASSIVE,
        )
    )
    engine = RuleOfEngagementEngine(store=_StubStore({eng.id: eng}))  # type: ignore[arg-type]
    decision = await engine.evaluate(
        _request(intensity=ScanIntensity.ACTIVE, engagement_id=eng.id)
    )
    assert decision.effective_request.intensity == ScanIntensity.PASSIVE
    assert decision.autonomy_level == AutonomyLevel.EXECUTE_PASSIVE


@pytest.mark.asyncio
async def test_autonomy_below_execute_blocks_run() -> None:
    eng = _engagement(RulesOfEngagement(autonomy_level=AutonomyLevel.RECOMMEND))
    engine = RuleOfEngagementEngine(store=_StubStore({eng.id: eng}))  # type: ignore[arg-type]
    with pytest.raises(GuardrailViolation) as exc:
        await engine.evaluate(_request(engagement_id=eng.id))
    assert exc.value.code == "AUTONOMY_INSUFFICIENT"


@pytest.mark.asyncio
async def test_force_hitl_when_engagement_requires_approval() -> None:
    eng = _engagement(
        RulesOfEngagement(
            max_intensity=ScanIntensity.ACTIVE,
            autonomy_level=AutonomyLevel.EXECUTE_ACTIVE,
            require_human_approval=True,
        )
    )
    engine = RuleOfEngagementEngine(store=_StubStore({eng.id: eng}))  # type: ignore[arg-type]
    decision = await engine.evaluate(_request(engagement_id=eng.id))
    assert decision.force_hitl is True


@pytest.mark.asyncio
async def test_extra_scope_returned_for_pipeline() -> None:
    eng = _engagement(
        RulesOfEngagement(
            scope_allowlist=["partner.example.com", "203.0.113.0/24"],
            autonomy_level=AutonomyLevel.EXECUTE_PASSIVE,
        )
    )
    engine = RuleOfEngagementEngine(store=_StubStore({eng.id: eng}))  # type: ignore[arg-type]
    decision = await engine.evaluate(_request(engagement_id=eng.id))
    assert "partner.example.com" in decision.extra_scope
    assert "203.0.113.0/24" in decision.extra_scope


@pytest.mark.asyncio
async def test_llm_rate_limit_override_merged_into_target_metadata() -> None:
    from pydantic import SecretStr

    eng = _engagement(
        RulesOfEngagement(
            scope_allowlist=["example.com"],
            autonomy_level=AutonomyLevel.EXECUTE_ACTIVE,
            max_intensity=ScanIntensity.ACTIVE,
            llm_probe_rate_limit_seconds=2.5,
            llm_auth_secret=SecretStr("Bearer engagement-token"),
        )
    )
    engine = RuleOfEngagementEngine(store=_StubStore({eng.id: eng}))  # type: ignore[arg-type]
    decision = await engine.evaluate(
        _request(engagement_id=eng.id, intensity=ScanIntensity.ACTIVE)
    )
    meta = decision.effective_request.target.metadata
    assert meta["rate_limit_seconds"] == 2.5
    assert meta["auth_token"] == "Bearer engagement-token"
    assert any("rate_limit_seconds" in a for a in decision.adjustments)
    assert any("auth_secret" in a for a in decision.adjustments)


@pytest.mark.asyncio
async def test_llm_require_rate_limit_blocks_when_unset() -> None:
    eng = _engagement(
        RulesOfEngagement(
            scope_allowlist=["example.com"],
            autonomy_level=AutonomyLevel.EXECUTE_ACTIVE,
            max_intensity=ScanIntensity.ACTIVE,
            llm_require_rate_limit=True,
        )
    )
    engine = RuleOfEngagementEngine(store=_StubStore({eng.id: eng}))  # type: ignore[arg-type]
    with pytest.raises(GuardrailViolation) as excinfo:
        await engine.evaluate(
            _request(engagement_id=eng.id, intensity=ScanIntensity.ACTIVE)
        )
    assert excinfo.value.code == "LLM_RATE_LIMIT_REQUIRED"


@pytest.mark.asyncio
async def test_llm_require_rate_limit_passes_when_request_supplies_it() -> None:
    eng = _engagement(
        RulesOfEngagement(
            scope_allowlist=["example.com"],
            autonomy_level=AutonomyLevel.EXECUTE_ACTIVE,
            max_intensity=ScanIntensity.ACTIVE,
            llm_require_rate_limit=True,
        )
    )
    engine = RuleOfEngagementEngine(store=_StubStore({eng.id: eng}))  # type: ignore[arg-type]
    req = ScanRequest(
        target=Target(
            type=TargetType.URL,
            value="https://example.com",
            metadata={"rate_limit_seconds": 1.0},
        ),
        engagement_id=eng.id,
        scanners=["llm_prompt_injection"],
        intensity=ScanIntensity.ACTIVE,
        requested_by="op",
    )
    decision = await engine.evaluate(req)
    assert decision.effective_request.target.metadata["rate_limit_seconds"] == 1.0


@pytest.mark.asyncio
async def test_llm_auth_secret_never_appears_in_repr() -> None:
    from pydantic import SecretStr

    rules = RulesOfEngagement(
        llm_auth_secret=SecretStr("Bearer super-sensitive-token-XYZ"),
    )
    rendered = repr(rules)
    assert "super-sensitive-token-XYZ" not in rendered
    assert "SecretStr" in rendered or "**" in rendered
