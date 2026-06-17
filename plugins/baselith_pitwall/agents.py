"""Vertical agent swarm coordinated by digital pheromones.

Three specialist agents — Tyres, Engine, Strategy — observe the shared belief
state and communicate **indirectly** by depositing decaying pheromones into the
core :class:`~core.swarm.pheromones.PheromoneSystem` (stigmergy). No agent calls
another directly; the strategy layer reads the aggregate pheromone field to
decide. This is the native swarm pattern from :mod:`core.swarm`.

Pheromone vocabulary (per-car location ``car:{id}``):

* ``pit_pressure``  — tyres are spent / past their cliff; favour boxing.
* ``thermal_risk``  — power-unit thermals are high; favour conserve / mode change.
* ``undercut``      — a close car ahead + healthy tyres; an undercut is live.
* ``conserve``      — degradation trending fast; back off to extend the stint.
"""

from __future__ import annotations

from core.observability.logging import get_logger
from core.swarm.colony import Colony
from core.swarm.pheromones import PheromoneSystem
from core.swarm.types import AgentProfile, AgentStatus, Capability

from .models import StintState

logger = get_logger(__name__)

# Domain pheromone types deposited by the verticals.
PIT_PRESSURE = "pit_pressure"
THERMAL_RISK = "thermal_risk"
UNDERCUT = "undercut"
CONSERVE = "conserve"

# Thresholds tuned for the simulated/typical stint profile.
_CLIFF_WEAR = 0.78
_HOT_ENGINE_C = 122.0
_UNDERCUT_GAP_S = 1.6


def _location(car_id: str) -> str:
    """Pheromone location key scoped to a single car."""
    return f"car:{car_id}"


class TyreAgent:
    """Vertical specialist: tyre condition and pit-pressure signalling."""

    name = "tyres"

    def analyze(self, stint: StintState, field: PheromoneSystem) -> None:
        """Deposit pit-pressure / conserve pheromones from tyre state."""
        loc = _location(stint.car_id)
        if stint.tyre_wear >= _CLIFF_WEAR:
            field.deposit(PIT_PRESSURE, loc, intensity=2.5, agent_id=self.name)
        elif stint.tyre_wear >= 0.55:
            field.deposit(PIT_PRESSURE, loc, intensity=1.2, agent_id=self.name)
        if stint.deg_rate_per_lap >= 0.025:
            field.deposit(CONSERVE, loc, intensity=1.0, agent_id=self.name)


class EngineAgent:
    """Vertical specialist: power-unit thermals and deployment."""

    name = "engine"

    def analyze(self, stint: StintState, field: PheromoneSystem) -> None:
        """Deposit thermal-risk / conserve pheromones from engine state."""
        loc = _location(stint.car_id)
        if stint.engine_temp_c >= _HOT_ENGINE_C:
            field.deposit(THERMAL_RISK, loc, intensity=2.0, agent_id=self.name)
            field.deposit(CONSERVE, loc, intensity=0.8, agent_id=self.name)
        elif stint.engine_temp_c >= _HOT_ENGINE_C - 8.0:
            field.deposit(THERMAL_RISK, loc, intensity=0.9, agent_id=self.name)


class StrategyAgent:
    """Vertical specialist: race position and undercut opportunity."""

    name = "strategy"

    def analyze(self, stint: StintState, field: PheromoneSystem) -> None:
        """Deposit undercut pheromone when a live opportunity exists."""
        loc = _location(stint.car_id)
        gap = stint.gap_ahead_s
        if gap is not None and gap <= _UNDERCUT_GAP_S and stint.tyre_wear < 0.7:
            intensity = 1.0 + (_UNDERCUT_GAP_S - gap)
            field.deposit(UNDERCUT, loc, intensity=intensity, agent_id=self.name)


class SwarmCoordinator:
    """Owns the colony, registers the verticals, and exposes the field signals."""

    _SIGNAL_TYPES = (PIT_PRESSURE, THERMAL_RISK, UNDERCUT, CONSERVE)

    def __init__(self, colony: Colony | None = None) -> None:
        self.colony = colony or Colony()
        self._verticals = (TyreAgent(), EngineAgent(), StrategyAgent())
        self._register_verticals()

    def _register_verticals(self) -> None:
        """Register each vertical as a swarm agent profile in the colony."""
        caps = {
            "tyres": ["tyre_analysis", "pit_strategy"],
            "engine": ["engine_analysis", "thermal_management"],
            "strategy": ["strategy_synthesis", "race_planning"],
        }
        for agent in self._verticals:
            profile = AgentProfile(
                id=f"pitwall-{agent.name}",
                name=agent.name,
                capabilities=[Capability(name=c) for c in caps[agent.name]],
                status=AgentStatus.IDLE,
            )
            self.colony.register_agent(profile)

    @property
    def agent_count(self) -> int:
        """Number of registered vertical agents."""
        return len(self._verticals)

    def observe(self, stint: StintState) -> dict[str, float]:
        """Run all verticals over the stint and return the aggregate field.

        Each vertical deposits pheromones; the returned dict is the sensed
        intensity per signal type at the car's location after this cycle.
        """
        field = self.colony.pheromones
        for agent in self._verticals:
            agent.analyze(stint, field)
        sensed = field.sense(_location(stint.car_id))
        return {sig: round(sensed.get(sig, 0.0), 3) for sig in self._SIGNAL_TYPES}

    def decay(self) -> None:
        """Apply a pheromone decay cycle (stale signals evaporate)."""
        self.colony.decay_pheromones()


__all__ = [
    "SwarmCoordinator",
    "TyreAgent",
    "EngineAgent",
    "StrategyAgent",
    "PIT_PRESSURE",
    "THERMAL_RISK",
    "UNDERCUT",
    "CONSERVE",
]
