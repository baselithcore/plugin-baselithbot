"""Unit tests for the StepCritic stack."""

from __future__ import annotations

from plugins.red_agent.critic import (
    CompositeCritic,
    CriticContext,
    RedundancyCritic,
    RoECritic,
    default_critic,
)
from plugins.red_agent.models import ScanIntensity, Target, TargetType
from plugins.red_agent.planner import PlannerStep


def _step(
    scanners: list[str],
    target_value: str = "https://example.com",
    intensity: ScanIntensity = ScanIntensity.PASSIVE,
) -> PlannerStep:
    return PlannerStep(
        scanners=scanners,
        target=Target(type=TargetType.URL, value=target_value),
        intensity=intensity,
    )


def test_roe_critic_blocks_excluded_target() -> None:
    ctx = CriticContext(excluded_targets=["api.example.com"])
    review = RoECritic().review(_step(["nuclei"], "https://api.example.com/v1"), ctx)
    assert not review.approved
    assert "excluded_targets" in review.reason


def test_roe_critic_blocks_target_outside_extra_scope() -> None:
    ctx = CriticContext(
        extra_scope=["example.com"],
        global_scope=["other.com"],
        bug_bounty_mode=False,
    )
    review = RoECritic().review(_step(["nuclei"], "https://elsewhere.test"), ctx)
    assert not review.approved


def test_roe_critic_passes_when_target_in_extra_scope() -> None:
    ctx = CriticContext(extra_scope=["example.com"])
    review = RoECritic().review(_step(["nuclei"], "https://api.example.com"), ctx)
    assert review.approved


def test_roe_critic_passes_when_bug_bounty_mode_on() -> None:
    ctx = CriticContext(bug_bounty_mode=True)
    review = RoECritic().review(_step(["nuclei"], "https://elsewhere.test"), ctx)
    assert review.approved


def test_roe_critic_blocks_intensity_above_ceiling() -> None:
    ctx = CriticContext(
        max_intensity=ScanIntensity.PASSIVE,
        bug_bounty_mode=True,
    )
    review = RoECritic().review(
        _step(["nuclei"], "https://example.com", intensity=ScanIntensity.ACTIVE), ctx
    )
    assert not review.approved
    assert "exceeds ceiling" in review.reason


def test_redundancy_critic_drops_repeats_keeps_novel() -> None:
    ctx = CriticContext(
        executed={("nuclei", "https://example.com")},
    )
    review = RedundancyCritic().review(
        _step(["nuclei", "zap"], "https://example.com"), ctx
    )
    assert review.approved
    assert review.amended_step is not None
    assert review.amended_step.scanners == ["zap"]


def test_redundancy_critic_vetos_when_all_repeats() -> None:
    ctx = CriticContext(
        executed={("nuclei", "https://example.com")},
    )
    review = RedundancyCritic().review(_step(["nuclei"], "https://example.com"), ctx)
    assert not review.approved


def test_composite_first_veto_wins() -> None:
    ctx = CriticContext(
        excluded_targets=["api.example.com"],
        executed=set(),
    )
    composite = CompositeCritic([RoECritic(), RedundancyCritic()])
    review = composite.review(_step(["nuclei"], "https://api.example.com"), ctx)
    assert not review.approved


def test_default_critic_factory_returns_composite() -> None:
    critic = default_critic()
    ctx = CriticContext(bug_bounty_mode=True)
    review = critic.review(_step(["nuclei"], "https://example.com"), ctx)
    assert review.approved
