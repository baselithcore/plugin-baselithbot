"""Lightweight multi-tenancy for BOP — independent of the auth plugin.

Tenant isolation is always on and carries **no** dependency on ``plugins.auth``.
Two modes, selected by the same ``auth_enabled`` flag that controls RBAC:

* **Lightweight (default, ``auth_enabled`` False).** The tenant is read from the
  ``X-Tenant-ID`` request header (configurable via ``tenant_header``), defaulting
  to ``"default"`` when absent. No auth, no JWT — a deployment can isolate
  tenants with a reverse proxy that sets the header.

* **Auth-backed (``auth_enabled`` True).** The header is ignored and the tenant
  is taken solely from the trusted execution context that ``plugins.auth`` +
  ``core.middleware.tenant.TenantMiddleware`` populate from the JWT. This closes
  the header-spoofing hole that would otherwise let a caller read another
  tenant's data.

Either way the resolved tenant is bound to the shared
:func:`core.context.set_tenant_context` contextvar for the duration of the
request, so the service layer reads it uniformly via :func:`current_tenant`
without any change to its public method signatures.
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
    set_tenant_context,
)

DEFAULT_TENANT = "default"
DEFAULT_TENANT_HEADER = "X-Tenant-ID"
DEFAULT_ACTOR = "anonymous"
ACTOR_HEADER = "X-Actor-ID"

# Best-effort identity of the principal performing the current request, used to
# stamp the audit trail. Independent of the tenant contextvar and of the auth
# plugin: resolved from the authenticated user when present, else a header.
_actor_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "bop_actor", default=DEFAULT_ACTOR
)


def current_tenant() -> str:
    """Return the active tenant id, or ``"default"`` outside a tenant context.

    Defensive against ``strict_tenant_isolation``: when the platform is
    configured to raise on a missing tenant context (e.g. a background task or a
    direct service call outside the request path), BOP degrades to the default
    tenant rather than crashing the operation. Request traffic always has a
    tenant bound by :func:`tenant_binder` (or the platform auth middleware), so
    this fallback only affects out-of-band callers.
    """
    try:
        return get_current_tenant_id()
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
            # Auth-backed: never trust client-supplied headers for tenancy.
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
