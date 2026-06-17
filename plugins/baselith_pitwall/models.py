"""Strongly-typed domain contracts for the digital pit wall.

Every message that enters the realtime queue is validated against these
Pydantic models at the boundary — no raw dicts flow into the swarm, the
simulator, or the guardrails. The models also define the natural-language
recommendation envelope and the FIA-compliance verdict.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .ontology import IndicatorSet


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp (avoids naive-datetime drift)."""
    return datetime.now(timezone.utc)


class TyreCompound(str, Enum):
    """FIA dry/wet tyre compounds relevant to stint strategy."""

    SOFT = "soft"
    MEDIUM = "medium"
    HARD = "hard"
    INTERMEDIATE = "intermediate"
    WET = "wet"


class RecommendationKind(str, Enum):
    """The actionable classes a pit-wall recommendation can take."""

    PIT_NOW = "pit_now"
    PIT_VSC = "pit_vsc"  # opportunistic cheap stop under a neutralisation
    PIT_WET = "pit_wet"  # cross over to a wet/intermediate compound
    STAY_OUT = "stay_out"
    PUSH = "push"
    CONSERVE = "conserve"
    ENGINE_MODE = "engine_mode"
    HOLD = "hold"


class RaceControlStatus(str, Enum):
    """Race-control flag state — drives neutralisation (free-stop) strategy."""

    GREEN = "green"
    YELLOW = "yellow"
    VSC = "vsc"  # virtual safety car — reduced pit-loss window
    SAFETY_CAR = "safety_car"  # full SC — largest free-stop opportunity

    @property
    def neutralised(self) -> bool:
        """True when a stop is materially cheaper than under green flag."""
        return self in (RaceControlStatus.VSC, RaceControlStatus.SAFETY_CAR)


class TelemetryFrame(BaseModel):
    """A single validated telemetry sample for one car.

    This is the only shape accepted off the realtime queue. Ranges are bounded
    so a malformed feed is rejected at ingestion rather than corrupting the
    swarm's belief state.
    """

    model_config = ConfigDict(extra="forbid")

    car_id: str = Field(min_length=1, max_length=32)
    lap: int = Field(ge=0, le=200)
    timestamp: datetime = Field(default_factory=_utcnow)

    position: int = Field(ge=1, le=30)
    sector: int = Field(default=1, ge=1, le=3)

    speed_kph: float = Field(ge=0.0, le=400.0)
    engine_temp_c: float = Field(ge=0.0, le=200.0)
    oil_temp_c: float = Field(ge=0.0, le=200.0)
    ers_deploy: float = Field(default=0.0, ge=0.0, le=1.0)

    fuel_kg: float = Field(ge=0.0, le=120.0)

    compound: TyreCompound = TyreCompound.MEDIUM
    tyre_age_laps: int = Field(ge=0, le=120)
    tyre_wear: float = Field(ge=0.0, le=1.0, description="0=fresh, 1=fully worn.")
    tyre_temp_c: float = Field(ge=0.0, le=200.0)

    gap_ahead_s: float | None = Field(default=None, ge=0.0)
    gap_behind_s: float | None = Field(default=None, ge=0.0)
    last_lap_s: float | None = Field(default=None, gt=0.0)


class RadioMessage(BaseModel):
    """A validated team-radio / driver transmission."""

    model_config = ConfigDict(extra="forbid")

    car_id: str = Field(min_length=1, max_length=32)
    lap: int = Field(ge=0, le=200)
    timestamp: datetime = Field(default_factory=_utcnow)
    source: str = Field(default="driver", max_length=32)
    text: str = Field(min_length=1, max_length=2000)


class StintState(BaseModel):
    """Derived per-car belief state the agents and simulator reason over.

    Built by folding telemetry frames; never accepted from the wire directly.
    """

    model_config = ConfigDict(extra="forbid")

    car_id: str
    lap: int = 0
    total_laps: int = 0
    position: int = 1
    compound: TyreCompound = TyreCompound.MEDIUM
    tyre_age_laps: int = 0
    tyre_wear: float = 0.0
    deg_rate_per_lap: float = 0.0
    fuel_kg: float = 0.0
    engine_temp_c: float = 0.0
    gap_ahead_s: float | None = None
    gap_behind_s: float | None = None
    updated_at: datetime = Field(default_factory=_utcnow)

    @property
    def laps_remaining(self) -> int:
        """Laps left in the race (never negative)."""
        return max(0, self.total_laps - self.lap)


