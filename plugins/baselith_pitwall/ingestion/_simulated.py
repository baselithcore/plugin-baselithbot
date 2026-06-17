"""Deterministic-ish synthetic telemetry generator.

Models a plausible stint (monotonic tyre wear, fuel burn, thermal load, varying
gap) so the plugin boots self-contained and drives the swarm, simulator, and
guardrails end-to-end with zero external infra.
"""

from __future__ import annotations

import asyncio
import math
from typing import Awaitable, Callable

from ..models import TyreCompound


class SimulatedSource:
    """Synthetic telemetry generator for one car."""

    _DEG = {
        TyreCompound.SOFT: 0.030,
        TyreCompound.MEDIUM: 0.020,
        TyreCompound.HARD: 0.013,
        TyreCompound.INTERMEDIATE: 0.025,
        TyreCompound.WET: 0.022,
    }

    def __init__(
        self,
        car_id: str = "BC44",
        total_laps: int = 58,
        tick_seconds: float = 0.5,
        compound: TyreCompound = TyreCompound.MEDIUM,
        start_position: int = 4,
    ) -> None:
        self.car_id = car_id
        self.total_laps = total_laps
        self.tick_seconds = tick_seconds
        self.compound = compound
        self.position = start_position

    async def run(self, emit: Callable[[dict], Awaitable[None]]) -> None:
        """Emit one frame per tick until the race ends or the task is cancelled."""
        deg = self._DEG[self.compound]
        fuel = 1.6 * self.total_laps  # kg, ~1.6 kg/lap burn
        tyre_age = 0
        gap_ahead = 1.8
        try:
            for lap in range(1, self.total_laps + 1):
                tyre_age += 1
                wear = min(1.0, deg * tyre_age)
                fuel = max(0.0, fuel - 1.6)
                push = 0.4 + 0.4 * math.sin(lap / 6.0)  # cyclic push/conserve
                engine_temp = 95.0 + 18.0 * push + 12.0 * wear
                tyre_temp = 88.0 + 22.0 * push + 18.0 * wear
                gap_ahead = max(0.0, gap_ahead + (0.25 - 0.6 * push))
                last_lap = 78.0 + 6.0 * wear - 2.5 * push
                payload = {
                    "car_id": self.car_id,
                    "lap": lap,
                    "position": self.position,
                    "sector": (lap % 3) + 1,
                    "speed_kph": 305.0 - 40.0 * (1.0 - push),
                    "engine_temp_c": round(engine_temp, 1),
                    "oil_temp_c": round(engine_temp - 8.0, 1),
                    "ers_deploy": round(push, 2),
                    "fuel_kg": round(fuel, 1),
                    "compound": self.compound.value,
                    "tyre_age_laps": tyre_age,
                    "tyre_wear": round(wear, 3),
                    "tyre_temp_c": round(tyre_temp, 1),
                    "gap_ahead_s": round(gap_ahead, 2),
                    "gap_behind_s": round(max(0.0, 2.5 - gap_ahead), 2),
                    "last_lap_s": round(last_lap, 2),
                }
                await emit(payload)
                await asyncio.sleep(self.tick_seconds)
        except asyncio.CancelledError:
            raise


__all__ = ["SimulatedSource"]
