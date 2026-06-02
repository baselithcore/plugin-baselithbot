"""Prometheus ``/metrics`` endpoint.

Gating layered: bearer admin **OR** ``X-API-Key: $WIKI_METRICS_TOKEN``
**OR** loopback (setup mode senza Postgres). Default policy:

- Postgres ON + bearer admin → 200 (auth router-side via ``require_admin``)
- ``WIKI_METRICS_TOKEN`` valorizzato + header match → 200 (per scrape)
- loopback → 200 (sviluppo locale, scrape diretto)
- altrimenti → 401

Senza ``prometheus_client`` installato l'endpoint ritorna 503 con
indicazione di installare l'extra ``[obs]``.
"""

from __future__ import annotations

import ipaddress as _ipaddress
import os

from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter(tags=["observability"])


def _is_loopback(host: str | None) -> bool:
    if not host:
        return False
    try:
        return _ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _gate(request: Request) -> None:
    # 1) X-API-Key match (env-configured)
    expected = os.getenv("WIKI_METRICS_TOKEN", "").strip()
    presented = request.headers.get("x-api-key", "").strip()
    if expected and presented and presented == expected:
        return

    # 2) Bearer admin (Postgres ON)
    auth_header = request.headers.get("authorization", "").lower()
    if auth_header.startswith("bearer "):
        try:
            from llm_wiki.auth.dependencies import require_admin

            require_admin(request)
            return
        except HTTPException:
            pass

    # 3) Loopback fallback (dev/setup)
    client_host = request.client.host if request.client else None
    if _is_loopback(client_host):
        return

    raise HTTPException(status_code=401, detail="metrics endpoint protected")


@router.get("/metrics")
def prometheus_metrics(request: Request) -> Response:
    _gate(request)
    try:
        from prometheus_client import (
            CONTENT_TYPE_LATEST,
            REGISTRY,
            generate_latest,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "prometheus_client non installato — aggiungi `[obs]` extra: pip install -e '.[obs]'"
            ),
        ) from exc
    payload = generate_latest(REGISTRY)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
