"""Multi-session registry over the per-session orchestration services.

The prototype ran a single implicit :class:`PitwallService`. The enterprise
product runs *many*: one live engine per :class:`RaceSession`, each with its own
telemetry bus and adapter, isolated by tenant. The manager owns their lifecycle
(create → start → pause → end → delete), persists every session and every
auditable act through the :class:`PitwallStore`, and records human-in-the-loop
acknowledgements. A default ``demo`` session is provisioned at boot when the
simulated source is enabled, so the bundled dashboard works zero-config exactly
as before.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from core.observability.logging import get_logger

from .config import PitwallConfig
from .ingestion import build_source
from .metrics import dec_sessions, inc_sessions
from .service import PitwallService
from .session_models import (
    AckStatus,
    AuditAction,
    AuditRecord,
    RaceSession,
    RecommendationAck,
    SessionCreate,
    SessionStatus,
    TelemetrySourceKind,
)
from .store import PitwallStore

logger = get_logger(__name__)

DEFAULT_SESSION_ID = "demo"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PitwallSessionManager:
    """Owns the set of live race sessions and their orchestration services."""

    def __init__(self, config: PitwallConfig, store: PitwallStore) -> None:
        self.config = config
        self.store = store
        self._services: dict[tuple[str, str], PitwallService] = {}

    # -- lifecycle ---------------------------------------------------------

    async def initialize(self) -> None:
        """Prepare the store and provision the default demo session if enabled."""
        await self.store.initialize()
        if self.config.use_simulated_source:
            await self._ensure_demo_session()

    async def _ensure_demo_session(self) -> None:
        """Create and start the zero-config demo session (idempotent)."""
        existing = await self.store.get_session("default", DEFAULT_SESSION_ID)
        if existing is None:
            session = RaceSession(
                id=DEFAULT_SESSION_ID,
                tenant_id="default",
                name="Demo Race",
                circuit="Baselith Circuit",
                total_laps=self.config.sim_total_laps,
                source_kind=TelemetrySourceKind.SIMULATED,
            )
            await self.store.save_session(session)
        await self.start_session("default", DEFAULT_SESSION_ID, actor="system")

    async def shutdown(self) -> None:
        """Stop every live service and release the registry."""
        for service in list(self._services.values()):
            await service.shutdown()
        self._services.clear()

    # -- session CRUD ------------------------------------------------------

    async def create_session(
        self, tenant_id: str, spec: SessionCreate, *, actor: str
    ) -> RaceSession:
        """Provision (but do not start) a new race session for a tenant."""
        session = RaceSession(
            id=uuid.uuid4().hex[:16],
            tenant_id=tenant_id,
            name=spec.name,
            circuit=spec.circuit,
            season=spec.season,
            total_laps=spec.total_laps,
            source_kind=spec.source_kind,
        )
        await self.store.save_session(session)
        await self._audit(session, AuditAction.SESSION_CREATED, actor)
        logger.info("pitwall_session_created", tenant=tenant_id, session=session.id)
        return session

    async def start_session(
        self, tenant_id: str, session_id: str, *, actor: str
    ) -> RaceSession | None:
        """Build the engine, attach its telemetry adapter, and go live."""
        session = await self.store.get_session(tenant_id, session_id)
        if session is None:
            return None
        if (tenant_id, session_id) in self._services:
            return session
        service = PitwallService(
            self.config,
            tenant_id=tenant_id,
            session_id=session_id,
            store=self.store,
        )
        source = build_source(session.source_kind, self.config)
        await service.initialize([source] if source is not None else [])
        self._services[(tenant_id, session_id)] = service
        inc_sessions(tenant_id)
        session = session.model_copy(
            update={
                "status": SessionStatus.LIVE,
                "started_at": _now(),
                "updated_at": _now(),
            }
        )
        await self.store.save_session(session)
        await self._audit(session, AuditAction.SESSION_STARTED, actor)
        logger.info("pitwall_session_started", tenant=tenant_id, session=session_id)
        return session

    async def end_session(
        self, tenant_id: str, session_id: str, *, actor: str
    ) -> RaceSession | None:
        """Stop the engine and mark the session finished (record retained)."""
        return await self._stop(
            tenant_id,
            session_id,
            SessionStatus.FINISHED,
            AuditAction.SESSION_ENDED,
            actor,
        )

    async def pause_session(
        self, tenant_id: str, session_id: str, *, actor: str
    ) -> RaceSession | None:
        """Suspend ingestion (e.g. red flag) without discarding the session."""
        return await self._stop(
            tenant_id,
            session_id,
            SessionStatus.PAUSED,
            AuditAction.SESSION_PAUSED,
            actor,
        )

    async def _stop(
        self,
        tenant_id: str,
        session_id: str,
        status: SessionStatus,
        action: AuditAction,
        actor: str,
    ) -> RaceSession | None:
        session = await self.store.get_session(tenant_id, session_id)
        if session is None:
            return None
        service = self._services.pop((tenant_id, session_id), None)
        if service is not None:
            await service.shutdown()
            dec_sessions(tenant_id)
        ended = _now() if status is SessionStatus.FINISHED else session.ended_at
        session = session.model_copy(
            update={"status": status, "ended_at": ended, "updated_at": _now()}
        )
        await self.store.save_session(session)
        await self._audit(session, action, actor)
        return session

    async def delete_session(
        self, tenant_id: str, session_id: str, *, actor: str
    ) -> bool:
        """Stop (if live) and delete a session and its derived records."""
        service = self._services.pop((tenant_id, session_id), None)
        if service is not None:
            await service.shutdown()
            dec_sessions(tenant_id)
        session = await self.store.get_session(tenant_id, session_id)
        deleted = await self.store.delete_session(tenant_id, session_id)
        if deleted and session is not None:
            await self._audit(session, AuditAction.SESSION_DELETED, actor)
        return deleted

    # -- reads -------------------------------------------------------------

    def get_service(self, tenant_id: str, session_id: str) -> PitwallService | None:
        """Return the live engine for a session, or None if not running."""
        return self._services.get((tenant_id, session_id))

    async def get_session(self, tenant_id: str, session_id: str) -> RaceSession | None:
        """Fetch a persisted session record."""
        return await self.store.get_session(tenant_id, session_id)

    async def list_sessions(self, tenant_id: str) -> list[RaceSession]:
        """List a tenant's sessions, newest first."""
        return await self.store.list_sessions(tenant_id)

    # -- HITL --------------------------------------------------------------

    async def acknowledge(
        self,
        tenant_id: str,
        session_id: str,
        rec_id: str,
        status: AckStatus,
        *,
        actor: str,
        note: str = "",
    ) -> RecommendationAck | None:
        """Record a strategist's verdict on an emitted recommendation."""
        rec = await self.store.get_recommendation(tenant_id, session_id, rec_id)
        if rec is None:
            return None
        ack = RecommendationAck(
            id=uuid.uuid4().hex,
            tenant_id=tenant_id,
            session_id=session_id,
            recommendation_id=rec_id,
            car_id=rec.car_id,
            status=status,
            actor=actor,
            note=note,
        )
        await self.store.save_ack(ack)
        await self.store.add_audit(
            AuditRecord(
                id=uuid.uuid4().hex,
                tenant_id=tenant_id,
                session_id=session_id,
                actor=actor,
                action=AuditAction.RECOMMENDATION_ACK,
                car_id=rec.car_id,
                detail={"recommendation_id": rec_id, "status": status.value},
            )
        )
        return ack

    # -- internal ----------------------------------------------------------

    async def _audit(
        self, session: RaceSession, action: AuditAction, actor: str
    ) -> None:
        await self.store.add_audit(
            AuditRecord(
                id=uuid.uuid4().hex,
                tenant_id=session.tenant_id,
                session_id=session.id,
                actor=actor,
                action=action,
                detail={"name": session.name, "status": session.status.value},
            )
        )


__all__ = ["PitwallSessionManager", "DEFAULT_SESSION_ID"]
