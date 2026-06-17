"""BaselithPitwall — a sentient digital pit wall for motorsport.

High-rate async telemetry ingestion, a pheromone-coordinated vertical agent
swarm (tyres / engine / strategy), MCTS race-scenario simulation, semantic
historical recall, and proactive natural-language recommendations validated by
FIA-regulation guardrails.
"""

from __future__ import annotations

from .config import PitwallConfig
from .models import (
    FIAVerdict,
    PitwallStatus,
    RadioMessage,
    Recommendation,
    RecommendationKind,
    SimScenario,
    StintState,
    TelemetryFrame,
    TyreCompound,
)
from .plugin import BaselithPitwallPlugin
from .service import PitwallService

__all__ = [
    "BaselithPitwallPlugin",
    "PitwallService",
    "PitwallConfig",
    "TelemetryFrame",
    "RadioMessage",
    "StintState",
    "SimScenario",
    "FIAVerdict",
    "Recommendation",
    "RecommendationKind",
    "PitwallStatus",
    "TyreCompound",
]
