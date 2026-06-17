"""Tests for the advanced strategy features: neutralisation, weather, battle, MC.

These cover the race-realistic levers added on top of the base pipeline:
Safety-Car / VSC free stops, dry↔wet crossover, undercut/overcut battle
forecasting, and the Monte-Carlo outcome distribution.
"""

from __future__ import annotations

from plugins.baselith_pitwall.battle import BattleAnalyzer
from plugins.baselith_pitwall.config import PitwallConfig
from plugins.baselith_pitwall.events import GREEN_PIT_LOSS, RaceEventModel
from plugins.baselith_pitwall.models import (
    RaceControlState,
    RaceControlStatus,
    RecommendationKind,
    RivalCar,
    StintState,
    TyreCompound,
    WeatherState,
)
from plugins.baselith_pitwall.montecarlo import MonteCarloRace
from plugins.baselith_pitwall.recommendations import RecommendationEngine
from plugins.baselith_pitwall.service import PitwallService
from plugins.baselith_pitwall.weather import WeatherModel


def _stint(**kw) -> StintState:
    base = dict(
        car_id="BC44",
        lap=20,
        total_laps=58,
        position=4,
        compound=TyreCompound.MEDIUM,
        tyre_age_laps=20,
        tyre_wear=0.5,
        deg_rate_per_lap=0.02,
        fuel_kg=40.0,
        engine_temp_c=110.0,
        gap_ahead_s=1.5,
    )
    base.update(kw)
    return StintState(**base)


# -- neutralisation economics ----------------------------------------------


def test_neutralisation_makes_stops_cheaper() -> None:
    assert RaceEventModel.pit_loss(RaceControlStatus.SAFETY_CAR) < GREEN_PIT_LOSS
    assert RaceEventModel.pit_loss(RaceControlStatus.VSC) < GREEN_PIT_LOSS
    assert RaceEventModel.free_stop_saving(RaceControlStatus.SAFETY_CAR) > 0


def test_neutralisation_probability_grows_with_laps() -> None:
    model = RaceEventModel(sc_probability_per_lap=0.05)
    assert model.neutralisation_probability(0) == 0.0
    assert model.neutralisation_probability(40) > model.neutralisation_probability(5)


def test_engine_pits_under_vsc_for_free_stop() -> None:
    engine = RecommendationEngine(
        use_llm=False, legal_compounds=["soft", "medium", "hard"]
    )
    rc = RaceControlState(status=RaceControlStatus.VSC, since_lap=20)
    cand = engine.decide(_stint(tyre_wear=0.4), {}, None, race_control=rc)
    assert cand.kind is RecommendationKind.PIT_VSC


# -- weather crossover ------------------------------------------------------


def test_weather_crossover_detected_on_slicks_in_rain() -> None:
    wet = WeatherState(track_wetness=0.7, rain_intensity=0.6)
    assert WeatherModel.crossover_needed(TyreCompound.MEDIUM, wet)
    assert WeatherModel.ideal_compound(wet) is TyreCompound.WET


def test_no_crossover_when_already_correct() -> None:
    dry = WeatherState(track_wetness=0.0)
    assert not WeatherModel.crossover_needed(TyreCompound.MEDIUM, dry)


def test_engine_recommends_wet_crossover() -> None:
    engine = RecommendationEngine(use_llm=False)
    wet = WeatherState(track_wetness=0.75, rain_intensity=0.7)
    cand = engine.decide(_stint(), {}, None, weather=wet)
    assert cand.kind is RecommendationKind.PIT_WET
    assert cand.pit_compound in {"wet", "intermediate"}


# -- battle forecast --------------------------------------------------------


def test_battle_forecast_undercut_when_chasing_with_cheap_stop() -> None:
    rival = RivalCar(car_id="RV7", position=3, gap_s=-1.0, tyre_age_laps=25)
    forecast = BattleAnalyzer.forecast(_stint(), rival, pit_loss=GREEN_PIT_LOSS)
    assert forecast.rival_id == "RV7"
    assert forecast.verdict in {"undercut", "overcut"}
    assert forecast.undercut_delta_s != 0.0


def test_battle_defend_when_rival_behind_and_faster() -> None:
    rival = RivalCar(
        car_id="RV9", position=5, gap_s=0.8, tyre_age_laps=2, pace_s_per_lap=76.0
    )
    forecast = BattleAnalyzer.forecast(_stint(tyre_wear=0.7), rival)
    assert forecast.verdict in {"defend", "hold"}


# -- Monte Carlo ------------------------------------------------------------


def test_monte_carlo_outcome_is_a_valid_distribution() -> None:
    mc = MonteCarloRace()
    out = mc.outcome_distribution(_stint(), samples=120)
    assert out.samples == 120
    assert 0.0 <= out.p_win <= 1.0
    assert 0.0 <= out.p_podium <= 1.0
    assert out.expected_finish >= 1.0
    assert out.best_strategy in {"one-stop", "two-stop"}


def test_monte_carlo_is_deterministic_for_seed() -> None:
    mc = MonteCarloRace()
    a = mc.outcome_distribution(_stint(), samples=80)
    b = mc.outcome_distribution(_stint(), samples=80)
    assert a.expected_finish == b.expected_finish


# -- service integration ----------------------------------------------------


async def test_service_vsc_triggers_free_stop_recommendation() -> None:
    cfg = PitwallConfig(use_simulated_source=False, use_llm=False, min_confidence=0.5)
    svc = PitwallService(cfg)
    from plugins.baselith_pitwall.models import TelemetryFrame

    await svc._on_frame(
        TelemetryFrame(
            car_id="BC44",
            lap=20,
            position=4,
            speed_kph=300,
            engine_temp_c=110,
            oil_temp_c=100,
            fuel_kg=40,
            compound=TyreCompound.MEDIUM,
            tyre_age_laps=20,
            tyre_wear=0.5,
            tyre_temp_c=100,
            gap_ahead_s=1.5,
        )
    )
    svc.set_race_control(RaceControlStatus.VSC, 20)
    rec = await svc.evaluate("BC44")
    assert rec is not None
    assert rec.kind is RecommendationKind.PIT_VSC
    assert rec.race_control is RaceControlStatus.VSC
    assert rec.outcome is not None and rec.outcome.samples > 0


async def test_service_battle_forecast_and_outcome_exposed() -> None:
    cfg = PitwallConfig(use_simulated_source=False, use_llm=False)
    svc = PitwallService(cfg)
    from plugins.baselith_pitwall.models import TelemetryFrame

    await svc._on_frame(
        TelemetryFrame(
            car_id="BC44",
            lap=15,
            position=4,
            speed_kph=300,
            engine_temp_c=110,
            oil_temp_c=100,
            fuel_kg=45,
            compound=TyreCompound.MEDIUM,
            tyre_age_laps=15,
            tyre_wear=0.45,
            tyre_temp_c=100,
            gap_ahead_s=1.0,
        )
    )
    svc.set_rivals("BC44", [RivalCar(car_id="RV7", position=3, gap_s=-1.0)])
    assert svc.battle_forecast("BC44") is not None
    assert svc.outcome("BC44") is not None
