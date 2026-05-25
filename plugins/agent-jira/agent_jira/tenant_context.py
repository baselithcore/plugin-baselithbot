"""
Tenant context management per multi-tenancy.

Il tenant corrente viene propagato tramite contextvars,
analogo al pattern già usato in CostController.
Il TenantMiddleware estrae il tenant_id dal JWT (claim "tenant_id"),
dall'header X-Tenant-ID, o dal subdomain.
"""

from __future__ import annotations

import contextvars
import logging
from dataclasses import dataclass
from typing import Optional

import jwt as pyjwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from pathlib import Path

from agent_jira.config import SECRET_KEY

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TenantInfo:
    """Informazioni sul tenant corrente nella richiesta."""

    tenant_id: str
    slug: Optional[str] = None
    plan: Optional[str] = None


_tenant_context: contextvars.ContextVar[Optional[TenantInfo]] = contextvars.ContextVar(
    "tenant_info", default=None
)


def get_current_tenant() -> Optional[TenantInfo]:
    """Restituisce il tenant corrente della richiesta, o None se single-tenant."""
    return _tenant_context.get()


def get_current_tenant_id() -> Optional[str]:
    """Shortcut per ottenere solo l'ID del tenant corrente."""
    tenant = _tenant_context.get()
    return tenant.tenant_id if tenant else None


def set_current_tenant(tenant: Optional[TenantInfo]) -> contextvars.Token:
    """Imposta il tenant corrente nel context. Restituisce il token per il reset."""
    return _tenant_context.set(tenant)


