"""BaselithBrain FastAPI application.

Self-contained second-brain API: routers wired at canonical absolute paths so
the app runs standalone *and* mounts cleanly under ``/baselithbrain`` (Starlette
strips the prefix). The lifespan builds the derived index from the vault; until
it completes, data endpoints answer from an empty-but-valid index and ``/healthz``
reports ``warming``.

Seeds a few starter notes into an empty vault on first run so the SPA always has
something to render (a real "second brain" feel out of the box).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .index_state import get_index
from .routers import (
    ai_router,
    assets_router,
    conversations_router,
    graph_router,
    health_router,
    mcp_router,
    notes_router,
    search_router,
    workspaces_router,
)
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    idx = get_index()
    idx.workspaces.ensure_default()
    seed_if_empty(idx.notes)
    await idx.rebuild()
    yield


app = FastAPI(title="BaselithBrain API", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(notes_router)
app.include_router(search_router)
app.include_router(graph_router)
app.include_router(mcp_router)
app.include_router(assets_router)
app.include_router(ai_router)
app.include_router(conversations_router)
app.include_router(workspaces_router)