class SimScenario(BaseModel):
    """One evaluated future explored by the MCTS race simulator."""

    model_config = ConfigDict(extra="forbid")

    actions: list[str] = Field(default_factory=list)
    expected_position: float = 0.0
    expected_race_time_s: float = 0.0
    reward: float = 0.0
    probability: float = 1.0


class WeatherState(BaseModel):
    """Track/weather conditions driving dry↔wet compound crossover."""

    model_config = ConfigDict(extra="forbid")

    air_temp_c: float = Field(default=24.0, ge=-10.0, le=60.0)
    track_temp_c: float = Field(default=38.0, ge=-10.0, le=80.0)
    rain_intensity: float = Field(
        default=0.0, ge=0.0, le=1.0, description="0=dry, 1=heavy rain falling now."
    )
    track_wetness: float = Field(
        default=0.0, ge=0.0, le=1.0, description="0=dry line, 1=fully wet surface."
    )
    rain_probability_next_laps: float = Field(
        default=0.0, ge=0.0, le=1.0, description="P(rain) over the next few laps."
    )

    @property
    def is_dry(self) -> bool:
        """Whether the race is currently a declared-dry (slick) situation."""
        return self.track_wetness < 0.25 and self.rain_intensity < 0.2


class RaceControlState(BaseModel):
    """Current race-control / neutralisation state for the session."""

    model_config = ConfigDict(extra="forbid")

    status: RaceControlStatus = RaceControlStatus.GREEN
    since_lap: int = Field(default=0, ge=0)


class RivalCar(BaseModel):
    """A nearby competitor used for undercut/overcut battle analysis."""

    model_config = ConfigDict(extra="forbid")

    car_id: str = Field(min_length=1, max_length=32)
    position: int = Field(ge=1, le=30)
    gap_s: float = Field(
        description="Signed gap: negative = ahead of us, positive = behind."
    )
    compound: TyreCompound = TyreCompound.MEDIUM
    tyre_age_laps: int = Field(default=0, ge=0, le=120)
    pace_s_per_lap: float | None = Field(default=None, gt=0.0)


class BattleForecast(BaseModel):
    """Projection of a battle with one rival (AWS-style Battle Forecast)."""

    model_config = ConfigDict(extra="forbid")

    rival_id: str
    laps_to_striking_distance: int | None = None
    closing_rate_s_per_lap: float = 0.0
    undercut_delta_s: float = 0.0
    verdict: str = "hold"  # undercut | overcut | hold | defend


class StrategyOutcome(BaseModel):
    """Monte-Carlo distribution over race outcomes for the live strategy."""

    model_config = ConfigDict(extra="forbid")

    samples: int = 0
    p_win: float = Field(default=0.0, ge=0.0, le=1.0)
    p_podium: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_finish: float = 0.0
    best_strategy: str = ""
    neutralisation_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class FIAVerdict(BaseModel):
    """Output of the regulation guardrail layer for a candidate action."""

    model_config = ConfigDict(extra="forbid")

    compliant: bool = True
    violations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @property
    def blocking(self) -> bool:
        """True when at least one hard violation must veto the action."""
        return not self.compliant


class Recommendation(BaseModel):
    """A proactive, regulation-checked pit-wall decision in natural language."""

    model_config = ConfigDict(extra="forbid")

    id: str
    car_id: str
    lap: int
    kind: RecommendationKind
    summary: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    fia_verdict: FIAVerdict = Field(default_factory=FIAVerdict)
    scenario: SimScenario | None = None
    battle: BattleForecast | None = None
    outcome: StrategyOutcome | None = None
    indicators: IndicatorSet | None = None
    race_control: RaceControlStatus = RaceControlStatus.GREEN
    pheromone_signals: dict[str, float] = Field(default_factory=dict)
    historical_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class PitwallStatus(BaseModel):
    """Aggregate health snapshot for the dashboard / MCP / status endpoint."""

    model_config = ConfigDict(extra="forbid")

    version: str
    running: bool
    cars_tracked: int
    frames_ingested: int
    recommendations_emitted: int
    queue_depth: int
    swarm_agents: int
    llm_enabled: bool
    semantic_enabled: bool


__all__ = [
    "TyreCompound",
    "RecommendationKind",
    "RaceControlStatus",
    "TelemetryFrame",
    "RadioMessage",
    "StintState",
    "SimScenario",
    "WeatherState",
    "RaceControlState",
    "RivalCar",
    "BattleForecast",
    "StrategyOutcome",
    "FIAVerdict",
    "Recommendation",
    "PitwallStatus",
]
