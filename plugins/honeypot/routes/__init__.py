"""Routes package for Honeypot API.

Provides domain-specific route modules for the Honeypot REST API.

Modules:
- status: Service status and control endpoints
- honeypots: Honeypot registry endpoints
- events: Attack event endpoints
- sessions: Session endpoints
- learning: Learning & feedback endpoints
- memory: Memory/reputation endpoints
- geo: GeoIP endpoints
- mcp: MCP/Prompt injection endpoints
- stream: Real-time streaming endpoints
- pentest: Threat-informed pentesting endpoints
- discovery: Botnet detection and network discovery endpoints
"""

# Dependency injection for route handlers
from ..dependencies import get_coordinator_dependency

__all__ = [
    "get_coordinator_dependency",
]
