"""Battle Forecast + undercut/overcut analysis against a specific rival.

Mirrors the AWS "Battle Forecast" / "Pit Strategy Battle" concept: project how
many laps until a chasing car is within striking distance, and quantify whether
boxing now (undercut) jumps a rival ahead, or staying out (overcut) holds them
off. The numbers come from the pace delta, the gap, and the neutralisation-aware
pit loss — not guesswork.
"""

from __future__ import annotations

from .events import GREEN_PIT_LOSS
from .models import BattleForecast, RivalCar, StintState

# Striking distance: within this gap (s) an attack (DRS/undercut) is live.
_STRIKING_DISTANCE_S = 1.2
# Lap-time advantage of fresh tyres over a rival's worn set, per lap (seconds).
_FRESH_TYRE_ADVANTAGE = 1.3


class BattleAnalyzer:
    """Projects gap evolution and the undercut/overcut verdict for one rival."""

    @staticmethod
    def _own_pace(stint: StintState) -> float:
        """Crude fuel/wear-corrected pace proxy (lower is faster)."""
        return 78.0 + 7.0 * stint.tyre_wear

    @classmethod
    def forecast(
        cls,
        stint: StintState,
        rival: RivalCar,
        pit_loss: float = GREEN_PIT_LOSS,
    ) -> BattleForecast:
        """Produce a battle forecast against ``rival``.

        ``rival.gap_s`` is signed: negative means the rival is ahead of us,
        positive means behind. Closing rate is the per-lap pace delta.
        """
        own = cls._own_pace(stint)
        rival_pace = rival.pace_s_per_lap or (
            78.0 + 7.0 * min(1.0, rival.tyre_age_laps * 0.02)
        )
        closing_rate = rival_pace - own  # >0 means we are faster than the rival
        abs_gap = abs(rival.gap_s)

        laps_to_strike: int | None = None
        if closing_rate > 0.05 and abs_gap > _STRIKING_DISTANCE_S:
            laps_to_strike = int((abs_gap - _STRIKING_DISTANCE_S) / closing_rate) + 1

        # Undercut delta: fresh-tyre time gained over ~2 laps, adjusted for how
        # cheap the stop is right now (a neutralisation makes the stop cheaper,
        # so the undercut is even more attractive). Positive favours undercut.
        undercut_delta = _FRESH_TYRE_ADVANTAGE * 2.0 + (GREEN_PIT_LOSS - pit_loss)

        verdict = cls._verdict(rival, undercut_delta, closing_rate)
        return BattleForecast(
            rival_id=rival.car_id,
            laps_to_striking_distance=laps_to_strike,
            closing_rate_s_per_lap=round(closing_rate, 3),
            undercut_delta_s=round(undercut_delta, 2),
            verdict=verdict,
        )

    @staticmethod
    def _verdict(rival: RivalCar, undercut_delta: float, closing_rate: float) -> str:
        """Classify the optimal posture against the rival."""
        rival_ahead = rival.gap_s < 0
        if rival_ahead:
            # We chase: undercut if the stop nets time, else overcut.
            return "undercut" if undercut_delta > 0 else "overcut"
        # Rival behind and catching us → defend (cover their stop).
        if closing_rate < 0:
            return "defend"
        return "hold"


__all__ = ["BattleAnalyzer"]
