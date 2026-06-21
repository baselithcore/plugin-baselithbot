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
from llm_wiki.auth._core_bridge import decode_core_token
from llm_wiki.auth.tenant_context import (
    TenantInfo,
    reset_tenant,
    set_current_tenant,
)

logger = logging.getLogger(__name__)


def _bearer_from_headers(headers: list[tuple[bytes, bytes]]) -> str | None:
    """Extract a ``Bearer`` token from raw ASGI headers (case-insensitive)."""
    for key, value in headers:
        if key.lower() == b"authorization":
            text = value.decode("latin-1")
            if text.lower().startswith("bearer "):
                return text[7:].strip() or None
    return None


class TenantMiddleware:
    """Bind the wiki tenant (== authenticated ``user_id``) from the central
    access token, so every downstream DB checkout scopes RLS to the caller.

    Pure ASGI (CLAUDE.md mandate — no extra ``BaseHTTPMiddleware`` task that
    would break streaming/cancellation). Identity comes solely from the central
    ``auth`` plugin's token: there is no ``X-Tenant-ID`` trust path (a header
    must never let an authenticated caller choose another tenant). The tenant
    contextvar is set before the inner app runs and reset in ``finally`` so it
    never leaks across requests; :mod:`llm_wiki.db.connection` reads it on each
    pool checkout to set the ``app.current_tenant_id`` RLS GUC.

    Knowledge base (filesystem + Qdrant) is SHARED and not tenant-scoped, so
    public read-only prefixes skip tenant resolution entirely.
    """

    EXEMPT_PREFIXES = (
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/static",
        # Public read-only — wiki is a SHARED resource.
        "/api/wiki",
        "/api/groups",
        "/api/status",
        "/api/branding",
        # Public embed: the router sets tenant context manually after its own
        # token verification (no central JWT on the iframe call).
        "/api/embed",
    )

    def __init__(self, app: object) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: object, send: object) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)  # type: ignore[operator]
            return

        path = scope.get("path", "") or ""
        token: str | None = None
        if not any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            token = _bearer_from_headers(scope.get("headers") or [])
        claims = decode_core_token(token) if token else None
        tenant_id = (
            str(claims.get("sub") or claims.get("uid") or "") or None
            if claims
            else None
        )

        ctx_token = (
            set_current_tenant(TenantInfo(tenant_id=tenant_id)) if tenant_id else None
        )
        try:
            await self.app(scope, receive, send)  # type: ignore[operator]
        finally:
            if ctx_token is not None:
                reset_tenant(ctx_token)


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
            if (
                path == prefix
                or path.startswith(prefix + "/")
                or path.startswith(prefix + "?")
            ):
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
