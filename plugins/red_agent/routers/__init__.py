"""Red Agent FastAPI routers."""

from plugins.red_agent.routers.activity import router as activity_router
from plugins.red_agent.routers.agents import router as agents_router
from plugins.red_agent.routers.approve import router as approve_router
from plugins.red_agent.routers.autopr import router as autopr_router
from plugins.red_agent.routers.engagements import router as engagements_router
from plugins.red_agent.routers.file_scan import router as file_scan_router
from plugins.red_agent.routers.findings import router as findings_router
from plugins.red_agent.routers.graph import router as graph_router
from plugins.red_agent.routers.graph_chat import router as graph_chat_router
from plugins.red_agent.routers.health import router as health_router
from plugins.red_agent.routers.playbooks import router as playbooks_router
from plugins.red_agent.routers.preflight import router as preflight_router
from plugins.red_agent.routers.reports import router as reports_router
from plugins.red_agent.routers.scan import router as scan_router
from plugins.red_agent.routers.settings import router as settings_router
from plugins.red_agent.routers.targets import router as targets_router
from plugins.red_agent.routers.triage import router as triage_router
from plugins.red_agent.routers.webhooks import router as webhooks_router
from plugins.red_agent.routers.ws import router as ws_router

__all__ = [
    "activity_router",
    "agents_router",
    "engagements_router",
    "file_scan_router",
    "scan_router",
    "findings_router",
    "graph_router",
    "graph_chat_router",
    "ws_router",
    "reports_router",
    "preflight_router",
    "playbooks_router",
    "settings_router",
    "approve_router",
    "targets_router",
    "triage_router",
    "health_router",
    "webhooks_router",
    "autopr_router",
]
