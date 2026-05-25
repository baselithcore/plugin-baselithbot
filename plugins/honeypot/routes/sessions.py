"""Session endpoints for Honeypot API.

Provides endpoints for managing attacker sessions and logs.
"""

from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models import HoneypotSession, SessionListResponse
from ..dependencies import get_coordinator_dependency

if TYPE_CHECKING:
    from ..swarm.coordinator import HoneypotSwarmCoordinator

router = APIRouter()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    active_only: bool = Query(False, description="Show only active sessions"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    from_db: bool = Query(True, description="Query sessions from database"),
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get list of attacker sessions."""

    if from_db:
        items, total = await coordinator.get_historical_sessions(
            active_only=active_only,
            page=page,
            page_size=page_size,
            protocol=protocol,
        )
        # If showing active only, total is the active count
        if active_only:
            active = total
        else:
            # Fallback to in-memory count for performance
            # (getting accurate DB active count would require another query)
            active = len(
                [s for s in coordinator._sessions.values() if s.ended_at is None]
            )

    else:
        sessions = coordinator.get_sessions(
            protocol=protocol,
            active_only=active_only,
        )

        # Paginate manually (sessions are usually fewer)
        total = len(sessions)
        start = (page - 1) * page_size
        end = start + page_size
        items = sessions[start:end]
        active = len([s for s in sessions if s.ended_at is None])

    return SessionListResponse(
        items=items,
        total=total,
        active=active,
    )


@router.get("/sessions/{session_id}", response_model=HoneypotSession)
async def get_session(
    session_id: str,
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get details of a specific session."""
    session = await coordinator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


@router.post("/sessions/{session_id}/analyze")
async def analyze_session(
    session_id: str,
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Trigger AI analysis for a session."""
    result = await coordinator.analyze_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return result
