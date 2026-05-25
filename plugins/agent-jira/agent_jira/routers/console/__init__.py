from __future__ import annotations

import inspect

from fastapi import APIRouter, Depends, Request


async def _require_console_user(request: Request) -> str:
    from agent_jira.security import require_user

    dependency = request.app.dependency_overrides.get(require_user, require_user)
    try:
        result = dependency(request)
    except TypeError:
        result = dependency()
    if inspect.isawaitable(result):
        return await result
    return result


router = APIRouter(
    prefix="/console", tags=["console"], dependencies=[Depends(_require_console_user)]
)

public_router = APIRouter(prefix="/console", tags=["console"])


# Import delle route per la registrazione lato FastAPI
from . import (  # noqa: E402,F401
    admin_routes,
    analysis,
    frontend,
    jira_routes,
    jira_settings,
    kb,
)

__all__ = ["router", "public_router"]
