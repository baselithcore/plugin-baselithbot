"""
Sigillum sacramentale — privacy enforcement.

The seal of confession (CCC §1467) is inviolable. This module:

- Holds session state in process memory only (no DB, no LTM, no Redis).
- Never serializes penitent utterances to logs, Sentry, traces, or
  metrics. Only phase transitions are logged, never content.
- Wipes session state on close. The session_id is opaque (uuid4) and
  has no link to user identity.

If you are reading this and considering adding persistence: do not.
The whole plugin is built around this invariant.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from core.observability.logging import get_logger

from .models import RitePhase, SessionState

logger = get_logger(__name__)


class SigillumStore:
    """Thread-safe in-memory session store with sigillum guarantees."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    async def create(self) -> SessionState:
        """Create a fresh session with an opaque id."""
        session_id = str(uuid4())
        state = SessionState(session_id=session_id)
        async with self._lock:
            self._sessions[session_id] = state
        # Log phase only — never content. Session id is opaque.
        logger.info("confessgpt_session_open", session_id=session_id)
        return state

    async def get(self, session_id: str) -> SessionState | None:
        """Fetch state. Returns None if unknown or already closed."""
        async with self._lock:
            return self._sessions.get(session_id)

    async def update(self, state: SessionState) -> None:
        """Replace state atomically."""
        async with self._lock:
            if state.session_id in self._sessions:
                self._sessions[state.session_id] = state

    async def close(self, session_id: str) -> None:
        """Wipe session state — sigillum enforcement.

        After close the session_id resolves to nothing. Even if the
        operator dumps the process the dict no longer holds it.
        """
        async with self._lock:
            self._sessions.pop(session_id, None)
        logger.info("confessgpt_session_close", session_id=session_id)

    async def close_all(self) -> None:
        """Wipe every active session — called on plugin shutdown."""
        async with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
        logger.info("confessgpt_sessions_wipe", count=count)

    def is_closed(self, session_id: str) -> bool:
        """True if the session is no longer present (closed or never opened)."""
        return session_id not in self._sessions


def is_terminal(phase: RitePhase) -> bool:
    """Return True for phases that end the rite."""
    return phase in (RitePhase.CONGEDO, RitePhase.INVITO_RIFLESSIONE)
