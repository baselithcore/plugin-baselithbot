"""Unit tests for the BaselithPitwall plugin.

Covers boundary validation, the swarm field, the FIA guardrail, the decision
engine, the MCTS simulator, and the end-to-end service pipeline — all with the
LLM and external infra disabled so the suite is hermetic and fast.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from plugins.baselith_pitwall.agents import (
    PIT_PRESSURE,
    THERMAL_RISK,
    UNDERCUT,
    SwarmCoordinator,
)
from plugins.baselith_pitwall.config import PitwallConfig
from plugins.baselith_pitwall.guardrails import FIAGuardrail, RaceContext
from plugins.baselith_pitwall.ingestion import TelemetryBus
from plugins.baselith_pitwall.models import (
    RadioMessage,
    RecommendationKind,
    StintState,
    TelemetryFrame,
    TyreCompound,
)
from plugins.baselith_pitwall.recommendations import RecommendationEngine
from plugins.baselith_pitwall.service import PitwallService
from plugins.baselith_pitwall.simulation import RaceSimulator


def _frame(**kw) -> TelemetryFrame:
    base = dict(
        car_id="BC44",
        lap=10,
        position=4,
        speed_kph=300.0,
        engine_temp_c=110.0,
        oil_temp_c=100.0,
        fuel_kg=60.0,
        compound=TyreCompound.MEDIUM,
        tyre_age_laps=10,
        tyre_wear=0.4,
        tyre_temp_c=100.0,
        gap_ahead_s=1.5,
    )
    base.update(kw)
    return TelemetryFrame(**base)


def _stint(**kw) -> StintState:
    base = dict(
        car_id="BC44",
        lap=20,
        total_laps=58,
        position=4,
        compound=TyreCompound.MEDIUM,
        tyre_age_laps=20,
        tyre_wear=0.45,
        deg_rate_per_lap=0.02,
        fuel_kg=40.0,
        engine_temp_c=110.0,
        gap_ahead_s=1.5,
    )
    base.update(kw)
    return StintState(**base)


# -- models / boundary validation -----------------------------------------


def test_telemetry_frame_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        _frame(tyre_wear=1.5)
    with pytest.raises(ValidationError):
        _frame(position=0)


def test_telemetry_frame_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TelemetryFrame.model_validate({**_frame().model_dump(), "ghost": 1})


async def test_bus_drops_invalid_payloads() -> None:
    bus = TelemetryBus(maxsize=16)
    await bus.emit({"car_id": "X", "lap": "not-an-int"})
    assert bus.frames_rejected == 1
    assert bus.frames_ingested == 0
    await bus.emit(_frame().model_dump(mode="json"))
    assert bus.frames_ingested == 1


# -- swarm ------------------------------------------------------------------


def test_swarm_registers_three_verticals() -> None:
    coord = SwarmCoordinator()
    assert coord.agent_count == 3
    assert coord.colony.get_stats()["total_agents"] == 3


def test_swarm_deposits_pit_pressure_past_cliff() -> None:
    coord = SwarmCoordinator()
    signals = coord.observe(_stint(tyre_wear=0.85))
    assert signals[PIT_PRESSURE] >= 2.0


def test_swarm_deposits_thermal_and_undercut() -> None:
    coord = SwarmCoordinator()
    signals = coord.observe(_stint(engine_temp_c=130.0, gap_ahead_s=0.8, tyre_wear=0.3))
    assert signals[THERMAL_RISK] > 0
    assert signals[UNDERCUT] > 0


# -- guardrail --------------------------------------------------------------


def test_guardrail_blocks_early_pit() -> None:
    g = FIAGuardrail()
    verdict = g.validate(
        RecommendationKind.PIT_NOW,
        _stint(lap=1),
        RaceContext(pit_compound="soft"),
    )
    assert verdict.blocking


def test_guardrail_blocks_illegal_compound() -> None:
    g = FIAGuardrail()
    verdict = g.validate(
        RecommendationKind.PIT_NOW,
        _stint(lap=20),
        RaceContext(pit_compound="wet", is_dry=True),
    )
    assert verdict.blocking


def test_guardrail_enforces_mandatory_compound_change() -> None:
    g = FIAGuardrail()
    verdict = g.validate(
        RecommendationKind.STAY_OUT,
        _stint(lap=57, total_laps=58),
        RaceContext(compounds_used={"medium"}, is_dry=True),
    )
    assert verdict.blocking


def test_guardrail_allows_legal_pit() -> None:
    g = FIAGuardrail()
    verdict = g.validate(
        RecommendationKind.PIT_NOW,
        _stint(lap=20),
        RaceContext(compounds_used={"medium"}, pit_compound="soft"),
    )
    assert verdict.compliant


# -- recommendation engine --------------------------------------------------


def test_engine_recommends_pit_under_high_pressure() -> None:
    engine = RecommendationEngine(
        use_llm=False, legal_compounds=["soft", "medium", "hard"]
    )
    cand = engine.decide(_stint(tyre_wear=0.85), {PIT_PRESSURE: 2.6}, None)
    assert cand.kind is RecommendationKind.PIT_NOW
    assert cand.pit_compound in {"soft", "medium", "hard"}


async def test_engine_render_neutralises_blocked_action() -> None:
    engine = RecommendationEngine(use_llm=False)
    cand = engine.decide(_stint(tyre_wear=0.85), {PIT_PRESSURE: 2.6}, None)
    g = FIAGuardrail()
    verdict = g.validate(
        RecommendationKind.PIT_NOW, _stint(lap=1), RaceContext(pit_compound="soft")
    )
    rec = await engine.render(cand, _stint(lap=1), None, {}, [], verdict)
    assert rec.kind is RecommendationKind.HOLD
    assert not rec.fia_verdict.compliant


# -- simulation -------------------------------------------------------------


async def test_simulator_returns_scenario() -> None:
    sim = RaceSimulator(max_iterations=40, horizon_laps=8)
    scenario = await sim.explore(_stint())
    assert scenario is not None
    assert scenario.actions
    assert scenario.expected_position >= 1.0


# -- service pipeline -------------------------------------------------------


async def test_service_pipeline_emits_recommendation() -> None:
    cfg = PitwallConfig(use_simulated_source=False, use_llm=False, sim_total_laps=58)
    svc = PitwallService(cfg)
    for lap in range(1, 30):
        await svc._on_frame(
            _frame(lap=lap, tyre_age_laps=lap, tyre_wear=min(1.0, 0.03 * lap))
        )
    recs = svc.recent_recommendations()
    assert recs
    assert all(r.fia_verdict is not None for r in recs)
    status = svc.status("0.1.0")
    assert status.cars_tracked == 1
    assert status.swarm_agents == 3


async def test_service_radio_triggers_evaluation() -> None:
    cfg = PitwallConfig(use_simulated_source=False, use_llm=False)
    svc = PitwallService(cfg)
    await svc._on_frame(_frame(lap=5, tyre_wear=0.5))
    rec = await svc.ingest_radio(
        RadioMessage(car_id="BC44", lap=5, text="Box box, tyres are gone!")
    )
    assert rec is not None
    assert rec.car_id == "BC44"
