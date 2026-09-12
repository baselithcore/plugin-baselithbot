"""Authenticated HTTP reverse proxy for the embedded dbview NestJS API.

Mounting strategy
-----------------
One FastAPI router at ``/api/dbview``. Every request under that prefix is
forwarded to the supervised Node child at ``http://127.0.0.1:<port>``,
re-rooted onto the upstream's native ``/api`` namespace::

    browser  →  /api/dbview/auth/me        (this router)
                              │ strip "/api/dbview", prepend "/api"
                              ▼
    upstream →  /api/auth/me               (NestJS, global prefix "api")

Central auth at the seam
------------------------
The router resolves the caller through the **shared auth chokepoint**
(``plugins.auth.api.get_current_user`` — Bearer / central API key /
refresh-cookie, tenant context bound as a side effect):

* authenticated → the central per-tab policy for ``(dbview, dbview)`` is
  enforced (403 on deny), then the identity is forwarded to the upstream as
  trusted gateway headers (see :mod:`plugins.dbview.identity`) so dbview's
  ``GatewayAuthGuard`` attaches the principal and JIT-mirrors the user;
* anonymous → the request is forwarded *without* identity and the upstream's
  own guards apply (``@Public`` endpoints such as ``/health`` and
  ``/auth/config`` respond; everything else 401s).

Inbound ``x-dbview-gateway-*`` headers are **always stripped** — a client can
never spoof the trusted identity, and the per-boot shared secret protects the
loopback upstream against direct access from other local processes.

The router is streaming end-to-end (``httpx`` + ``StreamingResponse``) so
multi-megabyte schema introspection payloads never buffer twice, and it
rewrites ``Set-Cookie`` paths (``/api/auth`` → ``/api/dbview/auth``) so the
standalone refresh flow keeps working when gateway mode is off.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Iterable

import httpx
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from core.auth.types import AuthRole, AuthUser

from .identity import (
    GATEWAY_SECRET_HEADER,
    GATEWAY_USER_HEADER,
    build_gateway_user_header,
    can_access_dbview_tab,
)
from .llm_governance import GOV_REQUEST_HEADERS, governed_request_headers
from .usage import USAGE_HEADER, report_upstream_usage

logger = logging.getLogger(__name__)


# Hop-by-hop headers (RFC 7230 §6.1) that must never cross a proxy, plus the
# trusted gateway headers a client must never smuggle through.
_HOP_BY_HOP_HEADERS: frozenset[str] = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "expect",
    }
)

_STRIPPED_REQUEST_HEADERS: frozenset[str] = (
    _HOP_BY_HOP_HEADERS
    | {
        "host",
        GATEWAY_USER_HEADER,
        GATEWAY_SECRET_HEADER,
    }
    # Governed-LLM headers are minted by this proxy per request; a client must
    # never smuggle one in (it would spoof the pinned provider/model/key).
    | GOV_REQUEST_HEADERS
)

# OPTIONS included so CORS preflights reach the NestJS controller logic.
_PROXIED_METHODS: tuple[str, ...] = (
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
    "HEAD",
)


def _current_user_dependency() -> Callable[..., Awaitable[AuthUser]]:
    """The shared central-auth chokepoint, with a resilient fallback.

    Uses ``plugins.auth.api.get_current_user`` (guideline: never
    hand-roll auth). If the auth plugin is not importable the fallback treats
    every caller as anonymous — the upstream then rejects everything but its
    ``@Public`` endpoints, which degrades closed.
    """
    try:
        from plugins.auth.api import get_current_user

        return get_current_user
    except Exception:  # noqa: BLE001 — auth plugin absent in this deployment
        logger.warning(
            "[dbview-proxy] plugins.auth unavailable — forwarding all traffic "
            "as anonymous (upstream guards still apply)"
        )

        async def _anonymous() -> AuthUser:
            return AuthUser(user_id="anonymous", roles={AuthRole.ANONYMOUS})

        return _anonymous


def _filter_request_headers(
    headers: Iterable[tuple[bytes, bytes]],
) -> list[tuple[str, str]]:
    """Drop hop-by-hop, ``Host`` and inbound gateway-identity headers.

    ``Host`` is removed so ``httpx`` regenerates it from the upstream URL;
    the gateway headers are removed so the trusted identity can only ever be
    minted by this proxy.
    """
    cleaned: list[tuple[str, str]] = []
    for raw_name, raw_value in headers:
        name = raw_name.decode("latin-1")
        if name.lower() in _STRIPPED_REQUEST_HEADERS:
            continue
        cleaned.append((name, raw_value.decode("latin-1")))
    return cleaned


def _filter_response_headers(
    headers: httpx.Headers, *, cookie_path_rewriter: Callable[[str], str]
) -> list[tuple[str, str]]:
    """Strip hop-by-hop headers and rewrite ``Set-Cookie`` paths.

    ``Content-Length`` is dropped because ``StreamingResponse`` re-derives it;
    forwarding a stale upstream value corrupts transformed bodies. The child's
    LLM-usage header is gateway-internal (already consumed by the cost report)
    and never reaches the browser.
    """
    cleaned: list[tuple[str, str]] = []
    for raw_name, raw_value in headers.raw:
        name = raw_name.decode("latin-1")
        lower = name.lower()
        value = raw_value.decode("latin-1")
        if lower in _HOP_BY_HOP_HEADERS or lower == "content-length":
            continue
        if lower == USAGE_HEADER:
            continue
        if lower == "set-cookie":
            value = _rewrite_set_cookie_path(value, cookie_path_rewriter)
        cleaned.append((name, value))
    return cleaned


def _rewrite_set_cookie_path(set_cookie: str, rewriter: Callable[[str], str]) -> str:
    """Apply ``rewriter`` to the ``Path=`` attribute of a Set-Cookie value."""
    parts = set_cookie.split(";")
    for index, part in enumerate(parts):
        stripped = part.strip()
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip().lower() == "path":
            parts[index] = f" Path={rewriter(value.strip())}"
            return ";".join(parts)
    return set_cookie


def _make_cookie_path_rewriter(
    proxy_prefix: str, upstream_api_prefix: str
) -> Callable[[str], str]:
    """Map upstream cookie paths onto the browser-visible proxy namespace.

    The upstream URL space ``/api/X`` is exposed to the browser as
    ``<proxy_prefix>/X`` (the forwarder strips the proxy prefix and prepends
    the upstream prefix), so a cookie scoped to ``/api/auth`` must become
    ``/api/dbview/auth`` — **not** ``/api/dbview/api/auth`` — or the browser
    never sends it back and the standalone refresh flow silently breaks.
    """
    proxy = proxy_prefix.rstrip("/")
    upstream = upstream_api_prefix.rstrip("/")

    def _rewrite(path: str) -> str:
        if not path or path == "/" or not path.startswith("/"):
            return path
        if path == proxy or path.startswith(proxy + "/"):
            return path  # already rewritten — idempotent
        if upstream and (path == upstream or path.startswith(upstream + "/")):
            suffix = path[len(upstream) :]
            return f"{proxy}{suffix}" if suffix else proxy or "/"
        return f"{proxy}{path}"

    return _rewrite


# Plugin-authored user-facing errors, localized en (default) + it per the
# platform backend-i18n rule; resolved from ``Accept-Language``.
_ERROR_MESSAGES: dict[str, dict[str, str]] = {
    "dbview_upstream_down": {
        "en": (
            "dbview NestJS API is not currently healthy. "
            "Check the plugin supervisor logs."
        ),
        "it": (
            "L'API NestJS di dbview non è al momento in salute. "
            "Controlla i log del supervisor del plugin."
        ),
    },
    "dbview_tab_denied": {
        "en": "Access to 'dbview:dbview' is not permitted",
        "it": "Accesso a 'dbview:dbview' non consentito",
    },
    "dbview_upstream_error": {
        "en": "upstream request failed: {exc}",
        "it": "richiesta verso l'upstream fallita: {exc}",
    },
}


def _locale(request: Request) -> str:
    """First supported language in ``Accept-Language`` (default ``en``)."""
    for part in request.headers.get("accept-language", "").split(","):
        code = part.split(";")[0].strip().lower()
        if code.startswith("it"):
            return "it"
        if code.startswith("en"):
            return "en"
    return "en"


def _msg(request: Request, code: str, **fmt: object) -> str:
    catalog = _ERROR_MESSAGES[code]
    text = catalog.get(_locale(request), catalog["en"])
    return text.format(**fmt) if fmt else text


def build_proxy_router(
    *,
    upstream_base_url_provider: Callable[[], str],
    healthy_provider: Callable[[], bool],
    gateway_secret_provider: Callable[[], str | None],
    proxy_prefix: str = "/api/dbview",
    upstream_api_prefix: str = "/api",
    request_timeout_s: float = 300.0,
) -> APIRouter:
    """Construct the authenticated reverse-proxy router.

    Args:
        upstream_base_url_provider: Returns the current ``http://host:port``
            of the Node child (indirection survives supervisor restarts).
        healthy_provider: ``True`` while the child accepts traffic; used to
            short-circuit with 503 instead of burning connections.
        gateway_secret_provider: Returns the per-boot shared secret injected
            into the child env, or ``None`` when gateway auth is disabled —
            in that case no identity headers are forwarded at all.
        proxy_prefix: Public mount path (must equal ``get_router_prefix()``).
        upstream_api_prefix: The upstream's own global prefix (``/api``).
        request_timeout_s: End-to-end forward timeout (matches the upstream
            deployment's 300 s reverse-proxy read timeout).

    Returns:
        An ``APIRouter`` ready for ``app.include_router(prefix=...)``.
    """
    router = APIRouter(tags=["dbview"])
    cookie_rewriter = _make_cookie_path_rewriter(proxy_prefix, upstream_api_prefix)
    upstream_prefix_clean = upstream_api_prefix.rstrip("/")
    current_user = _current_user_dependency()

    async def _forward(
        request: Request, sub_path: str, user: AuthUser
    ) -> StreamingResponse | JSONResponse:
        if not healthy_provider():
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "code": "dbview_upstream_down",
                    "detail": _msg(request, "dbview_upstream_down"),
                },
            )

        headers = _filter_request_headers(request.headers.raw)

        if user.is_authenticated:
            # Central per-tab policy (default-allow, admin/wildcard passes).
            if not can_access_dbview_tab(user):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "code": "dbview_tab_denied",
                        "detail": _msg(request, "dbview_tab_denied"),
                    },
                )
            secret = gateway_secret_provider()
            if secret:
                headers.append((GATEWAY_SECRET_HEADER, secret))
                headers.append((GATEWAY_USER_HEADER, build_gateway_user_header(user)))

        # Live per-request LLM governance: the operator's current dbview pin,
        # resolved fresh so a re-pin reaches the running child with no respawn.
        # Injected for every caller (the pin governs the plugin, not a user);
        # empty when unpinned. Inbound copies were stripped above (anti-spoof).
        headers.extend(governed_request_headers().items())

        upstream_base = upstream_base_url_provider().rstrip("/")
        normalised_path = sub_path.lstrip("/")
        if normalised_path:
            forwarded_path = f"{upstream_prefix_clean}/{normalised_path}"
        else:
            forwarded_path = upstream_prefix_clean or "/"
        target_url = f"{upstream_base}{forwarded_path}"
        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"

        forwarded_host = request.headers.get("host", "")
        headers.append(("X-Forwarded-Proto", request.url.scheme))
        if forwarded_host:
            headers.append(("X-Forwarded-Host", forwarded_host))
        headers.append(("X-Forwarded-Prefix", proxy_prefix))

        client_timeout = httpx.Timeout(request_timeout_s, connect=10.0)

        try:
            upstream_client = httpx.AsyncClient(timeout=client_timeout)
            stream_ctx = upstream_client.stream(
                request.method,
                target_url,
                headers=headers,
                content=request.stream(),
            )
            upstream_response = await stream_ctx.__aenter__()
        except httpx.HTTPError as exc:
            logger.warning(
                "[dbview-proxy] upstream connect failed (%s %s): %s",
                request.method,
                target_url,
                exc,
            )
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={
                    "code": "dbview_upstream_error",
                    "detail": _msg(request, "dbview_upstream_error", exc=exc),
                },
            )

        # The child reports what its LLM providers measured for this request.
        # Reported here — still inside the caller's request — so the host ledger
        # can attribute the spend to this plugin and to the authenticated user;
        # the header itself is internal telemetry and is stripped below.
        report_upstream_usage(upstream_response.headers)

        response_headers = _filter_response_headers(
            upstream_response.headers, cookie_path_rewriter=cookie_rewriter
        )

        async def body_iterator():
            try:
                async for chunk in upstream_response.aiter_raw():
                    yield chunk
            finally:
                await stream_ctx.__aexit__(None, None, None)
                await upstream_client.aclose()

        return StreamingResponse(
            body_iterator(),
            status_code=upstream_response.status_code,
            headers=dict(response_headers),
            media_type=upstream_response.headers.get("content-type"),
        )

    async def _proxy_root(
        request: Request,
        user: AuthUser = Depends(current_user),
    ) -> StreamingResponse | JSONResponse:
        # Bare ``GET /api/dbview`` reaches the upstream ``/api`` root instead
        # of 404-ing inside FastAPI.
        return await _forward(request, "", user)

    async def _proxy_path(
        request: Request,
        full_path: str,
        user: AuthUser = Depends(current_user),
    ) -> StreamingResponse | JSONResponse:
        return await _forward(request, full_path, user)

    # ``response_model=None`` is mandatory: FastAPI cannot infer a Pydantic
    # field from the ``StreamingResponse | JSONResponse`` union used to
    # short-circuit upstream failures with a structured error.
    router.add_api_route(
        "",
        _proxy_root,
        methods=list(_PROXIED_METHODS),
        include_in_schema=False,
        response_model=None,
    )
    router.add_api_route(
        "/{full_path:path}",
        _proxy_path,
        methods=list(_PROXIED_METHODS),
        include_in_schema=False,
        response_model=None,
    )

    return router


__all__ = ["build_proxy_router"]
