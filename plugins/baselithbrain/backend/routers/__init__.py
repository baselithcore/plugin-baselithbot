"""FastAPI routers for the BaselithBrain backend."""

from .ai_router import router as ai_router
from .assets_router import router as assets_router
from .backlinks_router import router as backlinks_router
from .conversations_router import router as conversations_router
from .daily_router import router as daily_router
from .export_router import router as export_router
from .graph_router import router as graph_router
from .health import router as health_router
from .history_router import router as history_router
from .mcp_router import router as mcp_router
from .notes_router import router as notes_router
from .search_router import router as search_router
from .tags_router import router as tags_router
from .templates_router import router as templates_router
from .trash_router import router as trash_router
from .workspaces_router import router as workspaces_router

__all__ = [
    "ai_router",
    "assets_router",
    "backlinks_router",
    "conversations_router",
    "daily_router",
    "export_router",
    "graph_router",
    "health_router",
    "history_router",
    "mcp_router",
    "notes_router",
    "search_router",
    "tags_router",
    "templates_router",
    "trash_router",
    "workspaces_router",
]
