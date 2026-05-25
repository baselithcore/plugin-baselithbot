"""Event and session query methods for HoneypotSwarmCoordinator.

Handles database queries for events and sessions with filtering,
pagination, and historical data retrieval.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..models import HoneypotSession

if TYPE_CHECKING:
    from .coordinator import HoneypotSwarmCoordinator


class EventQueriesMixin:
    """Mixin providing event and session query capabilities."""

    async def get_events(
        self: "HoneypotSwarmCoordinator",
        page: int = 1,
        page_size: int = 50,
        protocol: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        source_ip: Optional[str] = None,
        honeypot_id: Optional[str] = None,
        country: Optional[str] = None,
        is_bot: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Get paginated events from database with optional filtering."""
        from ..persistence import HoneypotDAO

        # Fetch events from DB (async)
        events, total = await HoneypotDAO.get_events(
            page=page,
            page_size=page_size,
            honeypot_id=honeypot_id,
            protocol=protocol,
            severity=severity,
            category=category,
            source_ip=source_ip,
            country=country,
            is_bot=is_bot,
        )

        return {
            "items": events,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def get_event(self: "HoneypotSwarmCoordinator", event_id: str) -> Optional[Any]:
        """Get event by ID from memory."""
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

    async def get_event_full(
        self: "HoneypotSwarmCoordinator", event_id: str
    ) -> Optional[Any]:
        """Get event by ID from memory, falling back to database.

        Args:
            event_id: Event ID to retrieve

        Returns:
            AttackEvent or None
        """
        # 1. Try memory (fast, sync)
        event = self.get_event(event_id)
        if event:
            return event

        # 2. Fallback to DB if event not in buffer
        try:
            from ..persistence import HoneypotDAO

            return await HoneypotDAO.get_event_by_id(event_id)
        except Exception as e:
            print(f"[WARN] Failed to fetch event {event_id} from DB: {e}")
            return None

    async def get_historical_sessions(
        self: "HoneypotSwarmCoordinator",
        honeypot_id: Optional[str] = None,
        active_only: bool = False,
        page: int = 1,
        page_size: int = 100,
        protocol: Optional[str] = None,
    ) -> tuple[List[HoneypotSession], int]:
        """Get historical sessions from database.

        Args:
            honeypot_id: Optional filter
            active_only: Only return active sessions
            page: Page number
            page_size: Items per page
            protocol: Optional filter by protocol

        Returns:
            Tuple of (List of sessions, total count)
        """
        from ..persistence import HoneypotDAO

        return await HoneypotDAO.get_sessions(
            honeypot_id=honeypot_id,
            active_only=active_only,
            page=page,
            page_size=page_size,
            protocol=protocol,
        )

    def get_sessions(
        self: "HoneypotSwarmCoordinator",
        protocol: Optional[str] = None,
        active_only: bool = False,
    ) -> List[HoneypotSession]:
        """Get filtered sessions from memory."""
        sessions = list(self._sessions.values())

        if protocol:
            sessions = [s for s in sessions if s.protocol.value == protocol]

        if active_only:
            sessions = [s for s in sessions if s.ended_at is None]

        # Sort by last activity desc (normalize to UTC to avoid naive/aware comparison)
        def _normalize_ts(ts: Optional[datetime]) -> datetime:
            if ts is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

        sessions.sort(
            key=lambda x: _normalize_ts(x.last_activity or x.started_at), reverse=True
        )

        return sessions

    async def get_session(
        self: "HoneypotSwarmCoordinator", session_id: str
    ) -> Optional[HoneypotSession]:
        """Get session by ID (from memory or DB)."""
        # Try memory first
        session = self._sessions.get(session_id)
        if session:
            return session

        # Fallback to DB
        from ..persistence import HoneypotDAO

        return await HoneypotDAO.get_session_by_id(session_id)


__all__ = ["EventQueriesMixin"]
