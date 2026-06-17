"""In-memory :class:`PitwallStore` — the zero-config default backend.

Holds everything in bounded per-tenant / per-session structures so the plugin
boots with no external infra and the test-suite stays hermetic. Identical
semantics to the Postgres backend (same keying, same newest-first reads, same
cascade-on-delete), so swapping backends never changes observable behaviour.
"""

from __future__ import annotations

from collections import defaultdict, deque

from ..models import Recommendation, StintState
from ..session_models import AuditRecord, RaceSession, RecommendationAck
from ._protocol import (
    MAX_AUDIT_PER_SESSION,
    MAX_RECS_PER_SESSION,
    MAX_SNAPSHOTS_PER_CAR,
)


class InMemoryPitwallStore:
    """Process-local store; recent records win under the bounded windows."""

    def __init__(self) -> None:
        self._sessions: dict[tuple[str, str], RaceSession] = {}
        self._recs: dict[tuple[str, str], deque[Recommendation]] = defaultdict(
            lambda: deque(maxlen=MAX_RECS_PER_SESSION)
        )
        self._audit: dict[str, deque[AuditRecord]] = defaultdict(
            lambda: deque(maxlen=MAX_AUDIT_PER_SESSION)
        )
        self._acks: dict[tuple[str, str], list[RecommendationAck]] = defaultdict(list)
        self._snaps: dict[tuple[str, str, str], deque[StintState]] = defaultdict(
            lambda: deque(maxlen=MAX_SNAPSHOTS_PER_CAR)
        )

    async def initialize(self) -> None:
        return None

    # -- Sessions ----------------------------------------------------------

    async def save_session(self, session: RaceSession) -> RaceSession:
        self._sessions[(session.tenant_id, session.id)] = session
        return session

    async def get_session(self, tenant_id: str, session_id: str) -> RaceSession | None:
        return self._sessions.get((tenant_id, session_id))

    async def list_sessions(self, tenant_id: str) -> list[RaceSession]:
        items = [s for (t, _), s in self._sessions.items() if t == tenant_id]
        return sorted(items, key=lambda s: s.created_at, reverse=True)

    async def delete_session(self, tenant_id: str, session_id: str) -> bool:
        # The audit ledger is append-only and deliberately survives deletion
        # (the deletion itself is recorded there), mirroring the Postgres cascade.
        existed = self._sessions.pop((tenant_id, session_id), None) is not None
        self._recs.pop((tenant_id, session_id), None)
        self._acks.pop((tenant_id, session_id), None)
        for key in [k for k in self._snaps if k[0] == tenant_id and k[1] == session_id]:
            self._snaps.pop(key, None)
        return existed

    # -- Recommendations ---------------------------------------------------

    async def save_recommendation(
        self, tenant_id: str, session_id: str, rec: Recommendation
    ) -> Recommendation:
        self._recs[(tenant_id, session_id)].append(rec)
        return rec

    async def get_recommendation(
        self, tenant_id: str, session_id: str, rec_id: str
    ) -> Recommendation | None:
        for rec in self._recs.get((tenant_id, session_id), ()):  # type: ignore[arg-type]
            if rec.id == rec_id:
                return rec
        return None

    async def list_recommendations(
        self,
        tenant_id: str,
        session_id: str,
        car_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Recommendation], int]:
        items = [
            r
            for r in reversed(self._recs.get((tenant_id, session_id), deque()))
            if car_id is None or r.car_id == car_id
        ]
        return items[offset : offset + limit], len(items)

    # -- Audit -------------------------------------------------------------

    @staticmethod
    def _audit_key(tenant_id: str, session_id: str) -> str:
        return f"{tenant_id}\x1f{session_id}"

    async def add_audit(self, record: AuditRecord) -> None:
        self._audit[self._audit_key(record.tenant_id, record.session_id)].append(record)

    async def list_audit(
        self,
        tenant_id: str,
        session_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditRecord], int]:
        records: list[AuditRecord] = []
        for key, bucket in self._audit.items():
            t, _, sess = key.partition("\x1f")
            if t != tenant_id:
                continue
            if session_id is not None and sess != session_id:
                continue
            records.extend(bucket)
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[offset : offset + limit], len(records)

    # -- Acks --------------------------------------------------------------

    async def save_ack(self, ack: RecommendationAck) -> RecommendationAck:
        self._acks[(ack.tenant_id, ack.session_id)].append(ack)
        return ack

    async def list_acks(
        self,
        tenant_id: str,
        session_id: str,
        recommendation_id: str | None = None,
    ) -> list[RecommendationAck]:
        items = self._acks.get((tenant_id, session_id), [])
        if recommendation_id is not None:
            items = [a for a in items if a.recommendation_id == recommendation_id]
        return list(reversed(items))

    # -- Stint snapshots ---------------------------------------------------

    async def add_stint_snapshot(
        self, tenant_id: str, session_id: str, stint: StintState
    ) -> None:
        self._snaps[(tenant_id, session_id, stint.car_id)].append(stint)

    async def list_stint_snapshots(
        self, tenant_id: str, session_id: str, car_id: str, limit: int = 200
    ) -> list[StintState]:
        snaps = list(self._snaps.get((tenant_id, session_id, car_id), deque()))
        return snaps[-limit:]


__all__ = ["InMemoryPitwallStore"]
