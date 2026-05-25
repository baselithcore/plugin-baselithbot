"""
Quota system per multi-tenancy.

Gestisce limiti per piano (free, pro, enterprise) su:
- storage_mb: spazio documenti totale
- documents: numero massimo di documenti
- api_calls_per_day: chiamate API giornaliere
- vectors: numero massimo di vettori in Qdrant
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, Optional

from agent_jira.tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)

# Limiti per piano (allineati a PLAN_MAX_USERS in config.py)
PLAN_LIMITS: Dict[str, Dict[str, int]] = {
    "free": {
        "storage_mb": 100,
        "documents": 50,
        "api_calls_per_day": 500,
        "vectors": 10_000,
    },
    "pro": {
        "storage_mb": 1_000,
        "documents": 500,
        "api_calls_per_day": 5_000,
        "vectors": 100_000,
    },
    "business": {
        "storage_mb": 5_000,
        "documents": 2_000,
        "api_calls_per_day": 20_000,
        "vectors": 500_000,
    },
    "enterprise": {
        "storage_mb": 10_000,
        "documents": 5_000,
        "api_calls_per_day": 50_000,
        "vectors": 1_000_000,
    },
}


def get_plan_limits(plan: str) -> Dict[str, int]:
    """Restituisce i limiti per un piano. Default a 'free' se non trovato."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"]).copy()


