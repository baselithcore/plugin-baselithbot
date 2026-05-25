"""ASGI middleware: tenant context, request id, security headers, access log."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..core.logging import log
from ..core.tenant import reset_tenant, resolve_tenant_from_request, set_tenant


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        tenant_id = resolve_tenant_from_request(dict(request.headers))
        token = set_tenant(tenant_id)
        request.state.tenant_id = tenant_id
        structlog.contextvars.bind_contextvars(tenant_id=tenant_id)
        try:
            response: Response = await call_next(request)
        finally:
            reset_tenant(token)
        response.headers["X-Tenant-Id"] = tenant_id
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Outermost middleware: assigns request_id and emits structured access log.

    Binds request-scoped context (request_id, method, path) into structlog
    contextvars so every downstream log line in the request scope carries
    them automatically. Clears them at the end to prevent cross-request
    leakage on async tasks reusing the loop.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        rid = request.headers.get("X-Request-Id") or f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = rid

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=rid,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        status = 500
        try:
            response: Response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-Id"] = rid
            return response
        except Exception:
            log.exception("http.request_failed")
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.info(
                "http.request",
                status=status,
                duration_ms=duration_ms,
                client=request.client.host if request.client else None,
                query=request.url.query or None,
            )
            structlog.contextvars.clear_contextvars()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=()"
        )
        return response
