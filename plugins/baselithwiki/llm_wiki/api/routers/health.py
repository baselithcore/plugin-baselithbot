"""Liveness + readiness endpoints.

- ``GET /health/live``: 200 sempre se il processo risponde.
- ``GET /health/ready``: 200 se le dipendenze obbligatorie sono ok,
  503 altrimenti. Aggiorna le gauge ``wiki_*_up`` (scrape Prom).

Pattern porting da ``agent-jira/app/routers/status.py``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response

from llm_wiki import config
from llm_wiki.observability.metrics import (
    GRAPHDB_UP,
    POSTGRES_UP,
    QDRANT_UP,
)

router = APIRouter(tags=["observability"])


def _payload(
    *, name: str, enabled: bool, required: bool, ready: bool, **extra: Any
) -> dict[str, Any]:
    if not enabled:
        status = "disabled"
    elif ready:
        status = "ok"
    else:
        status = "error"
    return {
        "name": name,
        "enabled": enabled,
        "required": required,
        "ready": ready,
        "status": status,
        **extra,
    }


def _check_qdrant() -> dict[str, Any]:
    try:
        from llm_wiki.vectorstore.qdrant_ops import get_qdrant

        client = get_qdrant()
        ready = client is not None
        QDRANT_UP.set(1 if ready else 0)
        return _payload(
            name="qdrant",
            enabled=True,
            required=True,
            ready=ready,
            mode=config.QDRANT_MODE,
            collection=config.COLLECTION_NAME,
        )
    except Exception as exc:  # pragma: no cover
        QDRANT_UP.set(0)
        return _payload(
            name="qdrant",
            enabled=True,
            required=True,
            ready=False,
            error=str(exc),
        )


def _check_postgres() -> dict[str, Any]:
    if not config.POSTGRES_ENABLED:
        POSTGRES_UP.set(1)
        return _payload(name="postgres", enabled=False, required=False, ready=True)
    try:
        from llm_wiki.db.connection import health_check

        ok = bool(health_check())
        POSTGRES_UP.set(1 if ok else 0)
        return _payload(
            name="postgres",
            enabled=True,
            required=bool(config.AUTH_REQUIRED),
            ready=ok,
        )
    except Exception as exc:
        POSTGRES_UP.set(0)
        return _payload(
            name="postgres",
            enabled=True,
            required=bool(config.AUTH_REQUIRED),
            ready=False,
            error=str(exc),
        )


def _check_graphdb() -> dict[str, Any]:
    try:
        from llm_wiki.graphdb.core import get_graph_db

        graph = get_graph_db()
        enabled = bool(graph.is_enabled())
        ready = bool(graph.ping()) if enabled else True
        GRAPHDB_UP.set(1 if (not enabled or ready) else 0)
        return _payload(name="graphdb", enabled=enabled, required=enabled, ready=ready)
    except Exception as exc:  # pragma: no cover
        GRAPHDB_UP.set(0)
        return _payload(
            name="graphdb",
            enabled=True,
            required=False,
            ready=False,
            error=str(exc),
        )


def _check_pack() -> dict[str, Any]:
    """Pack attivo: required quando ``APP_DOMAIN`` è valorizzato."""
    if not config.APP_DOMAIN:
        return _payload(
            name="domain_pack",
            enabled=False,
            required=False,
            ready=True,
            note="setup mode",
        )
    try:
        from llm_wiki.domain.registry import load_pack

        pack = load_pack()
        return _payload(
            name="domain_pack",
            enabled=True,
            required=True,
            ready=True,
            active=pack.name,
        )
    except Exception as exc:
        return _payload(
            name="domain_pack",
            enabled=True,
            required=True,
            ready=False,
            error=str(exc),
        )


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
def ready(response: Response) -> dict[str, Any]:
    deps = {
        "qdrant": _check_qdrant(),
        "postgres": _check_postgres(),
        "graphdb": _check_graphdb(),
        "domain_pack": _check_pack(),
    }
    blocking = [d for d in deps.values() if d.get("required") and not d.get("ready")]
    is_ready = not blocking
    response.status_code = 200 if is_ready else 503
    return {
        "status": "ok" if is_ready else "degraded",
        "ready": is_ready,
        "dependencies": deps,
    }
