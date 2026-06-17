"""Race-neutralisation (Safety Car / VSC) economics.

A neutralisation is the single biggest strategic lever in circuit racing: the
field slows, so the time lost serving a pit stop collapses. Teams therefore
pre-compute "if a VSC/SC drops now, do we have a free stop?" and bias plans by a
per-lap neutralisation probability. This module owns those numbers; the
simulator and recommender read them.
"""

from __future__ import annotations

from .models import RaceControlStatus

# Green-flag time lost serving a stop (pit-lane delta + stationary), seconds.
GREEN_PIT_LOSS = 22.0
# Under a full Safety Car the field is bunched and slow: a stop costs far less.
SAFETY_CAR_PIT_LOSS = 9.0
# Under a Virtual Safety Car the delta is in between.
VSC_PIT_LOSS = 13.0


class RaceEventModel:
    """Neutralisation pit-loss economics and per-lap occurrence probability."""

    def __init__(self, sc_probability_per_lap: float = 0.018) -> None:
        # Empirical-ish base rate; ~1 neutralisation per ~55-lap race.
        self.sc_probability_per_lap = max(0.0, min(1.0, sc_probability_per_lap))

    @staticmethod
    def pit_loss(status: RaceControlStatus) -> float:
        """Time lost serving a stop under the given race-control state."""
        if status is RaceControlStatus.SAFETY_CAR:
            return SAFETY_CAR_PIT_LOSS
        if status is RaceControlStatus.VSC:
            return VSC_PIT_LOSS
        return GREEN_PIT_LOSS

    @staticmethod
    def free_stop_saving(status: RaceControlStatus) -> float:
        """Seconds saved versus a green-flag stop if we box under this status."""
        return GREEN_PIT_LOSS - RaceEventModel.pit_loss(status)

    def neutralisation_probability(self, laps_remaining: int) -> float:
        """P(at least one neutralisation in the remaining laps)."""
        laps = max(0, laps_remaining)
        return 1.0 - (1.0 - self.sc_probability_per_lap) ** laps


__all__ = [
    "RaceEventModel",
    "GREEN_PIT_LOSS",
    "VSC_PIT_LOSS",
    "SAFETY_CAR_PIT_LOSS",
]
