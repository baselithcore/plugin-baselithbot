"""Fusion ontology — the common entity model every data source maps into.

Palantir-style intelligence starts with an *ontology*: heterogeneous feeds are
normalised into a single typed model, every datum carries its **provenance**,
and derived insight is traceable back to the sources that produced it. Here the
ontology is small and motorsport-specific: raw :class:`ObservedSignal`s from
many feeds are fused into :class:`FusedIndicator`s — composite signals that no
single source could yield — each annotated with the sources, freshness, and
cross-source agreement behind it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class SignalSource(str, Enum):
    """The heterogeneous feeds the fusion layer ingests and correlates."""

    TELEMETRY = "telemetry"
    RADIO = "radio"
    WEATHER = "weather"
    RACE_CONTROL = "race_control"
    TIMING = "timing"
    RIVAL = "rival"
    SWARM = "swarm"
    HISTORICAL = "historical"


class IndicatorSeverity(str, Enum):
    """Discretised urgency band derived from a normalised indicator value."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_value(cls, value: float) -> "IndicatorSeverity":
        """Map a 0..1 indicator value onto a severity band."""
        if value >= 0.85:
            return cls.CRITICAL
        if value >= 0.6:
            return cls.HIGH
        if value >= 0.33:
            return cls.MEDIUM
        return cls.LOW


class ObservedSignal(BaseModel):
    """One normalised observation from a single source, with confidence."""

    model_config = ConfigDict(extra="forbid")

    source: SignalSource
    key: str = Field(min_length=1, max_length=64)
    value: float
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    note: str = ""


class Provenance(BaseModel):
    """Data lineage for a fused indicator: who contributed and how much they agree."""

    model_config = ConfigDict(extra="forbid")

    sources: list[SignalSource] = Field(default_factory=list)
    agreement: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Fraction of contributing sub-signals pointing the same way.",
    )
    contributions: dict[str, float] = Field(
        default_factory=dict,
        description="Per-sub-signal contribution to the final value (0..1).",
    )

    @property
    def source_count(self) -> int:
        """Number of distinct sources behind the indicator."""
        return len(self.sources)


class FusedIndicator(BaseModel):
    """A unique, cross-source composite signal with its lineage and confidence."""

    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    value: float = Field(ge=0.0, le=1.0)
    severity: IndicatorSeverity = IndicatorSeverity.LOW
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str = ""
    provenance: Provenance = Field(default_factory=Provenance)


class IndicatorSet(BaseModel):
    """The full fused picture for one car at one lap — the intelligence layer."""

    model_config = ConfigDict(extra="forbid")

    car_id: str
    lap: int
    indicators: list[FusedIndicator] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_utcnow)

    def top(self, n: int = 3) -> list[FusedIndicator]:
        """The ``n`` most urgent indicators, value-weighted by confidence."""
        return sorted(
            self.indicators, key=lambda i: i.value * i.confidence, reverse=True
        )[:n]

    def by_key(self, key: str) -> FusedIndicator | None:
        """Look up a single indicator by its key."""
        return next((i for i in self.indicators if i.key == key), None)


__all__ = [
    "SignalSource",
    "IndicatorSeverity",
    "ObservedSignal",
    "Provenance",
    "FusedIndicator",
    "IndicatorSet",
]
