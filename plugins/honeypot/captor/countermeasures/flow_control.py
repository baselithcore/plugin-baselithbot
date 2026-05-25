"""Flow Control Countermeasures for Honeypot Plugin.

Implements flow control strategies per HoneyDOC Section IV-C2a.
Traffic can be blocked, discarded, redirected, or isolated.
"""

from core.observability.logging import get_logger
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

logger = get_logger(__name__)


@dataclass
class BlockEntry:
    """Entry for blocked IP/session."""

    target: str  # IP or session ID
    reason: str
    blocked_at: datetime
    expires_at: Optional[datetime] = None
    block_type: str = "ip"  # ip, session, network


@dataclass
class RedirectEntry:
    """Entry for redirected session."""

    session_id: str
    from_honeypot: str
    to_honeypot: str
    redirected_at: datetime
    reason: str


class FlowController:
    """Flow control manager per HoneyDOC countermeasures.

    Provides:
    - IP/session blocking with expiration
    - Session redirection to HIH
    - Session isolation for containment
    """

    def __init__(self):
        """Initialize flow controller."""
        self._blocked_entries: Dict[str, BlockEntry] = {}
        self._redirects: Dict[str, RedirectEntry] = {}
        self._isolated_sessions: Set[str] = set()

        logger.info("FlowController initialized")

    def block_ip(
        self,
        ip: str,
        reason: str = "",
        duration_seconds: Optional[int] = None,
    ) -> BlockEntry:
        """Block an IP address.

        Args:
            ip: IP address to block
            reason: Reason for blocking
            duration_seconds: Optional block duration (None = permanent)

        Returns:
            Block entry created
        """
        now = datetime.now(timezone.utc)
        expires_at = None
        if duration_seconds:
            expires_at = now + timedelta(seconds=duration_seconds)

        entry = BlockEntry(
            target=ip,
            reason=reason,
            blocked_at=now,
            expires_at=expires_at,
            block_type="ip",
        )
        self._blocked_entries[f"ip:{ip}"] = entry
        logger.info(f"Blocked IP {ip}: {reason}")
        return entry

    def block_session(
        self,
        session_id: str,
        reason: str = "",
        duration_seconds: Optional[int] = None,
    ) -> BlockEntry:
        """Block a session.

        Args:
            session_id: Session to block
            reason: Reason for blocking
            duration_seconds: Optional block duration

        Returns:
            Block entry created
        """
        now = datetime.now(timezone.utc)
        expires_at = None
        if duration_seconds:
            expires_at = now + timedelta(seconds=duration_seconds)

        entry = BlockEntry(
            target=session_id,
            reason=reason,
            blocked_at=now,
            expires_at=expires_at,
            block_type="session",
        )
        self._blocked_entries[f"session:{session_id}"] = entry
        logger.info(f"Blocked session {session_id}: {reason}")
        return entry

    def is_blocked(self, target: str, target_type: str = "ip") -> bool:
        """Check if target is blocked.

        Args:
            target: IP or session ID
            target_type: Type of target (ip or session)

        Returns:
            True if blocked
        """
        key = f"{target_type}:{target}"
        if key not in self._blocked_entries:
            return False

        entry = self._blocked_entries[key]

        # Check expiration
        if entry.expires_at:
            if datetime.now(timezone.utc) > entry.expires_at:
                del self._blocked_entries[key]
                logger.debug(f"Block expired for {target}")
                return False

        return True

    def unblock(self, target: str, target_type: str = "ip") -> bool:
        """Unblock a target.

        Args:
            target: IP or session ID
            target_type: Type of target

        Returns:
            True if unblocked
        """
        key = f"{target_type}:{target}"
        if key in self._blocked_entries:
            del self._blocked_entries[key]
            logger.info(f"Unblocked {target_type} {target}")
            return True
        return False

    def redirect_session(
        self,
        session_id: str,
        from_honeypot: str,
        to_honeypot: str,
        reason: str = "",
    ) -> RedirectEntry:
        """Redirect session to another honeypot.

        Per HoneyDOC: redirect interesting traffic to HIH for deep analysis.

        Args:
            session_id: Session to redirect
            from_honeypot: Source honeypot ID
            to_honeypot: Target honeypot ID (typically HIH)
            reason: Reason for redirect

        Returns:
            Redirect entry created
        """
        entry = RedirectEntry(
            session_id=session_id,
            from_honeypot=from_honeypot,
            to_honeypot=to_honeypot,
            redirected_at=datetime.now(timezone.utc),
            reason=reason,
        )
        self._redirects[session_id] = entry
        logger.info(
            f"Redirected session {session_id} from {from_honeypot} to {to_honeypot}"
        )
        return entry

    def get_redirect_target(self, session_id: str) -> Optional[str]:
        """Get redirect target for session.

        Args:
            session_id: Session to check

        Returns:
            Target honeypot ID or None
        """
        if session_id in self._redirects:
            return self._redirects[session_id].to_honeypot
        return None

    def isolate_session(self, session_id: str, reason: str = "") -> None:
        """Isolate a session (containment).

        Per HoneyDOC: limit outbound to prevent attacking non-honeypot systems.

        Args:
            session_id: Session to isolate
            reason: Reason for isolation
        """
        self._isolated_sessions.add(session_id)
        logger.info(f"Isolated session {session_id}: {reason}")

    def is_isolated(self, session_id: str) -> bool:
        """Check if session is isolated.

        Args:
            session_id: Session to check

        Returns:
            True if isolated
        """
        return session_id in self._isolated_sessions

    def release_isolation(self, session_id: str) -> bool:
        """Release session from isolation.

        Args:
            session_id: Session to release

        Returns:
            True if released
        """
        if session_id in self._isolated_sessions:
            self._isolated_sessions.discard(session_id)
            logger.info(f"Released session {session_id} from isolation")
            return True
        return False

    def get_blocked_entries(self) -> List[BlockEntry]:
        """Get all active block entries.

        Returns:
            List of block entries
        """
        # Clean up expired entries
        now = datetime.now(timezone.utc)
        expired = [
            k
            for k, v in self._blocked_entries.items()
            if v.expires_at and now > v.expires_at
        ]
        for key in expired:
            del self._blocked_entries[key]

        return list(self._blocked_entries.values())

    def get_redirects(self) -> List[RedirectEntry]:
        """Get all active redirects.

        Returns:
            List of redirect entries
        """
        return list(self._redirects.values())

    def get_isolated_sessions(self) -> Set[str]:
        """Get isolated session IDs.

        Returns:
            Set of isolated session IDs
        """
        return self._isolated_sessions.copy()

    def get_stats(self) -> Dict[str, int]:
        """Get flow control statistics.

        Returns:
            Stats dictionary
        """
        return {
            "blocked_ips": len(
                [e for e in self._blocked_entries.values() if e.block_type == "ip"]
            ),
            "blocked_sessions": len(
                [e for e in self._blocked_entries.values() if e.block_type == "session"]
            ),
            "active_redirects": len(self._redirects),
            "isolated_sessions": len(self._isolated_sessions),
        }

    def clear(self) -> None:
        """Clear all flow control state."""
        self._blocked_entries.clear()
        self._redirects.clear()
        self._isolated_sessions.clear()
        logger.info("FlowController cleared")
