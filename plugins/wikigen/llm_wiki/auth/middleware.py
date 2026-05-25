"""Middleware HTTP: TenantMiddleware + SecurityHeadersMiddleware.

Pattern allineato a ``agent-jira/app/tenant_context.py:TenantMiddleware``
+ ``app/security.py:SecurityHeadersMiddleware``.

Order di mount (in :mod:`main`):

1. ``CORSMiddleware``
2. ``SecurityHeadersMiddleware``
3. ``TenantMiddleware``  (deve girare DOPO che la response è formata
   per poter aggiungere ``X-Tenant-ID``, e PRIMA del routing per
   popolare il contextvar)

TenantMiddleware
================

Resolution priority:

1. JWT ``Authorization: Bearer <token>`` — sorgente autoritativa per
   utenti loggati. ``claim.tenant_id`` DEVE coincidere con
   ``users.tenant_id`` del DB per ``claim.sub`` (anti-tampering: chi
   modifica il claim senza rompere la firma viene smascherato).
2. ``X-Tenant-ID`` header — fallback solo per chiamate server-to-server
   (job, API key) dove non c'è JWT user. Default OFF: rifiutato se
   ``MULTI_TENANT_REQUIRED=true`` e nessun JWT.
3. ``None`` — proceed senza tenant. Le rotte tenant-scoped (chat,
   memories, conversations) risponderanno 401/403; rotte pubbliche
   (status, branding, wiki shared) continuano a funzionare.

EXEMPT_PREFIXES: rotte pubbliche di sistema (health, docs, branding,
wiki read-only) — non richiedono tenant context.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from llm_wiki import config
from llm_wiki.auth.tenant_context import (
    TenantInfo,
    reset_tenant,
    set_current_tenant,
)
from llm_wiki.auth.tokens import decode_access_token

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Estrae tenant dal JWT, verifica anti-tampering, popola contextvar.

    Reset garantito al ``finally`` — anche se l'handler solleva, il
    contextvar non resta sporco per la prossima request sullo stesso
    asyncio task / thread.
    """

    EXEMPT_PREFIXES = (
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/static",
        # Public read-only — wiki è risorsa SHARED.
        "/api/wiki",
        "/api/groups",
        "/api/status",
        "/api/branding",
        # Auth endpoints: tenant context popolato DOPO login.
        "/auth/login",
        "/auth/register",
        "/auth/refresh",
        # Embed pubblico: tenant context settato manualmente dal router
        # dopo verify_token. JWT non presente → middleware lascerebbe
        # contextvar a None e i CRUD downstream fallirebbero RLS.
        "/api/embed",
    )

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return await call_next(request)

        tenant_id = self._resolve_tenant_id(request)
        tenant_info = TenantInfo(tenant_id=tenant_id) if tenant_id else None
        token = set_current_tenant(tenant_info)

        try:
            response = await call_next(request)
            if tenant_id:
                response.headers["X-Tenant-ID"] = tenant_id
            return response
        finally:
            reset_tenant(token)

    def _resolve_tenant_id(self, request: Request) -> str | None:
        """Vedi modulo docstring per la priorità completa."""
        # 1. JWT — sorgente autoritativa.
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            jwt_token = auth_header[7:].strip()
            payload = decode_access_token(jwt_token)
            if payload:
                claim_tenant_id = payload.get("tenant_id")
                claim_user_id = payload.get("sub") or payload.get("uid")
                if claim_tenant_id and claim_user_id:
                    verified = self._verify_jwt_tenant(str(claim_user_id), str(claim_tenant_id))
                    if verified:
                        return verified
                    # JWT tampering — non fallback su header. Fail closed.
                    return None

        # 2. Header server-to-server — solo se NON c'è JWT (anti-bypass).
        header_value = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-ID")
        if header_value:
            return header_value.strip() or None

        return None

    def _verify_jwt_tenant(self, claim_user_id: str, claim_tenant_id: str) -> str | None:
        """Verifica DB: ``users.tenant_id`` per ``claim.sub`` deve
        coincidere con ``claim.tenant_id``. Fail-closed su qualsiasi
        errore (DB down → meglio negare che passare un tampered claim).

        In più — RBAC multi-wiki — se l'utente ha ``user_domain_grants``
        popolati e ``APP_DOMAIN`` non è tra essi, la request è respinta
        (no leak cross-wiki). Grants vuoti = back-compat: nessun
        enforcement, ogni utente vede il dominio del processo.
        """
        try:
            from llm_wiki.db.users import get_user_by_id

            user = get_user_by_id(claim_user_id)
            if not user:
                logger.warning(
                    "[auth] JWT user_id=%s non presente in DB",
                    claim_user_id,
                )
                return None
            db_tenant_id = str(user.get("tenant_id") or "")
            if db_tenant_id != claim_tenant_id:
                logger.warning(
                    "[auth] JWT tampering: claim tid=%s, DB tid=%s, user=%s",
                    claim_tenant_id,
                    db_tenant_id,
                    claim_user_id,
                )
                return None
            # Multi-wiki gate. Solo se APP_DOMAIN configurato (engine
            # in modalità setup → bypass).
            app_domain = (config.APP_DOMAIN or "").strip()
            if app_domain:
                try:
                    from llm_wiki.db.roles import get_user_domain_grants

                    grants = get_user_domain_grants(claim_user_id)
                    if grants and app_domain not in grants:
                        logger.warning(
                            "[auth] domain access denied: user=%s domain=%s grants=%s",
                            claim_user_id,
                            app_domain,
                            grants,
                        )
                        return None
                except Exception as exc:
                    # Default fail-closed: se il DB è giù, NON sappiamo
                    # se l'utente ha grant per il dominio corrente —
                    # rifiutiamo. Override via env ``DOMAIN_GATE_FAIL_OPEN``
                    # (sconsigliato in produzione).
                    logger.warning("[auth] domain grant lookup failed: %s", exc)
                    if not config.DOMAIN_GATE_FAIL_OPEN:
                        return None
            return db_tenant_id
        except Exception as exc:
            logger.warning("[auth] JWT/DB verify failed (fail-closed): %s", exc)
            return None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Header di sicurezza standard 2026.

    Toggleabili via env (``SECURITY_HEADERS_ENABLED``, ``ENABLE_HSTS``,
    ``CONTENT_SECURITY_POLICY``). HSTS OFF di default — abilitalo solo
    dietro HTTPS terminator, altrimenti rompe lo sviluppo locale.

    Path-aware embed relaxation
    ===========================

    Sui path serviti come iframe-embeddable (``/embed/...`` mini-app +
    ``/embed.js`` widget loader) NON applichiamo ``X-Frame-Options:
    DENY`` né ``frame-ancestors 'none'``: la funzione del bundle è
    proprio quella di girare dentro un iframe su un sito terzo.
    L'enforcement di "chi può embedare" sta nel layer applicativo
    (``origin_allowlist`` su ``embeds.token_hash`` — vedi mig 017).
    """

    EMBED_PATH_PREFIXES = ("/embed", "/embed.js")

    @classmethod
    def _is_embed_path(cls, path: str) -> bool:
        # Esatto match `/embed.js` o `/embed` (anche con trailing slash o
        # sotto-path tipo `/embed/index.html`). Esclude `/embedXXX` non-/.
        for prefix in cls.EMBED_PATH_PREFIXES:
            if path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "?"):
                return True
        return False

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        if not config.SECURITY_HEADERS_ENABLED:
            return response

        is_embed = self._is_embed_path(request.url.path)

        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        if not is_embed:
            h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "same-origin")
        h.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if config.CONTENT_SECURITY_POLICY and not is_embed:
            h.setdefault("Content-Security-Policy", config.CONTENT_SECURITY_POLICY)
        # Per i path embed scriviamo una CSP rilassata che permette
        # l'iframe da qualunque origine (controllo applicativo via
        # token+allowlist) ma mantiene gli altri vincoli baseline.
        if is_embed and config.SECURITY_HEADERS_ENABLED:
            h.setdefault(
                "Content-Security-Policy",
                (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: blob: https:; "
                    "font-src 'self' data:; "
                    "connect-src 'self'; "
                    "frame-ancestors *; "
                    "base-uri 'self'; "
                    "object-src 'none'"
                ),
            )
        if config.ENABLE_HSTS:
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        return response


class EmbedCORSMiddleware(BaseHTTPMiddleware):
    """CORS permissivo per ``/api/embed/*`` (token-authenticated, no cookie).

    Lo SPA (e i siti terzi che usano direttamente l'API senza iframe)
    devono poter chiamare ``/api/embed/chat`` cross-origin. La sicurezza
    NON viene da CORS ma dal layer applicativo:

    - ``embed_token`` plaintext in body (unguessable, sha256 lookup).
    - ``origin_allowlist`` per token: verify_token rifiuta richieste
      con ``Origin`` non in allowlist.
    - Rate-limit per ``(embed_id, ip)``.

    ACAO=* è safe perché NON usiamo credentials (token in body, no
    cookies). ``Access-Control-Allow-Credentials`` resta unset di
    proposito — abilitarlo richiederebbe echo-origin invece di ``*``.

    Mount before ``CORSMiddleware`` (statico per SPA) così le response
    per ``/api/embed/*`` non ereditano restrizioni dello SPA.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path
        if not path.startswith("/api/embed"):
            return await call_next(request)

        if request.method == "OPTIONS":
            return Response(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Max-Age": "86400",
                    "Vary": "Origin",
                },
            )

        response: Response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers.setdefault("Vary", "Origin")
        return response


__all__ = ["TenantMiddleware", "SecurityHeadersMiddleware", "EmbedCORSMiddleware"]
