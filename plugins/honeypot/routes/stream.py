"""Real-time streaming endpoints for Honeypot API.

Provides SSE streaming, swarm status, and correlation endpoints.
"""

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from ..models import CVECorrelationListResponse
from ..dependencies import get_coordinator_dependency

if TYPE_CHECKING:
    from ..swarm.coordinator import HoneypotSwarmCoordinator

router = APIRouter()


@router.get("/stream/attacks")
async def stream_attacks(include_history: bool = Query(True)):
    """Stream attack events in real-time via SSE.

    This endpoint provides Server-Sent Events for live attack visualization.
    Connect with EventSource in the browser for real-time updates.
    """
    from ..stream import attack_event_generator, get_stream_manager

    manager = get_stream_manager()
    queue = manager.subscribe()

    return StreamingResponse(
        attack_event_generator(queue, include_history=include_history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/status")
async def get_stream_status():
    """Get streaming service status."""
    from ..stream import get_stream_manager

    manager = get_stream_manager()
    return {
        "subscribers": manager.subscriber_count,
        "history_size": len(manager.get_history()),
    }


@router.delete("/stream/history")
async def clear_stream_history():
    """Clear broadcast history."""
    from ..stream import get_stream_manager

    manager = get_stream_manager()
    manager.clear_history()
    return {"status": "cleared", "message": "Stream history cleared"}


@router.get("/swarm/status")
async def get_swarm_status(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get honeypot swarm handler activity status.

    Returns activity data for each handler for swarm graph visualization.
    """

    # Get handler activity from stats
    stats = coordinator.get_stats()
    status = coordinator.get_status()

    # Build handler activity data
    handlers = {
        "ssh_handler": {
            "active": status.ssh_enabled,
            "events": stats.protocol_breakdown.get("ssh", 0),
            "sessions": 0,
        },
        "http_handler": {
            "active": status.http_enabled,
            "events": stats.protocol_breakdown.get("http", 0),
            "sessions": 0,
        },
        "tcp_handler": {
            "active": True,  # TCP is always listening
            "events": stats.protocol_breakdown.get("tcp", 0),
            "sessions": 0,
        },
        "correlator": {
            "active": True,
            "events": stats.cve_correlations,
            "sessions": 0,
        },
        "responder": {
            "active": True,
            "events": stats.total_events,  # Responds to all
            "sessions": stats.active_sessions,
        },
        "coordinator": {
            "active": status.is_running,
            "events": stats.total_events,
            "sessions": stats.total_sessions,
        },
    }

    # Get active session counts per protocol
    sessions = coordinator.get_sessions(active_only=True)
    for session in sessions:
        protocol = (
            session.protocol.value
            if hasattr(session.protocol, "value")
            else str(session.protocol)
        )
        handler_key = f"{protocol}_handler"
        if handler_key in handlers:
            handlers[handler_key]["sessions"] += 1

    return {
        "handlers": handlers,
        "total_events": stats.total_events,
        "active_sessions": stats.active_sessions,
        "is_running": status.is_running,
    }


@router.get("/cve-correlations", response_model=CVECorrelationListResponse)
async def get_cve_correlations(
    limit: int = Query(50, ge=1, le=200),
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get attack-to-CVE correlations."""
    correlations = coordinator.get_cve_correlations(limit=limit)
    unique_cves = len(set(c.cve_id for c in correlations))

    return CVECorrelationListResponse(
        items=correlations,
        total=len(correlations),
        unique_cves=unique_cves,
    )


@router.get("/cve-correlations/enriched")
async def get_enriched_cve_correlations(
    limit: int = Query(50, ge=1, le=200),
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get attack-to-CVE correlations with enriched CVE details from CVE Hunter.

    This endpoint combines honeypot attack correlations with detailed CVE data
    from the CVE Hunter plugin, providing a comprehensive view of vulnerabilities
    being exploited in real-time.
    """
    import httpx
    from typing import List, Dict, Any

    correlations = coordinator.get_cve_correlations(limit=limit)

    # Extract unique CVE IDs
    cve_ids = list(
        set(cve_id for corr in correlations for cve_id in corr.get("matched_cves", []))
    )

    # Fetch CVE details from CVE Hunter
    enriched_data: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        for cve_id in cve_ids[:20]:  # Limit to 20 CVEs to avoid timeout
            cve_detail = None
            try:
                response = await client.get(
                    f"http://localhost:8000/api/cve_hunter/cves/{cve_id}"
                )
                if response.status_code == 200:
                    cve_detail = response.json()
            except Exception:
                pass

            # Fallback if CVE details could not be fetched
            if not cve_detail:
                cve_detail = {
                    "cve_id": cve_id,
                    "title": "Details Unavailable",
                    "description": "Could not retrieve details from CVE Hunter.",
                    "severity": "unknown",
                    "cvss": None,
                    "affected_products": [],
                    "references": [],
                    "published_date": None,
                    "exploit_available": False,
                    "patch_available": False,
                    "ai_summary": None,
                    "cwe_ids": [],
                    "source": "honeypot_only",
                }

            # Find correlations for this CVE
            related_attacks = [
                {
                    "event_id": c.get("event_id"),
                    "category": c.get("category"),
                    "confidence": c.get("confidence"),
                    "timestamp": c.get("timestamp"),
                    "source_ip": c.get("source_ip"),
                }
                for c in correlations
                if cve_id in c.get("matched_cves", [])
            ]

            if related_attacks:
                enriched_data.append(
                    {
                        "cve_id": cve_id,
                        "cve_detail": cve_detail,
                        "attack_count": len(related_attacks),
                        "related_attacks": related_attacks[:5],  # Top 5 recent
                    }
                )

    return {
        "items": enriched_data,
        "total": len(enriched_data),
        "total_correlations": len(correlations),
        "unique_cves": len(cve_ids),
    }


@router.get("/top-attackers")
async def get_top_attackers(
    limit: int = Query(10, ge=1, le=50),
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get top attacker IPs."""
    return coordinator.get_top_attackers(limit=limit)
