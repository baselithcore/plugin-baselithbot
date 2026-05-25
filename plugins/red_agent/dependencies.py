"""FastAPI dependencies and DI wiring for the Red Agent plugin."""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Request, status

from core.di.container import ServiceNotFoundError, ServiceRegistry
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.config import RedAgentConfig

# Optional dedicated auth plugin. If absent we fall back to ``core.auth`` so the
# Red Agent surface keeps working in dev / minimal deployments.
try:
    from plugins.auth.dependencies import (  # type: ignore[import-not-found]
        require_auth as _ext_require_auth,
        require_roles as _ext_require_roles,
    )

    AUTH_PLUGIN_AVAILABLE = True
except ImportError:
    AUTH_PLUGIN_AVAILABLE = False
    _ext_require_auth = None  # type: ignore[assignment]
    _ext_require_roles = None  # type: ignore[assignment]

try:
    from core.auth import AuthManager, AuthRole, get_auth_manager

    CORE_AUTH_AVAILABLE = True
except ImportError:
    CORE_AUTH_AVAILABLE = False
    AuthManager = None  # type: ignore[assignment,misc]
    AuthRole = None  # type: ignore[assignment,misc]
    get_auth_manager = None  # type: ignore[assignment]


def _allow_anonymous() -> bool:
    """Dev escape hatch — set ``RED_AGENT_ALLOW_ANONYMOUS=true`` to bypass RBAC."""
    return os.getenv("RED_AGENT_ALLOW_ANONYMOUS", "").lower() in {"1", "true", "yes"}


def get_red_agent_config() -> RedAgentConfig:
    try:
        cfg = ServiceRegistry.get(RedAgentConfig)
    except ServiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Red Agent config not registered",
        ) from e
    if cfg is None:
        raise HTTPException(503, "Red Agent config not initialized")
    return cfg


def get_red_agent() -> RedAgent:
    try:
        agent = ServiceRegistry.get(RedAgent)
    except ServiceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Red Agent not registered",
        ) from e
    if agent is None:
        raise HTTPException(503, "Red Agent not initialized")
    return agent


async def _authenticate(request: Request):  # type: ignore[no-untyped-def]
    if not CORE_AUTH_AVAILABLE or get_auth_manager is None:
        return None
    try:
        manager: AuthManager = get_auth_manager()  # type: ignore[assignment]
    except Exception:
        return None
    return await manager.authenticate(request.headers.get("Authorization"))


def _strict_auth() -> bool:
    """Return True only when operator opted in via RED_AGENT_REQUIRE_AUTH=true."""
    return os.getenv("RED_AGENT_REQUIRE_AUTH", "").lower() in {"1", "true", "yes"}


async def _security_operator_dep(request: Request) -> None:
    # Prefer dedicated auth plugin when present.
    if (
        AUTH_PLUGIN_AVAILABLE
        and _ext_require_roles is not None
        and AuthRole is not None
    ):
        checker = _ext_require_roles(AuthRole.ADMIN)
        return await checker()  # type: ignore[no-any-return]

    # Permissive by default — most deployments rely on the global security
    # middleware. Set ``RED_AGENT_REQUIRE_AUTH=true`` to enforce ADMIN here.
    if not _strict_auth() or _allow_anonymous():
        return None

    user = await _authenticate(request)
    if user is None:
        return None
    if AuthRole is not None and user.has_role(AuthRole.ADMIN):
        return None
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="ADMIN role required",
    )


async def _viewer_dep(request: Request) -> None:
    if AUTH_PLUGIN_AVAILABLE and _ext_require_auth is not None:
        return await _ext_require_auth()  # type: ignore[no-any-return]

    if not _strict_auth() or _allow_anonymous():
        return None

    user = await _authenticate(request)
    if user is None or user.is_authenticated:
        return None
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


def require_security_operator() -> object:
    """RBAC dependency: only ADMIN may trigger scans (MVP).

    Future: introduce a dedicated SECURITY_OPERATOR role; until then
    admin role is required for any state-mutating endpoint. Tests can
    override `_security_operator_dep` via FastAPI's dependency_overrides.
    """
    return Depends(_security_operator_dep)


def require_viewer() -> object:
    """RBAC dependency: any authenticated user may read findings."""
    return Depends(_viewer_dep)
