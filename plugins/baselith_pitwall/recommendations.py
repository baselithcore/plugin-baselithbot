"""Decision policy + natural-language rendering of pit-wall recommendations.

Separation of concerns is deliberate:

* :meth:`RecommendationEngine.decide` turns the pheromone field and the MCTS
  scenario into a *candidate* action (the decision logic).
* The FIA guardrail (:mod:`.guardrails`) independently rules on legality.
* :meth:`RecommendationEngine.render` phrases the validated decision in natural
  language, using the core LLM when available and a deterministic template
  otherwise — so the engine never hard-fails when no model is configured.
"""

from __future__ import annotations

import uuid

from core.observability.logging import get_logger

from .agents import CONSERVE, PIT_PRESSURE, THERMAL_RISK, UNDERCUT
from .models import (
    BattleForecast,
    RaceControlState,
    RaceControlStatus,
    Recommendation,
    RecommendationKind,
    SimScenario,
    StintState,
    TyreCompound,
    WeatherState,
)
from .weather import WeatherModel

logger = get_logger(__name__)


class Candidate:
    """An un-rendered, pre-guardrail decision proposal."""

    def __init__(
        self,
        kind: RecommendationKind,
        confidence: float,
        rationale: str,
        pit_compound: str | None = None,
    ) -> None:
        self.kind = kind
        self.confidence = confidence
        self.rationale = rationale
        self.pit_compound = pit_compound


