"""HTTP reverse proxy router for the embedded dbview NestJS API.

Mounting strategy
-----------------
The plugin mounts a single FastAPI router at ``/api/dbview``.  Every
request landing under that prefix is forwarded to the supervised Node
child at ``http://127.0.0.1:<port>``, transparently rewriting the URL
path so that the downstream backend keeps its native ``/api/...``
namespace.

::

    browser  →  /api/dbview/auth/login   (proxy router)
                                │  strip "/api/dbview"
                                ▼
    proxy    →  /api/auth/login          (NestJS app, global prefix "api")

Why a custom router (and not Starlette ``Mount``)
-------------------------------------------------
* We need to integrate with BaselithCore's lazy plugin activation
  middleware, which discovers prefixes via AST on ``get_router_prefix``
  — that contract requires an ``APIRouter`` literal, not a ``Mount``.
* We need precise control over hop-by-hop header stripping (RFC 7230 §6.1)
  and Set-Cookie ``Path`` rewriting so the JWT refresh cookie keeps
  flowing under the new prefix.
* We need to surface upstream-down conditions as ``503`` JSON the host
  can shape (matches the activation middleware error envelope).

The router is **streaming**: it uses ``httpx.AsyncClient.stream`` and
``StreamingResponse`` end-to-end so large schema introspection payloads
(megabytes of compressed JSON) never sit in memory twice. WebSocket
upgrades are not yet forwarded — dbview does not use them today; the
plugin will be revisited if a WS endpoint is added upstream.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Iterable

import httpx
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)


# Hop-by-hop headers (RFC 7230 §6.1) and Transfer-Encoding controls that
# must NEVER be forwarded blindly across a proxy.
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


# Methods accepted by the catch-all route. ``OPTIONS`` is intentionally
# included so CORS preflights reach the NestJS controller logic.
_PROXIED_METHODS: tuple[str, ...] = (
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
    "HEAD",
)


def _filter_request_headers(
    headers: Iterable[tuple[bytes, bytes]],
) -> list[tuple[str, str]]:
    """Drop hop-by-hop + Host headers before forwarding the request.

    ``Host`` is removed so ``httpx`` regenerates it from the upstream URL
    — keeping the original ``Host`` would point the NestJS adapter at the
    public hostname and break virtual-host routing logic in the future.
    """
    cleaned: list[tuple[str, str]] = []
    for raw_name, raw_value in headers:
        name = raw_name.decode("latin-1")
        lower = name.lower()
        if lower in _HOP_BY_HOP_HEADERS or lower == "host":
            continue
        cleaned.append((name, raw_value.decode("latin-1")))
    return cleaned


def _filter_response_headers(
    headers: httpx.Headers, *, cookie_path_rewriter: Callable[[str], str]
) -> list[tuple[str, str]]:
    """Strip hop-by-hop headers and rewrite ``Set-Cookie`` paths.

    The dbview backend sets the refresh-token cookie with
    ``Path=/api/auth`` so the browser only ships it on the auth refresh
    endpoint. Once we move behind the plugin prefix the browser-visible
    URL is ``/api/dbview/api/auth/refresh``; we rewrite the cookie path
    on the wire to match that, otherwise the refresh flow silently fails
    after the first token rotation.
    """
    cleaned: list[tuple[str, str]] = []
    for raw_name, raw_value in headers.raw:
        name = raw_name.decode("latin-1")
        lower = name.lower()
        value = raw_value.decode("latin-1")
        if lower in _HOP_BY_HOP_HEADERS:
            continue
        # FastAPI's StreamingResponse rebuilds Content-Length from the
        # actual body; forwarding a stale upstream value will corrupt
        # responses whose bodies were transformed (e.g. gzip rewritten
        # by intermediate middleware).
        if lower == "content-length":
            continue
        if lower == "set-cookie":
            value = _rewrite_set_cookie_path(value, cookie_path_rewriter)
        cleaned.append((name, value))
    return cleaned


def _rewrite_set_cookie_path(set_cookie: str, rewriter: Callable[[str], str]) -> str:
    """Apply ``rewriter`` to the ``Path=`` attribute of a Set-Cookie value.

    Cookie attribute matching is case-insensitive and tolerant of extra
    whitespace, mirroring the parser shape used by browser engines.
    """
    parts = [p for p in set_cookie.split(";")]
    for index, part in enumerate(parts):
        stripped = part.strip()
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip().lower() == "path":
            parts[index] = f" Path={rewriter(value.strip())}"
            return ";".join(parts)
    return set_cookie


def _make_cookie_path_rewriter(prefix: str) -> Callable[[str], str]:
    """Return a function that prepends ``prefix`` to non-rewritten paths.

    ``/`` is left alone (cookies scoped to the whole site stay that way).
    Already-prefixed paths are short-circuited so repeated rewrites are
    idempotent.
    """
    cleaned_prefix = prefix.rstrip("/")

    def _rewrite(path: str) -> str:
        if not path or path == "/":
            return path
        if path.startswith(cleaned_prefix + "/") or path == cleaned_prefix:
            return path
        if not path.startswith("/"):
            return path
        return f"{cleaned_prefix}{path}"

    return _rewrite


def build_proxy_router(
    *,
    upstream_base_url_provider: Callable[[], str],
    healthy_provider: Callable[[], bool],
    proxy_prefix: str = "/api/dbview",
    upstream_api_prefix: str = "/api",
    request_timeout_s: float = 300.0,
) -> APIRouter:
    """Construct the reverse-proxy router.

    Args:
        upstream_base_url_provider: Callable returning the current
            ``http://host:port`` of the Node child. Indirection lets the
            supervisor swap ports across restarts.
        healthy_provider: Callable returning ``True`` while the child
            is accepting traffic. Used to short-circuit requests with
            HTTP 503 instead of blowing connection budget on a downed
            backend.
        proxy_prefix: Path the router is mounted under (must match the
            ``get_router_prefix()`` value the plugin advertises).
        upstream_api_prefix: Path the dbview API itself lives under
            (``app.setGlobalPrefix('api')`` → ``/api``).
        request_timeout_s: End-to-end forward timeout; matches the
            standalone deployment's nginx ``proxy_read_timeout``.

    Returns:
        An ``APIRouter`` ready for ``app.include_router(prefix=...)``.
    """
    router = APIRouter(tags=["dbview"])
    cookie_rewriter = _make_cookie_path_rewriter(proxy_prefix)
    upstream_prefix_clean = upstream_api_prefix.rstrip("/")

    async def _forward(
        request: Request, sub_path: str
    ) -> StreamingResponse | JSONResponse:
        if not healthy_provider():
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "code": "dbview_upstream_down",
                    "detail": (
                        "dbview NestJS API is not currently healthy. "
                        "Check the plugin supervisor logs."
                    ),
                },
            )

        upstream_base = upstream_base_url_provider().rstrip("/")
        normalised_path = sub_path.lstrip("/")
        # Preserve the upstream's "/api" global prefix in the forwarded URL.
        if normalised_path:
            forwarded_path = f"{upstream_prefix_clean}/{normalised_path}"
        else:
            forwarded_path = upstream_prefix_clean or "/"
        query = request.url.query
        target_url = f"{upstream_base}{forwarded_path}"
        if query:
            target_url = f"{target_url}?{query}"

        headers = _filter_request_headers(request.headers.raw)
        # Tell the backend what its public-facing prefix is, so any code
        # that wants to mint absolute self-links can produce URLs that
        # actually resolve through the proxy. dbview does not currently
        # rely on these but the hooks are cheap, standard, and futureproof.
        forwarded_proto = request.url.scheme
        forwarded_host = request.headers.get("host", "")
        headers.append(("X-Forwarded-Proto", forwarded_proto))
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
                    "detail": f"upstream request failed: {exc}",
                },
            )

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
    ) -> StreamingResponse | JSONResponse:
        # Root passthrough so a bare ``GET /api/dbview`` reaches the
        # upstream ``/api`` root rather than 404-ing inside FastAPI.
        return await _forward(request, "")

    async def _proxy_path(
        request: Request, full_path: str
    ) -> StreamingResponse | JSONResponse:
        return await _forward(request, full_path)

    # ``response_model=None`` is mandatory: FastAPI cannot infer a
    # Pydantic field from the ``StreamingResponse | JSONResponse`` union
    # we use to short-circuit upstream failures with a structured error.
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


__all__ = [
    "build_proxy_router",
]


# Re-export so static type-checkers in plugin tests have a stable
# entry point for the helper used by the dispatcher above.
ForwardCallback = Callable[[Request, str], Awaitable[StreamingResponse | JSONResponse]]
