"""Honeypot API Router.

REST API endpoints for the Honeypot dashboard.

This module aggregates domain-specific route modules:
- status: Service status and control
- honeypots: Honeypot registry
- events: Attack events
- attackers: Aggregated attacker data for visualization
- sessions: Attacker sessions
- learning: Learning & feedback
- memory: IP reputation & patterns
- geo: GeoIP & visualization
- mcp: Prompt injection analysis
- stream: Real-time SSE streaming
- pentest: Threat-informed pentesting
- discovery: Botnet detection and network discovery
- reports: Security report generation (PDF/Markdown)
"""

from fastapi import APIRouter, Depends

from core.auth import AuthRole
from plugins.auth.dependencies import require_roles

from .routes import (
    analytics,
    attackers,
    discovery,
    events,
    geo,
    honeypots,
    learning,
    logs,
    mcp,
    memory,
    pentest,
    reports,
    sessions,
    sinkhole,
    sinkhole_ws,
    status,
    stream,
    notifications,
)
from .dependencies import get_coordinator_dependency

# Export coordinator dependency for route usage
__all__ = [
    "create_router",
    "get_coordinator_dependency",
]


# Authenticating dependencies. Honeypot data is deployment-level security-ops
# intel (attacker captures), not per-tenant customer data — restricted to
# admins so non-admin tenant users never read another deployment's threat data.
_deps = [Depends(require_roles(AuthRole.ADMIN))]


def create_router() -> APIRouter:
    """Create Honeypot API router.

    Aggregates all domain-specific routers into a single router
    with the /api/honeypot prefix.

    Returns:
        Configured APIRouter with all honeypot endpoints
    """
    router = APIRouter(
        prefix="",
        tags=["honeypot"],
        dependencies=_deps,
    )

    # Include domain-specific routers
    router.include_router(status.router)
    router.include_router(honeypots.router)
    router.include_router(events.router)
    router.include_router(attackers.router)
    router.include_router(sessions.router)
    router.include_router(learning.router)
    router.include_router(memory.router)
    router.include_router(geo.router)
    router.include_router(mcp.router)
    router.include_router(stream.router)
    router.include_router(logs.router)
    router.include_router(pentest.pentest_router)
    router.include_router(discovery.router)
    router.include_router(sinkhole.router)
    router.include_router(sinkhole_ws.router)
    router.include_router(reports.router)
    router.include_router(notifications.router)
    router.include_router(analytics.router)

    return router
