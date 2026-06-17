"""
Status Router.

Provides health checks and system status endpoints used for monitoring
uptime, synthetic metrics, and service readiness.
"""

import time
from typing import Dict


from fastapi import APIRouter, Depends, Response

from core.services.indexing import get_indexing_service
from core.observability import telemetry
from core.observability.logging import get_logger
from core.middleware import require_admin
from core.config import get_app_config, get_vectorstore_config

logger = get_logger(__name__)

_app_config = get_app_config()
_vs_config = get_vectorstore_config()
COLLECTION = _vs_config.collection_name

router = APIRouter(tags=["status"])


@router.get("/health")
def health_check() -> Dict[str, str]:
    """Simple health check endpoint for monitoring (no auth required)."""
    return {"status": "ok"}


@router.get("/status")
def status(user: str = Depends(require_admin)) -> Dict[str, object]:
    """
    Returns the system status:
    - Number of indexed documents
    - Qdrant collection in use (from .env)
    - Synthetic metrics (no paths/files)
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
        "total_indexed_documents": get_indexing_service().indexed_count,
        "metrics": metrics,
    }


# --------------------------------------------------------------------------- #
# Kubernetes-style liveness / readiness probes                                #
#                                                                             #
# Liveness (``/health``) is unconditional and cheap. Readiness checks the     #
# dependencies the pod needs to serve traffic: the database is required;      #
# Redis is advisory (degraded, not unready). Results are briefly cached so a  #
# tight probe loop does not hammer the backends on every poll.                #
# --------------------------------------------------------------------------- #


async def _check_database() -> bool:
    """Return True if the database answers a trivial query; never raises."""
    try:
        from core.db.connection import get_async_connection

        async with get_async_connection() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as exc:  # noqa: BLE001 — readiness must never raise
        logger.warning("readiness_db_check_failed", extra={"error": str(exc)})
        return False


async def _check_redis() -> bool:
    """Return True if Redis responds to PING; never raises."""
    try:
        from core.cache import create_redis_client
        from core.config.cache import get_redis_cache_config

        client = create_redis_client(get_redis_cache_config().url)
        return bool(await client.ping())
    except Exception as exc:  # noqa: BLE001 — readiness must never raise
        logger.warning("readiness_redis_check_failed", extra={"error": str(exc)})
        return False


class _HealthChecker:
    """Caches dependency-probe results for a short TTL to throttle probes."""

    def __init__(self, ttl_seconds: float = 5.0) -> None:
        self._ttl = ttl_seconds
        self._cache: Dict[str, bool] | None = None
        self._expires_at = 0.0

    def invalidate(self) -> None:
        """Drop any cached result so the next check re-probes."""
        self._cache = None
        self._expires_at = 0.0

    async def check(self) -> Dict[str, bool]:
        now = time.monotonic()
        if self._cache is not None and now < self._expires_at:
            return self._cache
        result = {
            "database": await _check_database(),
            "redis": await _check_redis(),
        }
        self._cache = result
        self._expires_at = now + self._ttl
        return result


_health_checker: _HealthChecker | None = None


def get_health_checker() -> _HealthChecker:
    """Return the process-wide health checker (created lazily)."""
    global _health_checker
    if _health_checker is None:
        _health_checker = _HealthChecker()
    return _health_checker


@router.get("/readiness")
async def readiness(response: Response) -> Dict[str, object]:
    """Readiness probe: 200 when the database is reachable, else 503.

    Redis being down is reported but does not flip the pod to *not ready* —
    the service degrades gracefully rather than dropping out of rotation.
    """
    services = await get_health_checker().check()
    ready = bool(services["database"])
    response.status_code = 200 if ready else 503
    return {"status": "ready" if ready else "not_ready", "services": services}
