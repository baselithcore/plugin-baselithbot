"""Build the embeddable BaselithWiki ASGI application.

The vendored engine exposes its FastAPI app as ``_wiki_main.app`` with all
routers wired at their canonical absolute paths (``/api/*``, ``/auth/*``,
``/healthz``, ``/metrics``). We take that app **as-is** — when the host mounts
it under ``/baselithwiki`` Starlette strips the mount prefix, so the engine
keeps seeing its own paths and zero source changes are needed.

On top of the engine we graft the built single-page-app:

* compiled assets and ``index.html`` live in ``frontend/dist`` (produced by
  ``npm run build`` with ``VITE_BASE_PATH=/baselithwiki/``);
* a trailing ``{path:path}`` catch-all serves a real file when one exists and
  otherwise returns ``index.html`` so client-side routing deep-links resolve.

The catch-all is registered *last*, so every concrete engine route (and the
API) still wins the match — only genuinely unmatched GETs fall through to the
SPA shell.
"""

from __future__ import annotations

from typing import Any

from . import _bootstrap

_bootstrap.ensure_ready()

_DIST_DIR = _bootstrap.PLUGIN_DIR / "frontend" / "dist"

#: Path the host mounts this app under (kept in sync with plugin.MOUNT_PATH).
MOUNT_PATH = "/baselithwiki"

_app: Any | None = None


class _CookiePathRewriteMiddleware:
    """Rewrite the refresh cookie's ``Path`` for the mounted prefix.

    The engine pins the refresh cookie to ``Path=/auth`` (see
    ``llm_wiki/api/routers/auth/helpers.py``). Mounted under ``/baselithwiki``
    the browser would never send it back to ``/baselithwiki/auth/refresh`` —
    silently killing JWT rotation after the first access token expires. We
    rewrite outgoing ``Set-Cookie`` headers so the cookie is scoped to the
    real, prefixed path. Pure ASGI (no BaseHTTPMiddleware) to preserve
    streaming/cancellation per the core middleware convention.
    """

    def __init__(self, app: Any, mount_path: str = MOUNT_PATH) -> None:
        self.app = app
        self._src = b"Path=/auth"
        self._dst = f"Path={mount_path}/auth".encode()

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def _send(message: Any) -> None:
            if message.get("type") == "http.response.start":
                headers = message.get("headers")
                if headers:
                    message = {
                        **message,
                        "headers": [
                            (k, v.replace(self._src, self._dst))
                            if k.lower() == b"set-cookie"
                            else (k, v)
                            for k, v in headers
                        ],
                    }
            await send(message)

        await self.app(scope, receive, _send)


def _attach_spa(app: Any) -> None:
    """Register the SPA file server + index fallback on the engine app."""
    from fastapi.responses import FileResponse, JSONResponse

    index_file = _DIST_DIR / "index.html"

    async def _serve_spa(path: str) -> Any:
        if not index_file.is_file():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "BaselithWiki UI not built. Run "
                        "`VITE_BASE_PATH=/baselithwiki/ VITE_API_URL=/baselithwiki/api "
                        "npm --prefix plugins/baselithwiki/frontend run build`."
                    )
                },
            )
        # Map the request to a concrete asset when one exists; guard against
        # path traversal by confirming the resolved file stays under dist.
        candidate = (_DIST_DIR / path).resolve()
        if path and candidate.is_file() and _DIST_DIR.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index_file)

    # Registered after all engine routers → lowest match priority.
    app.add_api_route(
        "/{path:path}",
        _serve_spa,
        methods=["GET"],
        include_in_schema=False,
        name="baselithwiki_spa",
    )


def get_app() -> Any:
    """Return the singleton embeddable wiki application (built once)."""
    global _app
    if _app is not None:
        return _app

    _bootstrap.ensure_ready()
    import _wiki_main  # noqa: PLC0415 — deferred until env is isolated

    app = _wiki_main.app
    # Scope the refresh cookie to the mount prefix (added before serving →
    # the middleware stack is still mutable).
    app.add_middleware(_CookiePathRewriteMiddleware, mount_path=MOUNT_PATH)
    _attach_spa(app)
    _app = app
    return _app
