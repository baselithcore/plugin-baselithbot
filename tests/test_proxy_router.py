"""Unit tests for the authenticated dbview reverse proxy.

Covers the pure header/cookie helpers plus the router behaviour with a
mocked upstream: prefix forwarding, 503/502 short-circuits, central per-tab
enforcement, gateway identity injection and inbound spoof stripping.
"""

from __future__ import annotations

import base64
import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.auth.types import AuthRole, AuthUser
from plugins.dbview.identity import GATEWAY_SECRET_HEADER, GATEWAY_USER_HEADER
from plugins.dbview.proxy_router import (
    _filter_request_headers,
    _filter_response_headers,
    _make_cookie_path_rewriter,
    _rewrite_set_cookie_path,
    build_proxy_router,
)

pytestmark = pytest.mark.unit

_GATEWAY_SECRET = "test-gateway-secret-0123456789abcdef"


# ---------------------------------------------------------------------------
# Header / cookie helpers
# ---------------------------------------------------------------------------


def test_filter_request_headers_drops_hop_by_hop_host_and_gateway_headers():
    raw = [
        (b"host", b"public.example.com"),
        (b"authorization", b"Bearer abc"),
        (b"connection", b"keep-alive"),
        (b"keep-alive", b"timeout=5"),
        (b"content-type", b"application/json"),
        (b"x-request-id", b"req-1"),
        # A client must never be able to smuggle a trusted identity through.
        (GATEWAY_USER_HEADER.encode(), b"forged"),
        (GATEWAY_SECRET_HEADER.encode(), b"forged-secret"),
    ]
    filtered = _filter_request_headers(raw)
    keys = {name.lower() for name, _ in filtered}
    assert "host" not in keys, "Host must be stripped so httpx regenerates it"
    assert "connection" not in keys
    assert "keep-alive" not in keys
    assert GATEWAY_USER_HEADER not in keys
    assert GATEWAY_SECRET_HEADER not in keys
    assert "authorization" in keys
    assert "content-type" in keys
    assert "x-request-id" in keys


def test_cookie_path_rewriter_maps_upstream_namespace_onto_proxy_prefix():
    rewrite = _make_cookie_path_rewriter("/api/dbview", "/api")
    # The upstream '/api/X' space is browser-visible as '/api/dbview/X'.
    assert rewrite("/api/auth") == "/api/dbview/auth"
    assert rewrite("/api") == "/api/dbview"
    # Site-wide cookies are left alone — narrowing them would be surprising.
    assert rewrite("/") == "/"
    # Idempotency: already-rewritten paths stay untouched.
    assert rewrite("/api/dbview/auth") == "/api/dbview/auth"
    # Paths outside the upstream prefix are still confined under the proxy.
    assert rewrite("/other") == "/api/dbview/other"
    # Relative paths (browsers should never send these but be permissive).
    assert rewrite("api/auth") == "api/auth"


def test_rewrite_set_cookie_path_preserves_other_attributes():
    rewrite = _make_cookie_path_rewriter("/api/dbview", "/api")
    raw = (
        "dbview_refresh=tok-abc; Path=/api/auth; HttpOnly; "
        "Secure; SameSite=Strict; Max-Age=2592000"
    )
    rewritten = _rewrite_set_cookie_path(raw, rewrite)
    assert "Path=/api/dbview/auth" in rewritten
    assert "HttpOnly" in rewritten
    assert "Secure" in rewritten
    assert "SameSite=Strict" in rewritten
    assert "Max-Age=2592000" in rewritten


def test_rewrite_set_cookie_path_is_case_insensitive_for_path_attr():
    rewrite = _make_cookie_path_rewriter("/api/dbview", "/api")
    raw = "k=v; path=/api/auth; httponly"
    rewritten = _rewrite_set_cookie_path(raw, rewrite)
    assert "Path=/api/dbview/auth" in rewritten


def test_filter_response_headers_drops_hop_by_hop_and_content_length():
    rewrite = _make_cookie_path_rewriter("/api/dbview", "/api")
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
    cookies = [value for name, value in filtered if name.lower() == "set-cookie"]
    assert any("Path=/api/dbview/auth" in c for c in cookies)


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

    async def __aenter__(self) -> _StubResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _install_stub_client(response: _StubResponse) -> dict[str, Any]:
    """Patch httpx.AsyncClient so the proxy router talks to a stub upstream."""
    captured: dict[str, Any] = {}
    stream_ctx = _StubStreamCtx(response)

    class _StubClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.timeout = kwargs.get("timeout")

        async def aclose(self) -> None:
            captured["closed"] = True

        def stream(self, method: str, url: str, **kwargs: Any) -> _StubStreamCtx:
            captured["method"] = method
            captured["url"] = url
            captured["headers"] = kwargs.get("headers")
            return stream_ctx

    captured["_patcher"] = patch("plugins.dbview.proxy_router.httpx.AsyncClient", _StubClient)
    return captured


def _make_user(*, authenticated: bool = True, admin: bool = False) -> AuthUser:
    if not authenticated:
        return AuthUser(user_id="anonymous", roles={AuthRole.ANONYMOUS})
    roles = {AuthRole.ADMIN} if admin else {AuthRole.USER}
    return AuthUser(user_id="user-1", roles=roles, email="user1@example.com")


