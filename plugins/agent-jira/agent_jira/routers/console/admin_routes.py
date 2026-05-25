from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException

from . import public_router, router
from .common import _reset_analysis_cache_state

logger = logging.getLogger(__name__)


def _require_admin_reset_token(
    x_admin_reset_token: Optional[str] = Header(default=None),
) -> None:
    expected = os.getenv("ADMIN_RESET_TOKEN", "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_RESET_TOKEN non configurato sul backend",
        )
    if not x_admin_reset_token or x_admin_reset_token.strip() != expected:
        raise HTTPException(status_code=401, detail="Token admin non valido")


def _reset_falkordb() -> Dict[str, Any]:
    """Cancella tutti i grafi FalkorDB con prefix GRAPH_DB_NAME + FLUSHDB di sicurezza."""
    from agent_jira.graphdb import graph_db
    from agent_jira.config import GRAPH_DB_NAME

    result: Dict[str, Any] = {"graphs_deleted": [], "flushdb": False, "errors": []}
    if not graph_db.is_enabled():
        result["errors"].append("graph_db disabled")
        return result
    try:
        client = graph_db._get_client()
    except Exception as exc:
        result["errors"].append(f"client error: {exc}")
        return result

    # 1) enumerate via GRAPH.LIST
    try:
        graphs = client.execute_command("GRAPH.LIST") or []
    except Exception as exc:
        graphs = []
        result["errors"].append(f"GRAPH.LIST failed: {exc}")

    # 2) fallback: SCAN su chiavi con prefix GRAPH_DB_NAME
    try:
        for key in client.scan_iter(match=f"{GRAPH_DB_NAME}*"):
            if key not in graphs:
                graphs.append(key)
    except Exception as exc:
        result["errors"].append(f"SCAN failed: {exc}")

    for g in graphs:
        name = g.decode() if isinstance(g, (bytes, bytearray)) else str(g)
        try:
            client.execute_command("GRAPH.DELETE", name)
            result["graphs_deleted"].append(name)
        except Exception as exc:
            result["errors"].append(f"GRAPH.DELETE {name}: {exc}")

    # 3) FLUSHDB per rimuovere indici/metadata residui (FalkorDB è container dedicato).
    try:
        client.flushdb()
        result["flushdb"] = True
    except Exception as exc:
        result["errors"].append(f"FLUSHDB failed: {exc}")

    return result


def _reset_qdrant() -> Dict[str, Any]:
    """Cancella tutte le collection Qdrant con prefix COLLECTION_NAME."""
    from agent_jira.config import COLLECTION, QDRANT

    result: Dict[str, Any] = {"collections_deleted": [], "errors": []}
    try:
        existing = QDRANT.get_collections().collections or []
    except Exception as exc:
        result["errors"].append(f"get_collections: {exc}")
        return result

    for col in existing:
        name = col.name
        if name == COLLECTION or name.startswith(f"{COLLECTION}_"):
            try:
                QDRANT.delete_collection(collection_name=name)
                result["collections_deleted"].append(name)
            except Exception as exc:
                result["errors"].append(f"delete {name}: {exc}")
    return result


@router.post("/admin/reset-caches")
def reset_caches() -> Dict[str, Any]:
    """Svuota le cache in-process della console (analisi, KB counts, graph).
    Non tocca Redis/Qdrant/FalkorDB/filesystem: per quelli usa scripts/demo_reset.sh.
    """
    cleared: Dict[str, Any] = {
        "analysis_cache": False,
        "kb_counts": False,
        "graph": False,
    }

    try:
        _reset_analysis_cache_state()
        cleared["analysis_cache"] = True
    except Exception as exc:
        logger.warning("reset analysis cache failed: %s", exc)

    try:
        from .kb import _GRAPH_CACHE, _KB_COUNTS_CACHE

        _KB_COUNTS_CACHE.clear()
        cleared["kb_counts"] = True
        _GRAPH_CACHE.clear()
        cleared["graph"] = True
    except Exception as exc:
        logger.warning("reset KB caches failed: %s", exc)

    logger.info("Console in-process caches reset: %s", cleared)
    return {"status": "ok", "cleared": cleared}


@public_router.post(
    "/admin/purge-chat-caches",
    dependencies=[Depends(_require_admin_reset_token)],
)
def purge_chat_caches(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Svuota le cache in-memory del ChatService (response_cache, rerank_cache, history).

    Usato dallo script `scripts/full_reset.sh` per invalidare le cache dopo
    una pulizia tenant (necessario quando CACHE_BACKEND=local). Richiede header
    `X-Admin-Reset-Token` con valore pari a env `ADMIN_RESET_TOKEN`.

    Il parametro `tenant_id` è opzionale e usato solo per audit log — le cache
    in-process non sono tenant-scoped quindi vengono svuotate integralmente.
    """
    from agent_jira.chat import get_chat_service

    cleared: Dict[str, Any] = {
        "response_cache": False,
        "rerank_cache": False,
        "history_cache": False,
    }

    try:
        svc = get_chat_service()
    except Exception as exc:
        logger.warning("purge-chat-caches: ChatService non disponibile: %s", exc)
        return {"status": "error", "detail": str(exc), "cleared": cleared}

    try:
        if svc.response_cache is not None:
            svc.response_cache.clear()
            cleared["response_cache"] = True
    except Exception as exc:
        logger.warning("purge response_cache failed: %s", exc)

    try:
        if svc.rerank_cache is not None:
            svc.rerank_cache.clear()
            cleared["rerank_cache"] = True
    except Exception as exc:
        logger.warning("purge rerank_cache failed: %s", exc)

    try:
        history_cache = getattr(svc.history_manager, "_cache", None)
        if history_cache is not None:
            history_cache.clear()
            cleared["history_cache"] = True
    except Exception as exc:
        logger.warning("purge history_cache failed: %s", exc)

    logger.info("Chat caches purged (tenant_id=%s): %s", tenant_id or "<none>", cleared)
    return {"status": "ok", "tenant_id": tenant_id, "cleared": cleared}


@router.post("/admin/reset-all")
def reset_all(
    graph: bool = True,
    vector: bool = True,
    caches: bool = True,
) -> Dict[str, Any]:
    """Reset totale lato backend: cache in-process + FalkorDB (tutti i grafi con prefix)
    + Qdrant (tutte le collection con prefix). Il backend raggiunge i servizi
    via rete docker, evitando i problemi di hostname del client host.
    """
    result: Dict[str, Any] = {}
    if caches:
        result["caches"] = reset_caches()
    if graph:
        result["falkordb"] = _reset_falkordb()
    if vector:
        result["qdrant"] = _reset_qdrant()
    logger.info("Console reset-all: %s", result)
    return {"status": "ok", **result}
