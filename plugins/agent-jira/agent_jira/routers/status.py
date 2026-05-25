from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse

from agent_jira.graphdb import graph_db
from agent_jira.metrics import GRAPHDB_UP, POSTGRES_UP, QDRANT_UP, REDIS_UP
from agent_jira.security import require_admin
from agent_jira.telemetry import telemetry
from agent_jira.vectorstore import indexed_items
from agent_jira.config import CHATBOT_CLIENT_CONFIG, COLLECTION, QDRANT, QDRANT_MODE  # 👈 da .env

router = APIRouter(tags=["status"])
CHATBOT_ENV_PATH = (
    Path(__file__).resolve().parent.parent / "static" / "chatbot" / "chatbot.env"
)


def _dependency_payload(
    *,
    name: str,
    enabled: bool,
    required: bool,
    ready: bool,
    **extra: Any,
) -> Dict[str, Any]:
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


def _get_jira_client():
    from agent_jira.ui.services import get_chat_service

    return getattr(get_chat_service(), "jira_client", None)


def _check_qdrant() -> Dict[str, Any]:
    try:
        collections = QDRANT.get_collections()
        names = [item.name for item in collections.collections]
        collection_exists = COLLECTION in names
        QDRANT_UP.set(1 if collection_exists else 0)
        return _dependency_payload(
            name="qdrant",
            enabled=True,
            required=True,
            ready=collection_exists,
            mode=QDRANT_MODE,
            collection=COLLECTION,
            collection_exists=collection_exists,
        )
    except Exception as exc:  # pragma: no cover - depends on Qdrant runtime
        QDRANT_UP.set(0)
        return _dependency_payload(
            name="qdrant",
            enabled=True,
            required=True,
            ready=False,
            mode=QDRANT_MODE,
            collection=COLLECTION,
            error=str(exc),
        )


def _check_graphdb() -> Dict[str, Any]:
    enabled = bool(graph_db.is_enabled())
    ready = bool(graph_db.ping()) if enabled else True
    GRAPHDB_UP.set(1 if (not enabled or ready) else 0)
    return _dependency_payload(
        name="graphdb",
        enabled=enabled,
        required=enabled,
        ready=ready,
    )


def _check_postgres() -> Dict[str, Any]:
    """Health check Postgres: SELECT 1 via pool per verificare connettività."""
    from agent_jira.config import POSTGRES_ENABLED

    if not POSTGRES_ENABLED:
        POSTGRES_UP.set(1)
        return _dependency_payload(
            name="postgres", enabled=False, required=False, ready=True
        )
    try:
        from agent_jira.db.connection import get_connection

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        POSTGRES_UP.set(1)
        return _dependency_payload(
            name="postgres", enabled=True, required=True, ready=True
        )
    except Exception as exc:
        POSTGRES_UP.set(0)
        return _dependency_payload(
            name="postgres",
            enabled=True,
            required=True,
            ready=False,
            error=str(exc),
        )


def _check_redis() -> Dict[str, Any]:
    """Health check Redis (se CACHE_BACKEND=redis)."""
    from agent_jira.config import CACHE_BACKEND, CACHE_REDIS_URL

    if CACHE_BACKEND != "redis":
        REDIS_UP.set(1)
        return _dependency_payload(
            name="redis", enabled=False, required=False, ready=True
        )
    try:
        from agent_jira.cache import create_redis_client

        client = create_redis_client(CACHE_REDIS_URL)
        client.ping()
        REDIS_UP.set(1)
        return _dependency_payload(
            name="redis", enabled=True, required=True, ready=True
        )
    except Exception as exc:
        REDIS_UP.set(0)
        return _dependency_payload(
            name="redis",
            enabled=True,
            required=True,
            ready=False,
            error=str(exc),
        )


def _resolve_request_tenant_id(request: Optional[Request]) -> Optional[str]:
    """Extract tenant_id from JWT Authorization header. Used when tenant middleware
    skipped the route (e.g. /health/*) but endpoint still needs tenant context."""
    from agent_jira.tenant_context import get_current_tenant_id

    tid = get_current_tenant_id()
    if tid:
        return tid
    if request is None:
        return None
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    try:
        import jwt as pyjwt

        from agent_jira.config import SECRET_KEY

        if not SECRET_KEY:
            return None
        payload = pyjwt.decode(
            auth_header[7:].strip(), SECRET_KEY, algorithms=["HS256"]
        )
        claim_tenant_id = payload.get("tenant_id")
        return str(claim_tenant_id).strip() if claim_tenant_id else None
    except Exception:
        return None


