"""Tests for the Palantir-style fusion layer: ontology, fusion, AI intel.

Verifies that heterogeneous sources are fused into unique cross-source
indicators with correct provenance (sources, agreement, confidence), and that
the AI synthesiser produces a grounded brief without an LLM configured.
"""

from __future__ import annotations

from plugins.baselith_pitwall.config import PitwallConfig
from plugins.baselith_pitwall.fusion import FusionEngine, FusionInputs
from plugins.baselith_pitwall.intel import IntelSynthesizer
from plugins.baselith_pitwall.models import (
    BattleForecast,
    RaceControlState,
    RaceControlStatus,
    RadioMessage,
    RivalCar,
    StintState,
    TelemetryFrame,
    TyreCompound,
    WeatherState,
)
from plugins.baselith_pitwall.ontology import IndicatorSeverity, SignalSource
from plugins.baselith_pitwall.service import PitwallService


def _stint(**kw) -> StintState:
    base = dict(
        car_id="BC44",
        lap=22,
        total_laps=58,
        position=4,
        compound=TyreCompound.MEDIUM,
        tyre_age_laps=22,
        tyre_wear=0.82,
        deg_rate_per_lap=0.03,
        fuel_kg=35.0,
        engine_temp_c=125.0,
        gap_ahead_s=1.0,
    )
    base.update(kw)
    return StintState(**base)


def _frame(**kw) -> TelemetryFrame:
    base = dict(
        car_id="BC44",
        lap=22,
        position=4,
        speed_kph=300.0,
        engine_temp_c=125.0,
        oil_temp_c=110.0,
        fuel_kg=35.0,
        compound=TyreCompound.MEDIUM,
        tyre_age_laps=22,
        tyre_wear=0.82,
        tyre_temp_c=115.0,
        gap_ahead_s=1.0,
    )
    base.update(kw)
    return TelemetryFrame(**base)


# -- ontology ---------------------------------------------------------------


def test_severity_bands() -> None:
    assert IndicatorSeverity.from_value(0.1) is IndicatorSeverity.LOW
    assert IndicatorSeverity.from_value(0.5) is IndicatorSeverity.MEDIUM
    assert IndicatorSeverity.from_value(0.7) is IndicatorSeverity.HIGH
    assert IndicatorSeverity.from_value(0.95) is IndicatorSeverity.CRITICAL


# -- fusion -----------------------------------------------------------------


def test_fusion_produces_full_indicator_set() -> None:
    engine = FusionEngine()
    iset = engine.fuse(
        FusionInputs(
            stint=_stint(), weather=WeatherState(), race_control=RaceControlState()
        )
    )
    keys = {i.key for i in iset.indicators}
    assert keys == {
        "tyre_cliff_proximity",
        "neutralisation_opportunity",
        "weather_risk",
        "undercut_pressure",
        "strategic_pressure",
    }


def test_tyre_cliff_fuses_telemetry_and_radio() -> None:
    engine = FusionEngine()
    iset = engine.fuse(
        FusionInputs(
            stint=_stint(tyre_wear=0.85),
            weather=WeatherState(),
            race_control=RaceControlState(),
            radio_cues={"pit_pressure"},
        )
    )
    cliff = iset.by_key("tyre_cliff_proximity")
    assert cliff is not None
    assert SignalSource.TELEMETRY in cliff.provenance.sources
    assert SignalSource.RADIO in cliff.provenance.sources
    assert cliff.severity in (IndicatorSeverity.HIGH, IndicatorSeverity.CRITICAL)


def test_strategic_pressure_fuses_many_sources() -> None:
    engine = FusionEngine()
    iset = engine.fuse(
        FusionInputs(
            stint=_stint(),
            weather=WeatherState(track_wetness=0.4),
            race_control=RaceControlState(status=RaceControlStatus.VSC),
            swarm_signals={"pit_pressure": 2.5, "thermal_risk": 2.0},
            radio_cues={"pit_pressure"},
            battle=BattleForecast(
                rival_id="RV7", undercut_delta_s=4.0, verdict="undercut"
            ),
            has_rivals=True,
        )
    )
    sp = iset.by_key("strategic_pressure")
    assert sp is not None
    assert sp.provenance.source_count >= 4
    assert SignalSource.SWARM in sp.provenance.sources


def test_neutralisation_indicator_spikes_under_safety_car() -> None:
    engine = FusionEngine()
    green = engine.fuse(
        FusionInputs(
            stint=_stint(), weather=WeatherState(), race_control=RaceControlState()
        )
    ).by_key("neutralisation_opportunity")
    sc = engine.fuse(
        FusionInputs(
            stint=_stint(),
            weather=WeatherState(),
            race_control=RaceControlState(status=RaceControlStatus.SAFETY_CAR),
        )
    ).by_key("neutralisation_opportunity")
    assert green is not None and sc is not None
    assert sc.value > green.value


# -- AI intel ---------------------------------------------------------------


async def test_intel_brief_is_grounded_without_llm() -> None:
    engine = FusionEngine()
    iset = engine.fuse(
        FusionInputs(
            stint=_stint(),
            weather=WeatherState(),
            race_control=RaceControlState(),
            radio_cues={"pit_pressure"},
        )
    )
    synth = IntelSynthesizer(use_llm=False)
    brief = await synth.brief(iset)
    assert "Tyre Cliff" in brief or "Strategic Pressure" in brief
    assert "%" in brief


# -- service integration ----------------------------------------------------


async def test_service_exposes_indicators_and_intel() -> None:
    cfg = PitwallConfig(use_simulated_source=False, use_llm=False)
    svc = PitwallService(cfg)
    await svc._on_frame(_frame(lap=21, tyre_age_laps=21, tyre_wear=0.78))
    await svc._on_frame(_frame())
    await svc.ingest_radio(
        RadioMessage(car_id="BC44", lap=22, text="No grip, tyres are gone!")
    )
    svc.set_rivals(
        "BC44", [RivalCar(car_id="RV7", position=3, gap_s=-0.9, tyre_age_laps=24)]
    )

    iset = svc.indicators("BC44")
    assert iset is not None and len(iset.indicators) == 5
    cliff = iset.by_key("tyre_cliff_proximity")
    assert cliff is not None and cliff.provenance.source_count >= 2

    brief = await svc.intelligence("BC44")
    assert brief and isinstance(brief, str)

    # Indicators ride along on the live recommendation too.
    rec = await svc.evaluate("BC44")
    assert rec is not None and rec.indicators is not None
    assert len(rec.indicators.indicators) == 5
