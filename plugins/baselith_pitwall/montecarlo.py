"""Monte-Carlo race-outcome distribution.

Real strategy teams do not trust a single deterministic plan — they run the
remaining race thousands of times, drawing the uncertain variables (whether a
Safety Car falls, and how hard tyres degrade) from probability distributions,
and read off the *distribution* of finishing positions. This module does the
same on a lightweight per-sample stint model so it stays fast and synchronous
(callable from inside an async handler without blocking meaningfully).
"""

from __future__ import annotations

import random

from .events import GREEN_PIT_LOSS, RaceEventModel
from .models import StintState, StrategyOutcome

# The wear penalty mirrors the MCTS transition model (lap time per unit wear).
_WEAR_PENALTY = 7.0
_DEG_BASE = 0.02  # medium-ish per-lap wear; sampled around this.


class MonteCarloRace:
    """Samples neutralisations + degradation to estimate the outcome spread."""

    def __init__(self, event_model: RaceEventModel | None = None) -> None:
        self._events = event_model or RaceEventModel()

    def outcome_distribution(
        self, stint: StintState, samples: int = 200, seed: int = 12345
    ) -> StrategyOutcome:
        """Estimate P(win/podium) and expected finish for the live strategy.

        Each sample replays the remaining laps: tyres degrade with sampled
        noise, the car pits when worn, and a neutralisation may fall (making
        that stop cheap). The finishing position is approximated from the
        accumulated time lost relative to a clean reference.
        """
        rng = random.Random(seed)  # nosec B311 — simulation, not security
        laps = max(1, stint.laps_remaining)
        start_pos = stint.position
        finishes: list[float] = []
        neutralised_count = 0

        for _ in range(max(1, samples)):
            time_lost, neutralised = self._simulate_once(stint, laps, rng)
            neutralised_count += int(neutralised)
            # Map cumulative time lost onto a position delta (~1 place / 24s).
            finishes.append(max(1.0, start_pos + time_lost / 24.0))

        n = len(finishes)
        wins = sum(1 for f in finishes if f <= 1.5)
        podiums = sum(1 for f in finishes if f <= 3.5)
        expected = sum(finishes) / n
        return StrategyOutcome(
            samples=n,
            p_win=round(wins / n, 3),
            p_podium=round(podiums / n, 3),
            expected_finish=round(expected, 2),
            best_strategy=self._label(stint, laps),
            neutralisation_rate=round(neutralised_count / n, 3),
        )

    def _simulate_once(
        self, stint: StintState, laps: int, rng: random.Random
    ) -> tuple[float, bool]:
        """Replay the remaining laps once; return (time lost vs ref, neutralised)."""
        deg = _DEG_BASE * rng.uniform(0.7, 1.4)
        wear = stint.tyre_wear
        time_lost = 0.0
        neutralised = False
        pitted = False
        for _ in range(laps):
            wear = min(1.0, wear + deg)
            time_lost += _WEAR_PENALTY * wear
            # A neutralisation may fall on this lap.
            if not neutralised and rng.random() < self._events.sc_probability_per_lap:
                neutralised = True
            # Pit when worn; cheaper if a neutralisation is active.
            if wear > 0.7 and not pitted:
                pit_loss = 9.0 if neutralised else GREEN_PIT_LOSS
                time_lost += pit_loss
                wear = 0.0
                pitted = True
        return time_lost, neutralised

    @staticmethod
    def _label(stint: StintState, laps: int) -> str:
        """Human label for the dominant strategy shape."""
        if stint.tyre_wear > 0.7 or laps > 30:
            return "two-stop"
        return "one-stop"


__all__ = ["MonteCarloRace"]