def _check_tenant_jira_configured(request: Optional[Request] = None) -> bool:
    """True if current tenant has Jira credentials stored in DB."""
    try:
        from agent_jira.config import MULTI_TENANT_ENABLED, POSTGRES_ENABLED

        if not (MULTI_TENANT_ENABLED and POSTGRES_ENABLED):
            return False
        tenant_id = _resolve_request_tenant_id(request)
        if not tenant_id:
            return False
        from agent_jira.db.tenants import get_tenant_by_id

        tenant = get_tenant_by_id(tenant_id)
        if not tenant:
            return False
        jira = (tenant.get("settings") or {}).get("jira") or {}
        return bool(
            jira.get("base_url")
            and jira.get("email")
            and jira.get("api_token")
            and (jira.get("default_project_key") or jira.get("project_key"))
        )
    except Exception:
        return False


def _check_jira(request: Optional[Request] = None) -> Dict[str, Any]:
    client = _get_jira_client()
    enabled = bool(client and client.is_ready())
    if not enabled and _check_tenant_jira_configured(request):
        return _dependency_payload(
            name="jira",
            enabled=True,
            required=False,
            ready=True,
            status="ok",
        )
    if not enabled or client is None:
        return _dependency_payload(
            name="jira",
            enabled=False,
            required=False,
            ready=True,
        )
    checker = getattr(client, "check_connection", None)
    try:
        ready = bool(checker()) if callable(checker) else bool(client.is_ready())
    except Exception as exc:  # pragma: no cover - depends on Jira runtime
        return _dependency_payload(
            name="jira",
            enabled=True,
            required=False,
            ready=False,
            error=str(exc),
        )
    return _dependency_payload(
        name="jira",
        enabled=True,
        required=False,
        ready=ready,
    )


@router.get("/chatbot/config")
def chatbot_config() -> Dict[str, object]:
    """Config del widget chatbot (colori, flag) dal backend."""

    return CHATBOT_CLIENT_CONFIG


@router.get("/chatbot.env", response_class=PlainTextResponse)
def chatbot_env_legacy() -> str:
    """
    Compatibilità con i widget legacy che richiedono un file chatbot.env.
    Restituisce le variabili disponibili in formato chiave=valore.
    """

    if CHATBOT_ENV_PATH.exists():
        return CHATBOT_ENV_PATH.read_text(encoding="utf-8")

    lines = []
    if CHATBOT_CLIENT_CONFIG.get("api_url"):
        lines.append(f"CHATBOT_API_URL={CHATBOT_CLIENT_CONFIG['api_url']}")
    lines.append(
        f"CHATBOT_ENABLE_FEEDBACK={CHATBOT_CLIENT_CONFIG.get('feedback_enabled', True)}"
    )
    color_overrides = CHATBOT_CLIENT_CONFIG.get("color_overrides") or {}
    for key, value in color_overrides.items():
        lines.append(f"{key}={value}")
    return "\n".join(lines)


@router.get("/health/live")
def live_health() -> Dict[str, object]:
    return {"status": "alive"}


@router.get("/api/v2/heartbeat")
def heartbeat_v2() -> Dict[str, object]:
    """Endpoint compatibilità v2 per health check/heartbeat."""
    return {"status": "alive"}


@router.get("/health/ready")
def ready_health(request: Request, response: Response) -> Dict[str, object]:
    dependencies = {
        "postgres": _check_postgres(),
        "qdrant": _check_qdrant(),
        "graphdb": _check_graphdb(),
        "redis": _check_redis(),
        "jira": _check_jira(request),
    }
    blocking = [
        payload
        for payload in dependencies.values()
        if payload.get("required") and not payload.get("ready")
    ]
    ready = not blocking
    response.status_code = 200 if ready else 503
    return {
        "status": "ok" if ready else "degraded",
        "ready": ready,
        "dependencies": dependencies,
    }


@router.get("/status")
def status(user: str = Depends(require_admin)) -> Dict[str, object]:
    """
    Restituisce lo stato del sistema:
    - Numero documenti indicizzati
    - Collezione Qdrant in uso (da .env)
    - Metriche sintetiche (no percorsi/file)
    """

    metrics = telemetry.snapshot()
    counters = metrics.get("counters", {})
    clarification_summary = {
        "triggered": counters.get("clarification.triggered", 0),
        "no_hits": counters.get("clarification.no_hits", 0),
        "no_reranked_hits": counters.get("clarification.no_reranked_hits", 0),
        "empty_context": counters.get("clarification.empty_context", 0),
    }
    metrics["clarification"] = clarification_summary
    metrics["answers"] = {
        "generated": counters.get("answers.generated", 0),
        "cached": counters.get("answers.cached", 0),
        "clarification": counters.get("answers.clarification", 0),
        "guardrail_block": counters.get("answers.guardrail_block", 0),
        "guardrail_fallback": counters.get("answers.guardrail_fallback", 0),
        "error": counters.get("answers.error", 0),
    }
    metrics["sources"] = {
        "low_coverage": counters.get("sources.low_coverage", 0),
    }

    return {
        "status": "ok",
        "collection": COLLECTION,
        "total_indexed_documents": len(indexed_items),
        "metrics": metrics,
    }