def _build_app(
    *,
    healthy: bool = True,
    upstream: str = "http://127.0.0.1:65000",
    user: AuthUser | None = None,
    gateway_secret: str | None = _GATEWAY_SECRET,
) -> FastAPI:
    app = FastAPI()
    router = build_proxy_router(
        upstream_base_url_provider=lambda: upstream,
        healthy_provider=lambda: healthy,
        gateway_secret_provider=lambda: gateway_secret,
        proxy_prefix="/api/dbview",
    )
    app.include_router(router, prefix="/api/dbview")
    if user is not None:
        from plugins.auth.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = lambda: user
    return app


def test_proxy_returns_503_when_upstream_unhealthy():
    app = _build_app(healthy=False, user=_make_user())
    with TestClient(app) as client:
        resp = client.get("/api/dbview/health")
    assert resp.status_code == 503
    assert resp.json()["code"] == "dbview_upstream_down"


def test_proxy_forwards_url_with_global_api_prefix_and_injects_identity():
    response = _StubResponse(
        status_code=200,
        headers=[("content-type", "application/json")],
        body=b'{"ok":true}',
    )
    captured = _install_stub_client(response)
    captured["_patcher"].start()
    try:
        app = _build_app(user=_make_user(admin=True))
        with patch(
            "plugins.dbview.proxy_router.can_access_dbview_tab", return_value=True
        ), patch(
            "plugins.dbview.identity.is_effective_admin_cached", return_value=True
        ), patch(
            "plugins.dbview.identity.resolve_tenant_key", return_value="tenant-1"
        ), patch(
            "plugins.dbview.identity.lookup_central_profile",
            return_value=(None, None),
        ):
            with TestClient(app) as client:
                resp = client.get(
                    "/api/dbview/connections?limit=5",
                    headers={
                        # Forged inbound identity must be stripped.
                        GATEWAY_USER_HEADER: "forged",
                        GATEWAY_SECRET_HEADER: "forged",
                    },
                )
    finally:
        captured["_patcher"].stop()

    assert resp.status_code == 200
    # Plugin prefix stripped, upstream "/api" preserved, query forwarded.
    assert captured["url"] == "http://127.0.0.1:65000/api/connections?limit=5"

    header_map: dict[str, list[str]] = {}
    for name, value in captured["headers"]:
        header_map.setdefault(name.lower(), []).append(value)
    # Exactly one trusted identity pair — the forged inbound one is gone.
    assert header_map[GATEWAY_SECRET_HEADER] == [_GATEWAY_SECRET]
    assert len(header_map[GATEWAY_USER_HEADER]) == 1
    payload = header_map[GATEWAY_USER_HEADER][0]
    decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    assert decoded["id"] == "user-1"
    assert decoded["role"] == "admin"
    assert decoded["tenantKey"] == "tenant-1"
    assert "X-Forwarded-Prefix".lower() in {n.lower() for n, _ in captured["headers"]}


def test_proxy_denies_authenticated_user_when_tab_policy_blocks():
    app = _build_app(user=_make_user())
    with patch("plugins.dbview.proxy_router.can_access_dbview_tab", return_value=False):
        with TestClient(app) as client:
            resp = client.get("/api/dbview/connections")
    assert resp.status_code == 403
    assert resp.json()["code"] == "dbview_tab_denied"


def test_proxy_forwards_anonymous_without_identity_headers():
    response = _StubResponse(
        status_code=200,
        headers=[("content-type", "application/json")],
        body=b'{"registrationEnabled":false,"gateway":true}',
    )
    captured = _install_stub_client(response)
    captured["_patcher"].start()
    try:
        app = _build_app(user=_make_user(authenticated=False))
        with TestClient(app) as client:
            resp = client.get("/api/dbview/auth/config")
    finally:
        captured["_patcher"].stop()

    assert resp.status_code == 200
    header_names = {name.lower() for name, _ in captured["headers"]}
    assert GATEWAY_USER_HEADER not in header_names
    assert GATEWAY_SECRET_HEADER not in header_names


def test_proxy_rewrites_set_cookie_path():
    response = _StubResponse(
        status_code=200,
        headers=[
            ("content-type", "application/json"),
            ("set-cookie", "dbview_refresh=abc; Path=/api/auth; HttpOnly; SameSite=Strict"),
        ],
        body=b"{}",
    )
    captured = _install_stub_client(response)
    captured["_patcher"].start()
    try:
        app = _build_app(user=_make_user())
        with patch("plugins.dbview.proxy_router.can_access_dbview_tab", return_value=True):
            with TestClient(app) as client:
                resp = client.post("/api/dbview/auth/refresh")
    finally:
        captured["_patcher"].stop()

    assert resp.status_code == 200
    cookie_header = resp.headers.get("set-cookie", "")
    assert "Path=/api/dbview/auth" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=Strict" in cookie_header


def test_proxy_502s_when_upstream_connect_fails():
    class _ExplodingClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def aclose(self) -> None:
            return None

        def stream(self, method: str, url: str, **kwargs: Any):
            class _Ctx:
                async def __aenter__(_self):
                    raise httpx.ConnectError(f"refused: {url}")

                async def __aexit__(_self, *args):
                    return None

            return _Ctx()

    with patch("plugins.dbview.proxy_router.httpx.AsyncClient", _ExplodingClient):
        app = _build_app(user=_make_user())
        with patch("plugins.dbview.proxy_router.can_access_dbview_tab", return_value=True):
            with TestClient(app) as client:
                resp = client.get("/api/dbview/health")

    assert resp.status_code == 502
    body = resp.json()
    assert body["code"] == "dbview_upstream_error"
    assert "refused" in body["detail"]
