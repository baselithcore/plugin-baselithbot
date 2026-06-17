"""Build the embeddable BaselithBrain ASGI application.

The backend exposes its FastAPI app (``backend.app.app``) with routers wired at
canonical absolute paths (``/api/*``, ``/healthz``). When the host mounts it
under ``/baselithbrain`` Starlette strips the prefix, so the backend keeps
seeing its own paths and needs zero changes.

On top we graft the built single-page-app:

* compiled assets + ``index.html`` live in ``ui/dist`` (produced by
  ``npm run build`` with ``VITE_BASE_PATH=/baselithbrain/``);
* a trailing ``{path:path}`` catch-all serves a real file when one exists and
  otherwise returns ``index.html`` so client-side deep-links resolve.

The catch-all is registered *last*, so every concrete API route still wins the
match — only genuinely unmatched GETs fall through to the SPA shell.
"""

from __future__ import annotations

from typing import Any

from . import _bootstrap

_bootstrap.ensure_ready()

_DIST_DIR = _bootstrap.PLUGIN_DIR / "ui" / "dist"

_app: Any | None = None


def _attach_spa(app: Any) -> None:
    """Register the SPA file server + index fallback on the backend app."""
    from fastapi.responses import FileResponse, JSONResponse

    index_file = _DIST_DIR / "index.html"

    async def _serve_spa(path: str) -> Any:
        if not index_file.is_file():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "BaselithBrain UI not built. Run "
                        "`VITE_BASE_PATH=/baselithbrain/ npm --prefix "
                        "plugins/baselithbrain/ui install && "
                        "VITE_BASE_PATH=/baselithbrain/ npm --prefix "
                        "plugins/baselithbrain/ui run build`."
                    )
                },
            )
        candidate = (_DIST_DIR / path).resolve()
        if path and candidate.is_file() and _DIST_DIR.resolve() in candidate.parents:
            # Built assets carry content-hashed names → safe to cache forever.
            return FileResponse(candidate)
        # ``index.html`` is the only un-hashed file: it pins the current asset
        # hashes, so it must never be served stale (else a rebuilt UI keeps
        # loading old bundles in caching webviews). Force revalidation.
        return FileResponse(
            index_file,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    app.add_api_route(
        "/{path:path}",
        _serve_spa,
        methods=["GET"],
        include_in_schema=False,
        name="baselithbrain_spa",
    )


def get_app() -> Any:
    """Return the singleton embeddable second-brain application (built once)."""
    global _app
    if _app is not None:
        return _app

    _bootstrap.ensure_ready()
    # Relative import: ``backend`` is a subpackage of this plugin. Absolute
    # ``import backend`` would collide with the repo-root ``backend.py`` entry
    # point — the plugin package namespace keeps us isolated.
    from .backend.app import app  # noqa: PLC0415 — deferred until env is isolated

    _attach_spa(app)
    _app = app
    return _app
