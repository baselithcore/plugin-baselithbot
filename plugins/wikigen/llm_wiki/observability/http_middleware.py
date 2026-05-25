"""Middleware per metriche HTTP per-tenant.

Wrappa ogni request: inc counter chat / errors, observe latency, tutto
labellato con ``tenant_id`` (dal contextvar di ``llm_wiki.auth``).

Pattern porting da ``agent-jira/app/tenant_context.py:TenantMiddleware``,
spostato qui per separazione concerni: l'attuale ``TenantMiddleware``
in :mod:`llm_wiki.auth.middleware` resta responsabile della *risoluzione*
del tenant da JWT/header; questo middleware si limita a *misurare* la
richiesta, leggendo il contextvar già popolato.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from llm_wiki.observability.metrics import (
    TENANT_HTTP_ERRORS_TOTAL,
    TENANT_HTTP_LATENCY_SECONDS,
    TENANT_HTTP_REQUESTS_TOTAL,
)


def _route_template(request: Request) -> str:
    """Template della route (``/api/wiki/{slug}``) — non il path espanso.

    FastAPI espone la route nel ``request.scope`` come ``Route`` object;
    fallback al path raw se non ancora risolto (middleware è chiamato
    prima del routing in alcuni stack — Starlette in realtà espone scope
    ``route`` solo dopo routing, ma BaseHTTPMiddleware vede il response
    finale).
    """
    route = request.scope.get("route")
    if route is not None:
        return getattr(route, "path", request.url.path)
    return request.url.path


def _status_bucket(status: int) -> str:
    if status < 200:
        return "1xx"
    if status < 300:
        return "2xx"
    if status < 400:
        return "3xx"
    if status < 500:
        return "4xx"
    return "5xx"


class HttpMetricsMiddleware(BaseHTTPMiddleware):
    """Emette metriche Prometheus per-request, taggate per tenant."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            try:
                from llm_wiki.auth.tenant_context import get_current_tenant_id

                tid = get_current_tenant_id() or "_anonymous"
            except Exception:
                tid = "_anonymous"
            route = _route_template(request)
            elapsed = time.perf_counter() - start
            TENANT_HTTP_REQUESTS_TOTAL.labels(
                tenant_id=tid,
                method=request.method,
                route=route,
                status_bucket=_status_bucket(status_code),
            ).inc()
            TENANT_HTTP_LATENCY_SECONDS.labels(tenant_id=tid, route=route).observe(
                elapsed
            )
            if status_code >= 400:
                TENANT_HTTP_ERRORS_TOTAL.labels(
                    tenant_id=tid, route=route, status=str(status_code)
                ).inc()


__all__ = ["HttpMetricsMiddleware"]
