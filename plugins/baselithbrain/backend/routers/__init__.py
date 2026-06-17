"""FastAPI routers for the BaselithBrain backend."""

from .ai_router import router as ai_router
from .assets_router import router as assets_router
from .conversations_router import router as conversations_router
from .graph_router import router as graph_router
from .health import router as health_router
from .mcp_router import router as mcp_router
from .notes_router import router as notes_router
from .search_router import router as search_router
from .workspaces_router import router as workspaces_router

__all__ = [
    "ai_router",
    "assets_router",
    "conversations_router",
    "graph_router",
    "health_router",
    "mcp_router",
    "notes_router",
    "search_router",
    "workspaces_router",
]
