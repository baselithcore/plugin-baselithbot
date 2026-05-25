"""Unit tests for the dbview reverse-proxy helpers and router shape."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.dbview.proxy_router import (
    _filter_request_headers,
    _filter_response_headers,
    _make_cookie_path_rewriter,
    _rewrite_set_cookie_path,
    build_proxy_router,
)


# ---------------------------------------------------------------------------
# Header / cookie helpers
# ---------------------------------------------------------------------------


def test_filter_request_headers_drops_hop_by_hop_and_host():
    raw = [
        (b"host", b"public.example.com"),
        (b"authorization", b"Bearer abc"),
        (b"connection", b"keep-alive"),
        (b"keep-alive", b"timeout=5"),
        (b"content-type", b"application/json"),
        (b"x-request-id", b"req-1"),
    ]
    filtered = _filter_request_headers(raw)
    keys = {name.lower() for name, _ in filtered}
    assert "host" not in keys, "Host must be stripped so httpx regenerates it"
    assert "connection" not in keys
    assert "keep-alive" not in keys
    assert "authorization" in keys
    assert "content-type" in keys
    assert "x-request-id" in keys


def test_cookie_path_rewriter_prefixes_unprefixed_paths():
    rewrite = _make_cookie_path_rewriter("/api/dbview")
    assert rewrite("/api/auth") == "/api/dbview/api/auth"
    # Site-wide cookies are left alone — narrowing them would be surprising.
    assert rewrite("/") == "/"
    # Idempotency: already-prefixed paths stay untouched.
    assert rewrite("/api/dbview/api/auth") == "/api/dbview/api/auth"
    # Relative paths (browsers should never send these but be permissive).
    assert rewrite("api/auth") == "api/auth"


def test_rewrite_set_cookie_path_preserves_other_attributes():
    rewrite = _make_cookie_path_rewriter("/api/dbview")
    raw = (
        "dbview_refresh=tok-abc; Path=/api/auth; HttpOnly; "
        "Secure; SameSite=Strict; Max-Age=2592000"
    )
    rewritten = _rewrite_set_cookie_path(raw, rewrite)
    assert "Path=/api/dbview/api/auth" in rewritten
    assert "HttpOnly" in rewritten
    assert "Secure" in rewritten
    assert "SameSite=Strict" in rewritten
    assert "Max-Age=2592000" in rewritten


def test_rewrite_set_cookie_path_is_case_insensitive_for_path_attr():
    rewrite = _make_cookie_path_rewriter("/api/dbview")
    raw = "k=v; path=/api/auth; httponly"
    rewritten = _rewrite_set_cookie_path(raw, rewrite)
    assert "Path=/api/dbview/api/auth" in rewritten


def test_filter_response_headers_drops_hop_by_hop_and_content_length():
    rewrite = _make_cookie_path_rewriter("/api/dbview")
    headers = httpx.Headers(
        [
            ("content-type", "application/json"),
            ("content-length", "123"),
            ("transfer-encoding", "chunked"),
            ("set-cookie", "dbview_refresh=tok; Path=/api/auth; HttpOnly"),
        ]
    )
    filtered = _filter_response_headers(headers, cookie_path_rewriter=rewrite)
    keys = {name.lower() for name, _ in filtered}
    assert "content-length" not in keys, "stale Content-Length corrupts streaming bodies"
    assert "transfer-encoding" not in keys
    # Set-Cookie path is rewritten in-place.
    cookies = [value for name, value in filtered if name.lower() == "set-cookie"]
    assert any("Path=/api/dbview/api/auth" in c for c in cookies)


# ---------------------------------------------------------------------------
# Router behaviour with a mocked upstream
# ---------------------------------------------------------------------------


class _StubResponse:
    """Pseudo-httpx Response satisfying the proxy iteration contract."""

    def __init__(
        self,
        *,
        status_code: int = 200,
        headers: list[tuple[str, str]] | None = None,
        body: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self.headers = httpx.Headers(headers or [])
        self._body = body

    async def aiter_raw(self):
        yield self._body


class _StubStreamCtx:
    def __init__(self, response: _StubResponse) -> None:
        self._response = response
        self.aborted = False

    async def __aenter__(self) -> _StubResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.aborted = True


def _install_stub_client(response: _StubResponse) -> dict[str, Any]:
    """Patch httpx.AsyncClient so the proxy router talks to our stub.

    Returns a dict the caller can inspect after the request runs:
    ``method``/``url``/``headers`` of the captured upstream call.
    """
    captured: dict[str, Any] = {}

    stream_ctx = _StubStreamCtx(response)

    class _StubClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.timeout = kwargs.get("timeout")

        async def __aenter__(self) -> "_StubClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            pass

        async def aclose(self) -> None:
            captured["closed"] = True

        def stream(self, method: str, url: str, **kwargs: Any) -> _StubStreamCtx:
            captured["method"] = method
            captured["url"] = url
            captured["headers"] = kwargs.get("headers")
            return stream_ctx

    patcher = patch("plugins.dbview.proxy_router.httpx.AsyncClient", _StubClient)
    captured["_patcher"] = patcher
    captured["_stream_ctx"] = stream_ctx
    return captured


def _build_app(healthy: bool = True, upstream: str = "http://127.0.0.1:65000") -> FastAPI:
    app = FastAPI()
    router = build_proxy_router(
        upstream_base_url_provider=lambda: upstream,
        healthy_provider=lambda: healthy,
        proxy_prefix="/api/dbview",
    )
    app.include_router(router, prefix="/api/dbview")
    return app


def test_proxy_returns_503_when_upstream_unhealthy():
    app = _build_app(healthy=False)
    with TestClient(app) as client:
        resp = client.get("/api/dbview/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == "dbview_upstream_down"


def test_proxy_forwards_url_with_global_api_prefix():
    response = _StubResponse(
        status_code=200,
        headers=[("content-type", "application/json")],
        body=b'{"ok":true}',
    )
    captured = _install_stub_client(response)
    captured["_patcher"].start()
    try:
        app = _build_app(healthy=True, upstream="http://127.0.0.1:65000")
        with TestClient(app) as client:
            resp = client.get("/api/dbview/health?probe=1")
    finally:
        captured["_patcher"].stop()

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    # Plugin prefix stripped, upstream "/api" preserved, query forwarded.
    assert captured["url"] == "http://127.0.0.1:65000/api/health?probe=1"
    assert captured["method"] == "GET"
    # X-Forwarded-* hints added (case preserved).
    header_names = {name for name, _ in captured["headers"]}
    assert "X-Forwarded-Prefix" in header_names


def test_proxy_rewrites_set_cookie_path():
    response = _StubResponse(
        status_code=200,
        headers=[
            ("content-type", "application/json"),
            (
                "set-cookie",
                "dbview_refresh=abc; Path=/api/auth; HttpOnly; SameSite=Strict",
            ),
        ],
        body=b"{}",
    )
    captured = _install_stub_client(response)
    captured["_patcher"].start()
    try:
        app = _build_app(healthy=True)
        with TestClient(app) as client:
            resp = client.post("/api/dbview/auth/refresh")
    finally:
        captured["_patcher"].stop()

    assert resp.status_code == 200
    cookie_header = resp.headers.get("set-cookie", "")
    assert "Path=/api/dbview/api/auth" in cookie_header
    # Original attributes preserved.
    assert "HttpOnly" in cookie_header
    assert "SameSite=Strict" in cookie_header


def test_proxy_502s_when_upstream_connect_fails():
    captured: dict[str, Any] = {}

    class _ExplodingClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def aclose(self) -> None:
            captured["closed"] = True

        def stream(self, method: str, url: str, **kwargs: Any):
            class _Ctx:
                async def __aenter__(_self):
                    raise httpx.ConnectError(f"refused: {url}")

                async def __aexit__(_self, *args):
                    return None

            return _Ctx()

    with patch("plugins.dbview.proxy_router.httpx.AsyncClient", _ExplodingClient):
        app = _build_app(healthy=True)
        with TestClient(app) as client:
            resp = client.get("/api/dbview/health")

    assert resp.status_code == 502
    body = resp.json()
    assert body["code"] == "dbview_upstream_error"
    assert "refused" in body["detail"]
