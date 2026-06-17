"""Shared dependencies and helpers for the pit-wall router package.

Centralises the cross-cutting request concerns so each endpoint group stays
thin: tenant binding (lightweight header or JWT-backed), session resolution
(``X-Session-ID`` header, default ``demo``), the live-engine lookup, localized
errors, RBAC guards, idempotent-replay, and per-tenant rate limiting. The
concrete :class:`RouterContext` is built once per router from the plugin and
captured by every endpoint closure.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from fastapi import Depends, HTTPException, Request

from ..i18n import negotiate_locale, translate
from ..security import require_approver, require_strategist, require_viewer
from ..service import PitwallService
from ..session_manager import DEFAULT_SESSION_ID
from ..tenancy import current_actor, tenant_binder

if TYPE_CHECKING:
    from ..plugin import BaselithPitwallPlugin

API_VERSION = "1.0.0"
SESSION_HEADER = "X-Session-ID"


@dataclass(frozen=True)
class Ctx:
    """Resolved per-request context: which tenant, which session, acting whom."""

    tenant: str
    session_id: str
    actor: str


class RouterContext:
    """Plugin-bound helpers shared by every endpoint group."""

    def __init__(self, plugin: "BaselithPitwallPlugin") -> None:
        self.plugin = plugin
        cfg = plugin.config
        self.auth_enabled = cfg.auth_enabled
        self._bind_tenant = tenant_binder(
            auth_enabled=cfg.auth_enabled, header=cfg.tenant_header
        )

    # -- request context ---------------------------------------------------

    async def ctx(self, request: Request) -> AsyncIterator[Ctx]:
        """Bind the tenant context and resolve the target session + actor.

        Delegates to the ``tenant_binder`` generator via ``async for`` so its
        contextvar cleanup runs when FastAPI tears the dependency down.
        """
        async for tenant in self._bind_tenant(request):
            # Header wins; query param is the fallback for EventSource (SSE),
            # which cannot send custom headers.
            session_id = (
                (request.headers.get(SESSION_HEADER) or "").strip()
                or (request.query_params.get("session_id") or "").strip()
                or DEFAULT_SESSION_ID
            )
            yield Ctx(tenant=tenant, session_id=session_id, actor=current_actor())

    # -- engine + session lookup ------------------------------------------

    def live_service(self, ctx: Ctx) -> PitwallService:
        """Return the running engine for ``ctx`` or raise 503 if not live."""
        service = self.plugin.manager.get_service(ctx.tenant, ctx.session_id)
        if service is None or not service.bus.running:
            raise HTTPException(status_code=503, detail="pitwall_session_not_live")
        return service

    # -- errors ------------------------------------------------------------

    @staticmethod
    def error(status: int, key: str, accept_language: str | None) -> HTTPException:
        """Build a localized HTTPException from a catalog key."""
        return HTTPException(status, translate(key, negotiate_locale(accept_language)))

    # -- hardening ---------------------------------------------------------

    def rate_check(self, ctx: Ctx) -> None:
        """Enforce the per-tenant rate limit on a mutating call (429 on breach)."""
        if not self.plugin.rate_limiter.allow(ctx.tenant):
            raise HTTPException(status_code=429, detail="pitwall_rate_limited")

    def idem_get(self, ctx: Ctx, key: str | None) -> Any | None:
        """Return a previously stored idempotent result for ``key``, if any."""
        if not key:
            return None
        return self.plugin.idempotency.get(ctx.tenant, key)

    def idem_put(self, ctx: Ctx, key: str | None, value: Any) -> Any:
        """Store an idempotent result under ``key`` and return it unchanged."""
        if key:
            self.plugin.idempotency.put(ctx.tenant, key, value)
        return value

    # -- guards ------------------------------------------------------------

    def viewer(self) -> Callable[..., Any]:
        """Read-surface guard dependency."""
        return require_viewer(self.auth_enabled)

    def strategist(self) -> Callable[..., Any]:
        """Mutating-surface guard dependency."""
        return require_strategist(self.auth_enabled)

    def approver(self) -> Callable[..., Any]:
        """HITL accept/reject guard dependency."""
        return require_approver(self.auth_enabled)

    def ctx_dep(self) -> Callable[..., Any]:
        """Return the FastAPI dependency that resolves :class:`Ctx`."""

        async def _dep(request: Request) -> AsyncIterator[Ctx]:
            async for ctx in self.ctx(request):
                yield ctx

        return _dep


def use_ctx(rc: RouterContext) -> Any:
    """Shorthand to declare the ctx dependency in a route signature."""
    return Depends(rc.ctx_dep())


__all__ = ["RouterContext", "Ctx", "use_ctx", "API_VERSION", "SESSION_HEADER"]
