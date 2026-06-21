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
    # Identity is delegated to the central ``auth`` plugin: login + refresh
    # happen against the core app's own endpoints (not under ``/baselithwiki``),
    # so no cookie-path rewrite is needed here anymore.
    _attach_spa(app)
    _app = app
    return _app
