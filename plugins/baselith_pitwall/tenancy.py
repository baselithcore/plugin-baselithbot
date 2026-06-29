"""Lightweight multi-tenancy for the pit wall — independent of the auth plugin.

Tenant isolation is always on and carries **no** hard dependency on
``plugins.auth``. Two modes, selected by the same ``auth_enabled`` flag that
controls RBAC:

* **Lightweight (default).** The tenant is read from the ``X-Tenant-ID`` request
  header (configurable), defaulting to ``"default"`` when absent. A deployment
  can isolate tenants with a reverse proxy that sets the header.
* **Auth-backed (``auth_enabled`` True).** The header is ignored and the tenant
  is taken solely from the trusted execution context that ``plugins.auth`` +
  ``core.middleware.tenant.TenantMiddleware`` populate from the JWT — closing the
  header-spoofing hole.

The resolved tenant is bound to the shared :func:`core.context.set_tenant_context`
contextvar for the request, so the service layer reads it uniformly via
:func:`current_tenant` without changing any method signature.
"""

from __future__ import annotations

import contextvars
from collections.abc import AsyncIterator
from typing import Any, Callable

from fastapi import Request

from core.context import (
    TenantContextError,
    get_current_tenant_id,
    reset_tenant_context,
    resolve_plugin_tenant_key,
    set_tenant_context,
)

DEFAULT_TENANT = "default"
DEFAULT_TENANT_HEADER = "X-Tenant-ID"
DEFAULT_ACTOR = "anonymous"
ACTOR_HEADER = "X-Actor-ID"

_actor_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "pitwall_actor", default=DEFAULT_ACTOR
)


def current_tenant() -> str:
    """Return the active tenant id, or ``"default"`` outside a tenant context."""
    try:
        # Honour a runtime per-plugin tenancy override; for the default ``shared``
        # mode this equals ``get_tenant_or_default()`` → behaviour unchanged.
        return resolve_plugin_tenant_key("baselith_pitwall")
    except TenantContextError:
        return DEFAULT_TENANT


def current_actor() -> str:
    """Return the principal for the current request, or ``"anonymous"``."""
    return _actor_ctx.get()


def _resolve_actor(request: Request, auth_enabled: bool) -> str:
    """Derive the acting principal from the auth user, then a header."""
    user = getattr(getattr(request, "state", None), "user", None)
    uid = getattr(user, "user_id", None)
    if uid:
        return str(uid)
    if not auth_enabled:
        header_actor = (request.headers.get(ACTOR_HEADER) or "").strip()
        if header_actor:
            return header_actor
    return DEFAULT_ACTOR


def tenant_binder(
    *, auth_enabled: bool = False, header: str = DEFAULT_TENANT_HEADER
) -> Callable[..., Any]:
    """Build a router-level dependency that binds the request's tenant context.

    In auth-backed mode it trusts the already-bound context (JWT-derived); in
    lightweight mode it derives the tenant from the configured header. The
    contextvar is always restored on the way out.
    """

    async def _bind(request: Request) -> AsyncIterator[str]:
        actor_token = _actor_ctx.set(_resolve_actor(request, auth_enabled))
        try:
            if auth_enabled:
                yield get_current_tenant_id()
                return
            raw = (request.headers.get(header) or "").strip()
            tenant = raw or DEFAULT_TENANT
            tenant_token = set_tenant_context(tenant)
            try:
                yield tenant
            finally:
                reset_tenant_context(tenant_token)
        finally:
            _actor_ctx.reset(actor_token)

    return _bind


__all__ = [
    "current_tenant",
    "current_actor",
    "tenant_binder",
    "DEFAULT_TENANT",
    "DEFAULT_TENANT_HEADER",
    "ACTOR_HEADER",
]
