"""Cross-source fusion engine — the Palantir-style intelligence core.

Takes the heterogeneous, independently-noisy feeds (telemetry, team radio,
weather, race control, rivals/timing, the agent swarm, historical memory) and
fuses them into **unique composite indicators** that no single feed exposes —
each carrying its provenance (which sources, how fresh, how much they agree).

The fusion is deterministic and synchronous; the AI narrative on top of it lives
in :mod:`.intel`. Indicators are normalised to 0..1 so they compose and rank.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .events import GREEN_PIT_LOSS, RaceEventModel
from .models import (
    BattleForecast,
    RaceControlState,
    StintState,
    WeatherState,
)
from .ontology import (
    FusedIndicator,
    IndicatorSet,
    IndicatorSeverity,
    Provenance,
    SignalSource,
)
from .weather import WeatherModel


@dataclass
class FusionInputs:
    """The multi-source bundle fused into one indicator set for a car."""

    stint: StintState
    weather: WeatherState
    race_control: RaceControlState
    swarm_signals: dict[str, float] = field(default_factory=dict)
    radio_cues: set[str] = field(default_factory=set)
    history_hits: list[str] = field(default_factory=list)
    battle: BattleForecast | None = None
    has_rivals: bool = False


def _indicator(
    key: str,
    label: str,
    value: float,
    contributions: dict[str, float],
    sources: list[SignalSource],
    rationale: str,
) -> FusedIndicator:
    """Assemble an indicator, deriving agreement/confidence from contributions."""
    value = max(0.0, min(1.0, value))
    active = [c for c in contributions.values() if c > 0.05]
    agreement = (len(active) / len(contributions)) if contributions else 0.0
    # Confidence rewards corroboration across independent sources.
    confidence = round(
        min(1.0, 0.45 + 0.18 * len(sources)) * (0.5 + 0.5 * agreement), 3
    )
    return FusedIndicator(
        key=key,
        label=label,
        value=round(value, 3),
        severity=IndicatorSeverity.from_value(value),
        confidence=confidence,
        rationale=rationale,
        provenance=Provenance(
            sources=sources,
            agreement=round(agreement, 3),
            contributions={k: round(v, 3) for k, v in contributions.items()},
        ),
    )


class FusionEngine:
    """Fuses heterogeneous signals into the unique cross-source indicator set."""

    def __init__(self, events: RaceEventModel | None = None) -> None:
        self._events = events or RaceEventModel()

    def fuse(self, inp: FusionInputs) -> IndicatorSet:
        """Produce the full fused indicator set for one car at the current lap."""
        indicators = [
            self._tyre_cliff(inp),
            self._neutralisation_opportunity(inp),
            self._weather_risk(inp),
            self._undercut(inp),
        ]
        indicators.append(self._strategic_pressure(inp, indicators))
        return IndicatorSet(
            car_id=inp.stint.car_id, lap=inp.stint.lap, indicators=indicators
        )

    # -- individual unique indicators --------------------------------------

    def _tyre_cliff(self, inp: FusionInputs) -> FusedIndicator:
        """Proximity to the tyre performance cliff (telemetry + radio + memory)."""
        s = inp.stint
        wear = s.tyre_wear
        deg = min(1.0, s.deg_rate_per_lap / 0.05)
        radio_grip = 0.8 if {"pit_pressure", "conserve"} & inp.radio_cues else 0.0
        hist = (
            0.6 if any("cliff" in h or "degrad" in h for h in inp.history_hits) else 0.0
        )
        contributions = {
            "telemetry_wear": wear,
            "telemetry_deg": deg * 0.5,
            "radio_grip": radio_grip,
            "historical_cliff": hist,
        }
        sources = [SignalSource.TELEMETRY]
        if radio_grip:
            sources.append(SignalSource.RADIO)
        if hist:
            sources.append(SignalSource.HISTORICAL)
        value = 0.6 * wear + 0.2 * deg + 0.12 * radio_grip + 0.08 * hist
        return _indicator(
            "tyre_cliff_proximity",
            "Tyre Cliff Proximity",
            value,
            contributions,
            sources,
            f"Wear {wear:.0%}, deg {s.deg_rate_per_lap:.1%}/lap"
            + (", driver reports low grip" if radio_grip else "")
            + (", historical cliff precedent" if hist else "")
            + ".",
        )

    def _neutralisation_opportunity(self, inp: FusionInputs) -> FusedIndicator:
        """Value of pitting under a (possible) neutralisation: race-control + tyre."""
        rc = inp.race_control
        readiness = min(1.0, inp.stint.tyre_age_laps / 12.0)
        if rc.status.neutralised:
            saving = RaceEventModel.free_stop_saving(rc.status) / GREEN_PIT_LOSS
            value = min(1.0, 0.55 + saving) * (0.6 + 0.4 * readiness)
            sources = [SignalSource.RACE_CONTROL, SignalSource.TELEMETRY]
            rationale = f"{rc.status.value.upper()} active — free-stop window open."
        else:
            prob = self._events.neutralisation_probability(inp.stint.laps_remaining)
            value = prob * readiness * 0.6
            sources = [SignalSource.RACE_CONTROL, SignalSource.TELEMETRY]
            rationale = f"P(neutralisation)≈{prob:.0%} over remaining laps."
        return _indicator(
            "neutralisation_opportunity",
            "Neutralisation Opportunity",
            value,
            {"race_control": value, "tyre_readiness": readiness},
            sources,
            rationale,
        )

    def _weather_risk(self, inp: FusionInputs) -> FusedIndicator:
        """Imminence of a weather-driven compound crossover (weather + telemetry)."""
        w = inp.weather
        urgency = WeatherModel.urgency(inp.stint.compound, w)
        value = max(w.track_wetness, w.rain_probability_next_laps, urgency)
        contributions = {
            "wetness": w.track_wetness,
            "rain_forecast": w.rain_probability_next_laps,
            "crossover_urgency": urgency,
        }
        return _indicator(
            "weather_risk",
            "Weather Crossover Risk",
            value,
            contributions,
            [SignalSource.WEATHER, SignalSource.TELEMETRY],
            f"Wetness {w.track_wetness:.0%}, rain forecast {w.rain_probability_next_laps:.0%}"
            + (", tyre family mismatched" if urgency > 0 else "")
            + ".",
        )

    def _undercut(self, inp: FusionInputs) -> FusedIndicator:
        """Undercut threat/opportunity vs the nearest rival (rival + timing + RC)."""
        if inp.battle is None or not inp.has_rivals:
            return _indicator(
                "undercut_pressure",
                "Undercut Pressure",
                0.0,
                {"rival": 0.0},
                [SignalSource.RIVAL],
                "No rival in range.",
            )
        b = inp.battle
        # Normalise the undercut delta (seconds) and proximity into 0..1.
        delta_norm = max(0.0, min(1.0, b.undercut_delta_s / 8.0))
        proximity = 1.0 if (b.laps_to_striking_distance or 99) <= 3 else 0.4
        value = 0.65 * delta_norm + 0.35 * proximity
        return _indicator(
            "undercut_pressure",
            "Undercut Pressure",
            value,
            {"undercut_delta": delta_norm, "proximity": proximity},
            [SignalSource.RIVAL, SignalSource.TIMING, SignalSource.RACE_CONTROL],
            f"Vs {b.rival_id}: {b.verdict}, delta {b.undercut_delta_s:.1f}s.",
        )

    def _strategic_pressure(
        self, inp: FusionInputs, others: list[FusedIndicator]
    ) -> FusedIndicator:
        """Top-line meta-indicator fusing the swarm field with every sub-indicator."""
        swarm_norm = min(1.0, sum(inp.swarm_signals.values()) / 8.0)
        peak = max((i.value for i in others), default=0.0)
        value = 0.55 * peak + 0.45 * swarm_norm
        contributions = {"swarm_field": swarm_norm, "sub_indicator_peak": peak}
        sources = [SignalSource.SWARM]
        for ind in others:
            for src in ind.provenance.sources:
                if src not in sources:
                    sources.append(src)
        return _indicator(
            "strategic_pressure",
            "Strategic Pressure",
            value,
            contributions,
            sources,
            "Composite of the swarm field and every cross-source indicator.",
        )


__all__ = ["FusionEngine", "FusionInputs"]