def require_tenant_id() -> str:
    """Restituisce il tenant_id corrente o solleva un errore se non presente."""
    tenant = _tenant_context.get()
    if tenant is None:
        raise RuntimeError("Tenant context non inizializzato. Richiesta senza tenant.")
    return tenant.tenant_id


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware che estrae e imposta il tenant context per ogni richiesta.

    Ordine di risoluzione:
    1. Claim JWT "tenant_id" (se presente nell'auth già processato)
    2. Header X-Tenant-ID
    3. None (backward compatible, single-tenant mode)

    In modalità MULTI_TENANT_REQUIRED=true, rifiuta richieste senza tenant
    (eccetto health checks e rotte pubbliche).
    """

    EXEMPT_PREFIXES = ("/health", "/docs", "/openapi.json", "/static")

    async def dispatch(self, request: Request, call_next):
        # Skip per rotte esenti (nessun tenant context necessario)
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return await call_next(request)

        tenant_id = self._resolve_tenant_id(request)

        if tenant_id:
            tenant_info = TenantInfo(tenant_id=tenant_id)
            token = set_current_tenant(tenant_info)
        else:
            # Nessun tenant identificato — prosegui senza tenant context.
            token = set_current_tenant(None)

        # Per il labeling Prometheus usiamo il template di route (se FastAPI
        # l'ha risolta) per evitare esplosione cardinalità su path variabili.
        import time

        start = time.perf_counter()
        status_code = 500

        try:
            # Tracking API call per quota
            if tenant_id:
                try:
                    from agent_jira.quotas import quota_tracker

                    quota_tracker.track_api_call(tenant_id)
                except Exception:
                    pass  # Non bloccare la request per errori di tracking

            response = await call_next(request)
            status_code = response.status_code
            if tenant_id:
                response.headers["X-Tenant-ID"] = tenant_id
            return response
        finally:
            # Sprint 10: metriche per-tenant.
            try:
                from agent_jira.metrics import (
                    TENANT_HTTP_ERRORS_TOTAL,
                    TENANT_HTTP_LATENCY_SECONDS,
                    TENANT_HTTP_REQUESTS_TOTAL,
                )

                # Route template se disponibile, altrimenti path bucketizzato.
                route = getattr(request.scope.get("route"), "path", None) or path
                method = request.method
                status_bucket = f"{status_code // 100}xx"
                labels_tid = tenant_id or "-"

                TENANT_HTTP_REQUESTS_TOTAL.labels(
                    tenant_id=labels_tid,
                    method=method,
                    route=route,
                    status_bucket=status_bucket,
                ).inc()
                TENANT_HTTP_LATENCY_SECONDS.labels(
                    tenant_id=labels_tid, route=route
                ).observe(time.perf_counter() - start)
                if status_code >= 400:
                    TENANT_HTTP_ERRORS_TOTAL.labels(
                        tenant_id=labels_tid,
                        route=route,
                        status=str(status_code),
                    ).inc()
            except Exception:
                pass  # Metriche mai bloccanti

            _tenant_context.reset(token)

    def _resolve_tenant_id(self, request: Request) -> Optional[str]:
        """
        Risolve il tenant_id della richiesta con verifica di coerenza contro il DB.

        Priorità:
          1. JWT (sorgente autoritativa): `tenant_id` del claim DEVE coincidere con
             `users.tenant_id` del DB per lo user_id del claim. Mismatch → None
             (= accesso negato in modalità MULTI_TENANT_REQUIRED).
          2. Header X-Tenant-ID solo come fallback per chiamate server-to-server
             (job, API key) dove non c'è un JWT user.

        Questa verifica chiude il vettore di JWT tampering: un attaccante che
        modifichi `tenant_id` nel payload (senza breakare la firma) non può
        accedere ai dati del tenant target perché il DB smaschera il mismatch.
        """
        # 1. JWT — sorgente autoritativa per utenti loggati
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer ") and SECRET_KEY:
            token = auth_header[7:].strip()
            try:
                payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                claim_tenant_id = payload.get("tenant_id")
                claim_user_id = payload.get("sub") or payload.get("uid")

                if claim_tenant_id and claim_user_id:
                    # Verifica coerenza JWT ↔ DB. Import locale per evitare
                    # cicli all'import time e per non pagare il costo su request
                    # server-to-server (senza JWT user).
                    try:
                        from agent_jira.db.users import get_user_by_id

                        user = get_user_by_id(str(claim_user_id))
                        if not user:
                            logger.warning(
                                "JWT user_id=%s non presente in DB", claim_user_id
                            )
                            return None
                        db_tenant_id = user.get("tenant_id")
                        if str(db_tenant_id) != str(claim_tenant_id):
                            logger.warning(
                                "JWT tampering rilevato: claim tenant_id=%s ma "
                                "DB tenant_id=%s per user %s — accesso negato",
                                claim_tenant_id,
                                db_tenant_id,
                                claim_user_id,
                            )
                            return None
                        return str(db_tenant_id).strip()
                    except Exception as exc:
                        # Se la verifica DB fallisce (DB down, ecc.) preferiamo
                        # fail-closed in multi-tenant mode.
                        logger.warning("Verifica coerenza JWT/DB fallita: %s", exc)
                        return None
            except pyjwt.PyJWTError:
                pass  # Token invalido/scaduto

        # 2. Header X-Tenant-ID — solo per flussi server-to-server senza JWT user
        header_value = request.headers.get("x-tenant-id") or request.headers.get(
            "X-Tenant-ID"
        )
        if header_value:
            return header_value.strip()

        return None


def get_tenant_documents_root(base_root: Path) -> Path:
    """
    Restituisce la documents root per il tenant corrente.
    In single-tenant mode restituisce la root base invariata.
    In multi-tenant mode restituisce base_root / tenant_id.
    """
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        return base_root
    tenant_root = base_root / tenant_id
    tenant_root.mkdir(parents=True, exist_ok=True)
    return tenant_root


def get_tenant_cache_prefix(base_prefix: str) -> str:
    """Restituisce un prefix cache con namespace tenant se presente."""
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        return base_prefix
    return f"{base_prefix}:t:{tenant_id}"


def get_tenant_collection_suffix() -> str:
    """Restituisce un suffisso per collection/graph name per il tenant corrente."""
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        return ""
    return f"_{tenant_id}"
