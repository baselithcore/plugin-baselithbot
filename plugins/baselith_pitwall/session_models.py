"""Enterprise domain contracts: race sessions, audit ledger, HITL acks.

The prototype ran one implicit, ephemeral race. The enterprise product is
*multi-session* and *multi-tenant*: every live race is a :class:`RaceSession`
owned by a tenant, every state-changing act is recorded in an append-only
:class:`AuditRecord` ledger, and every emitted call can be accepted or rejected
by a strategist through a :class:`RecommendationAck` (the human-in-the-loop
contract). These models are persisted losslessly (JSONB round-trip) by the
store and never accept raw dicts off the wire — they validate at the boundary
exactly like :mod:`.models`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp (avoids naive-datetime drift)."""
    return datetime.now(timezone.utc)


class SessionStatus(str, Enum):
    """Lifecycle of a race session managed by the pit wall."""

    CONFIGURING = "configuring"  # created, no telemetry flowing yet
    LIVE = "live"  # ingestion running, decisions emitting
    PAUSED = "paused"  # ingestion suspended (red flag / break)
    FINISHED = "finished"  # race over; record retained for debrief
    ARCHIVED = "archived"  # cold storage, read-only


class TelemetrySourceKind(str, Enum):
    """Where a session's telemetry comes from (drives adapter selection)."""

    SIMULATED = "simulated"
    FILE_REPLAY = "file_replay"
    WEBSOCKET = "websocket"
    UDP = "udp"
    MANUAL = "manual"  # frames pushed only via the REST ingest endpoint


class AuditAction(str, Enum):
    """The auditable acts performed against a session."""

    SESSION_CREATED = "session_created"
    SESSION_STARTED = "session_started"
    SESSION_PAUSED = "session_paused"
    SESSION_ENDED = "session_ended"
    SESSION_DELETED = "session_deleted"
    RACE_CONTROL_SET = "race_control_set"
    WEATHER_SET = "weather_set"
    RIVALS_SET = "rivals_set"
    RADIO_INGESTED = "radio_ingested"
    RECOMMENDATION_EMITTED = "recommendation_emitted"
    RECOMMENDATION_ACK = "recommendation_ack"


class AckStatus(str, Enum):
    """A strategist's verdict on an emitted recommendation."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class RaceSession(BaseModel):
    """A tenant-owned race, the top-level unit the pit wall reasons within."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    tenant_id: str = Field(default="default", max_length=128)
    name: str = Field(min_length=1, max_length=200)
    circuit: str = Field(default="", max_length=200)
    season: str = Field(default="", max_length=32)
    total_laps: int = Field(default=58, gt=0, le=200)
    source_kind: TelemetrySourceKind = TelemetrySourceKind.SIMULATED
    status: SessionStatus = SessionStatus.CONFIGURING
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    started_at: datetime | None = None
    ended_at: datetime | None = None


class AuditRecord(BaseModel):
    """An immutable record of one auditable act within a session."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    tenant_id: str = Field(default="default", max_length=128)
    session_id: str = Field(min_length=1, max_length=64)
    actor: str = Field(default="anonymous", max_length=128)
    action: AuditAction
    car_id: str | None = Field(default=None, max_length=32)
    detail: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)


class RecommendationAck(BaseModel):
    """A human-in-the-loop verdict recorded against a recommendation."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    tenant_id: str = Field(default="default", max_length=128)
    session_id: str = Field(min_length=1, max_length=64)
    recommendation_id: str = Field(min_length=1, max_length=64)
    car_id: str = Field(min_length=1, max_length=32)
    status: AckStatus
    actor: str = Field(default="anonymous", max_length=128)
    note: str = Field(default="", max_length=2000)
    created_at: datetime = Field(default_factory=_utcnow)


class SessionCreate(BaseModel):
    """Request body to provision a new race session."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    circuit: str = Field(default="", max_length=200)
    season: str = Field(default="", max_length=32)
    total_laps: int = Field(default=58, gt=0, le=200)
    source_kind: TelemetrySourceKind = TelemetrySourceKind.SIMULATED


__all__ = [
    "SessionStatus",
    "TelemetrySourceKind",
    "AuditAction",
    "AckStatus",
    "RaceSession",
    "AuditRecord",
    "RecommendationAck",
    "SessionCreate",
]
