"""The :class:`PitwallStore` persistence contract shared by every backend.

The domain talks to this small Protocol, never to a concrete backend. Both the
in-memory default and the durable Postgres implementation satisfy it, so the
service, session manager, and routers stay backend-agnostic. Every method is
``async`` even where the in-memory impl is synchronous internally, so a real I/O
backend never ripples through callers. Persistence is opt-in: nothing here is on
the realtime telemetry hot path — it is the durable *record* of sessions,
emitted recommendations, the audit ledger, and human-in-the-loop acks.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import Recommendation, StintState
from ..session_models import AuditRecord, RaceSession, RecommendationAck

# Per-session retained windows. Bound memory; recent records win.
MAX_RECS_PER_SESSION = 2000
MAX_AUDIT_PER_SESSION = 5000
MAX_SNAPSHOTS_PER_CAR = 1000


@runtime_checkable
class PitwallStore(Protocol):
    """Abstract persistence contract for sessions, recs, audit, and acks."""

    async def initialize(self) -> None:
        """Prepare the backend (e.g. create schema). No-op for in-memory."""
        ...

    # -- Sessions ----------------------------------------------------------

    async def save_session(self, session: RaceSession) -> RaceSession:
        """Insert or replace a race session (keyed by tenant + id)."""
        ...

    async def get_session(self, tenant_id: str, session_id: str) -> RaceSession | None:
        """Fetch a tenant's session by id, or None if unknown."""
        ...

    async def list_sessions(self, tenant_id: str) -> list[RaceSession]:
        """Return all sessions for a tenant, newest first."""
        ...

    async def delete_session(self, tenant_id: str, session_id: str) -> bool:
        """Delete a session and its derived records; True if it existed."""
        ...

    # -- Recommendations ---------------------------------------------------

    async def save_recommendation(
        self, tenant_id: str, session_id: str, rec: Recommendation
    ) -> Recommendation:
        """Append an emitted recommendation to a session's durable history."""
        ...

    async def get_recommendation(
        self, tenant_id: str, session_id: str, rec_id: str
    ) -> Recommendation | None:
        """Fetch one persisted recommendation by id."""
        ...

    async def list_recommendations(
        self,
        tenant_id: str,
        session_id: str,
        car_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Recommendation], int]:
        """Return a page of recommendations (newest first) and the total count."""
        ...

    # -- Audit ledger ------------------------------------------------------

    async def add_audit(self, record: AuditRecord) -> None:
        """Append an immutable audit record."""
        ...

    async def list_audit(
        self,
        tenant_id: str,
        session_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditRecord], int]:
        """Return a page of audit records (newest first) and the total count."""
        ...

    # -- HITL acknowledgements --------------------------------------------

    async def save_ack(self, ack: RecommendationAck) -> RecommendationAck:
        """Persist a strategist's verdict on a recommendation."""
        ...

    async def list_acks(
        self,
        tenant_id: str,
        session_id: str,
        recommendation_id: str | None = None,
    ) -> list[RecommendationAck]:
        """List acks for a session, optionally filtered to one recommendation."""
        ...

    # -- Stint snapshots (debrief trail) ----------------------------------

    async def add_stint_snapshot(
        self, tenant_id: str, session_id: str, stint: StintState
    ) -> None:
        """Append a per-lap belief-state snapshot for post-race debrief."""
        ...

    async def list_stint_snapshots(
        self, tenant_id: str, session_id: str, car_id: str, limit: int = 200
    ) -> list[StintState]:
        """Return recent stint snapshots for one car (oldest→newest)."""
        ...


__all__ = [
    "PitwallStore",
    "MAX_RECS_PER_SESSION",
    "MAX_AUDIT_PER_SESSION",
    "MAX_SNAPSHOTS_PER_CAR",
]
