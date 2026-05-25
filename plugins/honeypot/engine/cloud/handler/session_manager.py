"""Cloud Handler - Session Management.

Centralized session management for CloudManagementHandler.
Extracted to keep cloud_handler.py under 500 LOC.
"""

from core.observability.logging import get_logger
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from aiohttp import web

from ..models import CloudProvider, CloudSession, SessionState
from ..protocols import GeoIPServiceProtocol
from ..state_machine import SessionStateMachine

logger = get_logger(__name__)


class CloudSessionManager:
    """Manages cloud honeypot sessions and state machines.

    Supports dependency injection for GeoIP service.
    """

    def __init__(
        self,
        honeypot_id: str,
        provider: CloudProvider,
        max_auth_attempts: int = 5,
        session_timeout_minutes: int = 30,
        on_state_change: Optional[Callable] = None,
        geoip_service: Optional[GeoIPServiceProtocol] = None,
    ):
        """Initialize session manager.

        Args:
            honeypot_id: Honeypot instance identifier
            provider: Cloud provider type
            max_auth_attempts: Max failed auth before blocking
            session_timeout_minutes: Session inactivity timeout
            on_state_change: Callback for state transitions
            geoip_service: Optional GeoIP service for IP enrichment
        """
        self.honeypot_id = honeypot_id
        self.provider = provider
        self.max_auth_attempts = max_auth_attempts
        self.session_timeout_minutes = session_timeout_minutes
        self.on_state_change = on_state_change
        self._geoip_service = geoip_service

        # Session storage (keyed by source IP)
        self._sessions: Dict[str, CloudSession] = {}
        self._state_machines: Dict[str, SessionStateMachine] = {}

    def get_or_create_session(
        self,
        source_ip: str,
        source_port: int = 0,
        request: Optional[web.Request] = None,
    ) -> CloudSession:
        """Get existing session or create new one.

        Args:
            source_ip: Source IP address
            source_port: Source port
            request: Optional HTTP request for metadata

        Returns:
            CloudSession instance
        """
        session_key = source_ip

        if session_key not in self._sessions:
            session = self._create_session(source_ip, source_port)
            self._sessions[session_key] = session

            logger.info(f"New cloud session: {session.session_id} from {source_ip}")

        return self._sessions[session_key]

    def _create_session(
        self,
        source_ip: str,
        source_port: int,
    ) -> CloudSession:
        """Create a new session with state machine.

        Args:
            source_ip: Source IP address
            source_port: Source port

        Returns:
            New CloudSession
        """
        session_id = self._generate_session_id()

        session = CloudSession(
            session_id=session_id,
            honeypot_id=self.honeypot_id,
            provider=self.provider,
            source_ip=source_ip,
            source_port=source_port,
        )

        # Enrich session with geolocation data
        if self._geoip_service:
            try:
                self._geoip_service.enrich_session(session)
                if session.geo_country:
                    logger.debug(
                        f"Session {session_id}: GeoIP enriched - "
                        f"{session.geo_country}/{session.geo_city} ASN:{session.asn}"
                    )
            except Exception as e:
                logger.warning(f"GeoIP enrichment failed for {source_ip}: {e}")

        state_machine = SessionStateMachine(
            session=session,
            max_auth_attempts=self.max_auth_attempts,
            session_timeout_minutes=self.session_timeout_minutes,
            on_state_change=self.on_state_change,
        )

        self._state_machines[session_id] = state_machine

        return session

    def _generate_session_id(self) -> str:
        """Generate unique session identifier."""
        return f"cloud-{uuid.uuid4().hex[:16]}"

    def get_session(self, session_id: str) -> Optional[CloudSession]:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            CloudSession or None
        """
        for session in self._sessions.values():
            if session.session_id == session_id:
                return session
        return None

    def get_session_by_ip(self, source_ip: str) -> Optional[CloudSession]:
        """Get session by source IP.

        Args:
            source_ip: Source IP address

        Returns:
            CloudSession or None
        """
        return self._sessions.get(source_ip)

    def get_state_machine(self, session_id: str) -> Optional[SessionStateMachine]:
        """Get state machine for session.

        Args:
            session_id: Session identifier

        Returns:
            SessionStateMachine or None
        """
        return self._state_machines.get(session_id)

    def get_active_sessions(self) -> List[CloudSession]:
        """Get all non-terminal sessions.

        Returns:
            List of active CloudSession instances
        """
        return [
            s
            for s in self._sessions.values()
            if s.current_state not in (SessionState.BLOCKED, SessionState.EXPIRED)
        ]

    def get_all_sessions(self) -> List[CloudSession]:
        """Get all sessions.

        Returns:
            List of all CloudSession instances
        """
        return list(self._sessions.values())

    async def end_session(
        self,
        session_id: str,
        reason: str = "manual",
        callback: Optional[Callable] = None,
    ) -> None:
        """End a session.

        Args:
            session_id: Session identifier
            reason: Reason for ending session
            callback: Optional callback to invoke after ending
        """
        state_machine = self._state_machines.get(session_id)
        if state_machine:
            state_machine.end_session(reason)

            if callback:
                session = self.get_session(session_id)
                if session:
                    await callback(session)

    async def end_all_sessions(
        self,
        reason: str = "shutdown",
        callback: Optional[Callable] = None,
    ) -> None:
        """End all active sessions.

        Args:
            reason: Reason for ending sessions
            callback: Optional callback per session
        """
        for session_id in list(self._state_machines.keys()):
            await self.end_session(session_id, reason, callback)

    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Remove expired sessions older than max_age.

        Args:
            max_age_hours: Maximum session age in hours

        Returns:
            Number of sessions removed
        """
        now = datetime.now(timezone.utc)
        removed = 0

        for ip, session in list(self._sessions.items()):
            if session.current_state in (SessionState.BLOCKED, SessionState.EXPIRED):
                age = (now - session.started_at).total_seconds() / 3600
                if age > max_age_hours:
                    del self._sessions[ip]
                    self._state_machines.pop(session.session_id, None)
                    removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} expired sessions")

        return removed

    def get_statistics(self) -> Dict:
        """Get session statistics.

        Returns:
            Dictionary with session statistics
        """
        sessions = list(self._sessions.values())

        states = {}
        for session in sessions:
            state = session.current_state.value
            states[state] = states.get(state, 0) + 1

        return {
            "total_sessions": len(sessions),
            "active_sessions": len(self.get_active_sessions()),
            "sessions_by_state": states,
            "unique_ips": len(set(s.source_ip for s in sessions)),
        }