class QuotaTracker:
    """
    Tracker per l'utilizzo delle risorse di un tenant.

    Usa Redis per il tracking distribuito (api_calls con TTL giornaliero),
    e query on-demand per storage e document count.
    """

    def __init__(self) -> None:
        self._redis = None
        self._redis_checked = False

    def _get_redis(self):
        if not self._redis_checked:
            self._redis_checked = True
            try:
                from agent_jira.config import CACHE_BACKEND, CACHE_REDIS_URL

                if CACHE_BACKEND == "redis" and CACHE_REDIS_URL:
                    from agent_jira.cache import create_redis_client

                    self._redis = create_redis_client(CACHE_REDIS_URL)
            except Exception:
                self._redis = None
        return self._redis

    def track_api_call(self, tenant_id: Optional[str] = None) -> None:
        """Incrementa il contatore API calls per il tenant corrente."""
        tid = tenant_id or get_current_tenant_id()
        if not tid:
            return

        redis = self._get_redis()
        if not redis:
            return

        today = datetime.date.today().isoformat()
        key = f"quota:api_calls:{tid}:{today}"
        pipe = redis.pipeline(transaction=False)
        pipe.incr(key)
        pipe.expire(key, 86400 + 3600)  # TTL 25h per sicurezza
        pipe.execute()

    def get_api_calls_today(self, tenant_id: Optional[str] = None) -> int:
        """Restituisce il numero di API calls del tenant oggi."""
        tid = tenant_id or get_current_tenant_id()
        if not tid:
            return 0

        redis = self._get_redis()
        if not redis:
            return 0

        today = datetime.date.today().isoformat()
        key = f"quota:api_calls:{tid}:{today}"
        val = redis.get(key)
        return int(val) if val else 0

    def check_api_quota(self, plan: str, tenant_id: Optional[str] = None) -> None:
        """Verifica se il tenant ha superato la quota API giornaliera."""
        from fastapi import HTTPException, status

        tid = tenant_id or get_current_tenant_id()
        if not tid:
            return

        limits = get_plan_limits(plan)
        daily_limit = limits.get("api_calls_per_day", 0)
        if daily_limit <= 0:
            return

        current = self.get_api_calls_today(tid)
        if current >= daily_limit:
            logger.warning(
                "[quotas] Tenant %s ha superato il limite API giornaliero (%d/%d)",
                tid,
                current,
                daily_limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quota API giornaliera esaurita ({current}/{daily_limit}). "
                f"Aggiorna il piano per aumentare il limite.",
            )

    # === Storage & documents (Sprint 12) ===
    def get_storage_usage_mb(self, tenant_id: Optional[str] = None) -> float:
        """Calcola lo spazio su disco (MB) occupato dai documenti del tenant."""
        tid = tenant_id or get_current_tenant_id()
        if not tid:
            return 0.0
        try:
            from pathlib import Path

            from agent_jira.config import DOCUMENTS_ROOT

            tenant_dir = Path(DOCUMENTS_ROOT) / tid
            if not tenant_dir.exists():
                return 0.0
            total = sum(p.stat().st_size for p in tenant_dir.rglob("*") if p.is_file())
            return round(total / (1024 * 1024), 2)
        except Exception as exc:
            logger.warning("[quotas] storage usage failed for %s: %s", tid, exc)
            return 0.0

    def get_document_count(self, tenant_id: Optional[str] = None) -> int:
        """Numero di documenti del tenant su disco."""
        tid = tenant_id or get_current_tenant_id()
        if not tid:
            return 0
        try:
            from pathlib import Path

            from agent_jira.config import DOCUMENTS_EXTENSIONS, DOCUMENTS_ROOT

            tenant_dir = Path(DOCUMENTS_ROOT) / tid
            if not tenant_dir.exists():
                return 0
            allowed = {ext.lower() for ext in DOCUMENTS_EXTENSIONS}
            return sum(
                1
                for p in tenant_dir.rglob("*")
                if p.is_file() and p.suffix.lower() in allowed
            )
        except Exception as exc:
            logger.warning("[quotas] doc count failed for %s: %s", tid, exc)
            return 0

    def check_upload_quota(
        self,
        plan: str,
        incoming_bytes: int,
        tenant_id: Optional[str] = None,
    ) -> None:
        """
        Verifica se il tenant può accettare un upload di `incoming_bytes`.
        Raise HTTPException 413 se supera il limite storage_mb o documents.
        """
        from fastapi import HTTPException, status

        tid = tenant_id or get_current_tenant_id()
        if not tid:
            return

        limits = get_plan_limits(plan)
        storage_limit_mb = limits.get("storage_mb", 0)
        docs_limit = limits.get("documents", 0)

        current_mb = self.get_storage_usage_mb(tid)
        incoming_mb = incoming_bytes / (1024 * 1024)
        if storage_limit_mb > 0 and current_mb + incoming_mb > storage_limit_mb:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"Spazio esaurito: {current_mb:.1f}/{storage_limit_mb} MB "
                    f"(piano {plan}). Cancella documenti o aggiorna il piano."
                ),
            )

        current_docs = self.get_document_count(tid)
        if docs_limit > 0 and current_docs >= docs_limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"Numero massimo documenti raggiunto: {current_docs}/{docs_limit} "
                    f"(piano {plan})."
                ),
            )

    # === LLM tokens budget (giornaliero) ===
    def track_llm_tokens(self, tokens: int, tenant_id: Optional[str] = None) -> None:
        """Incrementa il contatore token LLM giornaliero per il tenant."""
        tid = tenant_id or get_current_tenant_id()
        if not tid or tokens <= 0:
            return
        redis = self._get_redis()
        if not redis:
            return
        today = datetime.date.today().isoformat()
        key = f"quota:llm_tokens:{tid}:{today}"
        pipe = redis.pipeline(transaction=False)
        pipe.incrby(key, tokens)
        pipe.expire(key, 86400 + 3600)
        pipe.execute()

    def get_llm_tokens_today(self, tenant_id: Optional[str] = None) -> int:
        tid = tenant_id or get_current_tenant_id()
        if not tid:
            return 0
        redis = self._get_redis()
        if not redis:
            return 0
        today = datetime.date.today().isoformat()
        val = redis.get(f"quota:llm_tokens:{tid}:{today}")
        return int(val) if val else 0

    # === Usage summary + Prometheus export ===
    def get_usage_summary(
        self, tenant_id: Optional[str] = None, plan: str = "free"
    ) -> Dict[str, Any]:
        """Restituisce un riepilogo completo dell'utilizzo del tenant."""
        tid = tenant_id or get_current_tenant_id()
        limits = get_plan_limits(plan)
        storage_mb = self.get_storage_usage_mb(tid) if tid else 0.0
        doc_count = self.get_document_count(tid) if tid else 0
        api_calls = self.get_api_calls_today(tid) if tid else 0
        llm_tokens = self.get_llm_tokens_today(tid) if tid else 0

        # Export metriche Prometheus per dashboard SaaS.
        try:
            from agent_jira.metrics import TENANT_QUOTA_USAGE

            if tid:
                TENANT_QUOTA_USAGE.labels(
                    tenant_id=tid, quota_type="storage_mb", plan=plan
                ).set(storage_mb)
                TENANT_QUOTA_USAGE.labels(
                    tenant_id=tid, quota_type="documents", plan=plan
                ).set(doc_count)
                TENANT_QUOTA_USAGE.labels(
                    tenant_id=tid, quota_type="api_calls", plan=plan
                ).set(api_calls)
                TENANT_QUOTA_USAGE.labels(
                    tenant_id=tid, quota_type="llm_tokens", plan=plan
                ).set(llm_tokens)
        except Exception:
            pass

        return {
            "tenant_id": tid,
            "plan": plan,
            "usage": {
                "storage_mb": storage_mb,
                "documents": doc_count,
                "api_calls_today": api_calls,
                "llm_tokens_today": llm_tokens,
            },
            "limits": limits,
            "percent_used": {
                "storage_mb": _pct(storage_mb, limits.get("storage_mb", 0)),
                "documents": _pct(doc_count, limits.get("documents", 0)),
                "api_calls": _pct(api_calls, limits.get("api_calls_per_day", 0)),
            },
        }


def _pct(used: float, limit: float) -> float:
    if not limit or limit <= 0:
        return 0.0
    return round((used / limit) * 100, 1)


# Singleton
quota_tracker = QuotaTracker()