class RecommendationEngine:
    """Blends swarm signals + simulation into a regulation-aware recommendation."""

    def __init__(
        self,
        use_llm: bool = True,
        llm_model: str | None = None,
        legal_compounds: list[str] | None = None,
    ) -> None:
        self._use_llm = use_llm
        self._llm_model = llm_model
        self._legal = legal_compounds or [c.value for c in TyreCompound]

    # -- decision ----------------------------------------------------------

    def _pit_compound(self, stint: StintState) -> str:
        """Choose a legal compound sized to the remaining race distance."""
        remaining = stint.laps_remaining
        if remaining >= 30 and TyreCompound.HARD.value in self._legal:
            return TyreCompound.HARD.value
        if remaining >= 14 and TyreCompound.MEDIUM.value in self._legal:
            return TyreCompound.MEDIUM.value
        if TyreCompound.SOFT.value in self._legal:
            return TyreCompound.SOFT.value
        return self._legal[0]

    def decide(
        self,
        stint: StintState,
        signals: dict[str, float],
        scenario: SimScenario | None,
        weather: WeatherState | None = None,
        race_control: RaceControlState | None = None,
        battle: BattleForecast | None = None,
    ) -> Candidate:
        """Map swarm field + scenario + race context to a candidate action.

        Priority order reflects real pit-wall logic: a weather crossover and a
        free stop under neutralisation override ordinary degradation strategy.
        """
        # 1) Weather crossover — overrides everything (safety + huge pace delta).
        if weather is not None and WeatherModel.crossover_needed(
            stint.compound, weather
        ):
            target = WeatherModel.ideal_compound(weather)
            return Candidate(
                RecommendationKind.PIT_WET,
                confidence=min(
                    0.97, 0.6 + WeatherModel.urgency(stint.compound, weather)
                ),
                rationale=f"Conditions crossed over (wetness {weather.track_wetness:.0%}); "
                f"fit {target.value} now.",
                pit_compound=target.value,
            )

        # 2) Free stop under a neutralisation (VSC/SC) — bank the cheap stop.
        if (
            race_control is not None
            and race_control.status.neutralised
            and stint.tyre_age_laps >= 1
            and stint.tyre_wear >= 0.25
        ):
            return Candidate(
                RecommendationKind.PIT_VSC,
                confidence=0.92,
                rationale=f"{race_control.status.value.upper()} active — pit now for a "
                "cheap stop and bank the free time.",
                pit_compound=self._pit_compound(stint),
            )

        pit = signals.get(PIT_PRESSURE, 0.0)
        thermal = signals.get(THERMAL_RISK, 0.0)
        undercut = signals.get(UNDERCUT, 0.0)
        conserve = signals.get(CONSERVE, 0.0)
        # A rival-aware undercut verdict reinforces the swarm undercut signal.
        if battle is not None and battle.verdict == "undercut":
            undercut = max(undercut, 1.6)

        if pit >= 2.0:
            return Candidate(
                RecommendationKind.PIT_NOW,
                confidence=min(0.95, 0.6 + pit / 6.0),
                rationale=f"Tyre wear {stint.tyre_wear:.0%} past the cliff; "
                f"pit pressure pheromone {pit:.1f}.",
                pit_compound=self._pit_compound(stint),
            )
        if undercut >= 1.5 and stint.tyre_wear < 0.6:
            return Candidate(
                RecommendationKind.PIT_NOW,
                confidence=min(0.9, 0.55 + undercut / 6.0),
                rationale=f"Undercut window live (gap {stint.gap_ahead_s}s, "
                f"signal {undercut:.1f}); fresh rubber jumps the car ahead.",
                pit_compound=self._pit_compound(stint),
            )
        if thermal >= 1.5:
            return Candidate(
                RecommendationKind.ENGINE_MODE,
                confidence=min(0.85, 0.5 + thermal / 6.0),
                rationale=f"Power-unit thermals high ({stint.engine_temp_c:.0f}°C, "
                f"signal {thermal:.1f}); drop to a conservative mode.",
            )
        if conserve >= 1.0:
            return Candidate(
                RecommendationKind.CONSERVE,
                confidence=min(0.8, 0.5 + conserve / 5.0),
                rationale=f"Degradation trending fast (signal {conserve:.1f}); "
                "manage tyres to extend the stint.",
            )
        return self._from_scenario(scenario)

    def _from_scenario(self, scenario: SimScenario | None) -> Candidate:
        """Fall back to the simulator's first recommended move."""
        if not scenario or not scenario.actions:
            return Candidate(
                RecommendationKind.HOLD,
                confidence=0.5,
                rationale="No dominant signal; hold the current plan.",
            )
        first = scenario.actions[0]
        rationale = (
            f"MCTS favours '{first}' → P{scenario.expected_position:.1f} "
            f"(reward {scenario.reward:.1f})."
        )
        if first.startswith("pit_"):
            return Candidate(
                RecommendationKind.PIT_NOW,
                0.7,
                rationale,
                pit_compound=first.split("_", 1)[1],
            )
        if first == "push":
            return Candidate(RecommendationKind.PUSH, 0.65, rationale)
        if first == "conserve":
            return Candidate(RecommendationKind.CONSERVE, 0.65, rationale)
        return Candidate(RecommendationKind.STAY_OUT, 0.6, rationale)

    # -- rendering ---------------------------------------------------------

    async def render(
        self,
        candidate: Candidate,
        stint: StintState,
        scenario: SimScenario | None,
        signals: dict[str, float],
        history: list[str],
        verdict,
        battle: BattleForecast | None = None,
        outcome=None,
        race_control: RaceControlState | None = None,
    ) -> Recommendation:
        """Build the final recommendation, phrasing the summary in natural language."""
        summary = await self._summary(candidate, stint, history)
        # A blocking FIA verdict cannot be served as-is — neutralise to HOLD.
        kind = candidate.kind
        confidence = candidate.confidence
        if verdict.blocking:
            summary = (
                f"Hold: '{candidate.kind.value}' blocked by regulation "
                f"({'; '.join(verdict.violations)})."
            )
            kind = RecommendationKind.HOLD
            confidence = min(confidence, 0.4)
        return Recommendation(
            id=f"rec-{uuid.uuid4().hex[:10]}",
            car_id=stint.car_id,
            lap=stint.lap,
            kind=kind,
            summary=summary,
            rationale=candidate.rationale,
            confidence=round(confidence, 3),
            fia_verdict=verdict,
            scenario=scenario,
            battle=battle,
            outcome=outcome,
            race_control=race_control.status
            if race_control
            else RaceControlStatus.GREEN,
            pheromone_signals=signals,
            historical_refs=history,
        )

    async def _summary(
        self, candidate: Candidate, stint: StintState, history: list[str]
    ) -> str:
        """Phrase the decision; LLM when enabled, deterministic template otherwise."""
        template = self._template(candidate, stint)
        if not self._use_llm:
            return template
        try:
            from core.services.llm.service import get_llm_service

            service = get_llm_service()
            prompt = (
                "You are a Formula race strategist on the pit wall. In ONE concise "
                "sentence (max 30 words), deliver this decision to the driver as a "
                "clear radio call.\n"
                f"Decision: {candidate.kind.value}. Lap {stint.lap}, P{stint.position}, "
                f"tyre wear {stint.tyre_wear:.0%}, compound {stint.compound.value}.\n"
                f"Rationale: {candidate.rationale}\n"
                + (f"Past precedent: {history[0]}\n" if history else "")
                + "Radio call:"
            )
            text = await service.generate_response(prompt, model=self._llm_model)
            cleaned = text.strip().strip('"')
            return cleaned or template
        except Exception as exc:  # noqa: BLE001 — graceful degrade to template
            logger.info("pitwall_llm_phrasing_unavailable", error=str(exc))
            return template

    @staticmethod
    def _template(candidate: Candidate, stint: StintState) -> str:
        """Deterministic, regulation-safe phrasing used when no LLM is present."""
        prefix = {
            RecommendationKind.PIT_NOW: f"Box this lap for {candidate.pit_compound}",
            RecommendationKind.PIT_VSC: f"Box NOW under neutralisation for {candidate.pit_compound} — free stop",
            RecommendationKind.PIT_WET: f"Box for {candidate.pit_compound} — conditions crossed over",
            RecommendationKind.STAY_OUT: "Stay out, hold track position",
            RecommendationKind.PUSH: "Push now, close the gap",
            RecommendationKind.CONSERVE: "Manage the tyres, lift and coast",
            RecommendationKind.ENGINE_MODE: "Switch to a conservative engine mode",
            RecommendationKind.HOLD: "Hold the current plan",
        }[candidate.kind]
        return f"{prefix} — P{stint.position}, lap {stint.lap}."


__all__ = ["RecommendationEngine", "Candidate"]
