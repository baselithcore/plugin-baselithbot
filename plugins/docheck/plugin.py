"""DoCheckPlugin — full port of docheck (Document Compliance Checker) into BaselithCore.

Mirrors the original :file:`docheck-engine/src/docheck/main.py` 1:1:

1. Configure structlog logging via ``core.logging.setup_logging``.
2. Ensure storage_root + docs_dir exist on disk.
3. Setup OpenTelemetry tracing (local file exporter, no cloud).
4. Run Alembic ``upgrade head`` against the active DB.
5. Install Postgres row-level-security session hook (no-op for SQLite).
6. Reindex policy rules into the configured vector store (Chroma default).

Shutdown: best-effort log line.

Routing
-------
docheck routers are aggregated by :file:`docheck/api/__init__.py` into a single
``api_router`` mounted at ``/api/v1``. The plugin returns that aggregate to
preserve the original URL surface verbatim.

Middleware
----------
The original ``main.py`` registers four app-level middlewares:
``SecurityHeadersMiddleware``, ``TenantMiddleware``, ``RequestIdMiddleware``,
and ``CORSMiddleware`` (with Electron/Tauri/VSCode-webview origin regex).
BaselithCore's plugin contract exposes ``setup_app_middleware`` for that —
integrators using ``core.api.factory.create_app`` get full parity automatically.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# sys.path bootstrap — MUST run before any ``from docheck...`` import.
#
# The upstream codebase carries dozens of absolute imports of the form
# ``from docheck.xxx import yyy``. To preserve them verbatim (zero regression
# risk on import paths) the plugin directory is added to sys.path so the
# nested ``plugins/docheck/docheck/`` package resolves as a top-level
# ``docheck``.
# ---------------------------------------------------------------------------
_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from fastapi import APIRouter, FastAPI  # noqa: E402

from core.plugins import RouterPlugin  # noqa: E402

logger = logging.getLogger(__name__)


class DoCheckPlugin(RouterPlugin):
    """BaselithCore plugin wrapping the docheck FastAPI surface."""

    # -- routing ----------------------------------------------------------

    def get_router_prefix(self) -> str:
        # docheck's main.py mounts the aggregated api router at ``/api/v1``.
        return "/api/v1"

    def get_router_tags(self) -> List[str]:
        return ["docheck"]

    def create_router(self) -> APIRouter:
        # Required by RouterPlugin abstract contract. Real routers are
        # returned by ``get_routers``; this empty stub is never mounted.
        return APIRouter()

    def get_routers(self) -> List[APIRouter]:
        """Return the aggregate docheck API router (mounted under /api/v1)."""
        from docheck.api import router as api_router

        return [api_router]

    # -- static frontend --------------------------------------------------

    def get_static_assets_path(self):
        """Serve the built Next.js export if present.

        The docheck UI builds via ``next build`` (and optionally
        ``next export`` for fully static deploys). When operators ship a
        static export under ``ui/out/`` or the default ``ui/.next/``
        directory, expose it so BaselithCore's lifespan can mount it at
        ``/plugins/docheck/static`` (and ``/docheck`` if ``index.html``
        is present).

        Returns ``None`` when no built output exists yet — the Electron
        bundle and dev server (``next dev``) cover the runtime UI in
        non-static deployments.
        """
        ui_root = _PLUGIN_DIR / "ui"
        for candidate in ("out", "dist", ".next"):
            path = ui_root / candidate
            if path.exists():
                return path
        return None

    # -- lifespan ---------------------------------------------------------

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Boot order: logging → storage dirs → tracing → migrations → RLS → policy reindex.

        Mirrors :file:`docheck/main.py` ``lifespan`` 1:1.
        """
        await super().initialize(config)

        from docheck.core.config import settings
        from docheck.core.logging import log, setup_logging
        from docheck.core.telemetry import setup_tracing
        from docheck.db.migrate import upgrade_to_head
        from docheck.db.rls import install_rls_hook

        setup_logging(settings.debug)
        settings.storage_root.mkdir(parents=True, exist_ok=True)
        settings.docs_dir.mkdir(parents=True, exist_ok=True)

        try:
            setup_tracing()
        except Exception as exc:
            logger.warning("[docheck] tracing setup failed: %s", exc)

        try:
            upgrade_to_head()
        except Exception as exc:
            logger.error("[docheck] alembic upgrade failed: %s", exc)
            raise

        try:
            install_rls_hook()
        except Exception as exc:
            logger.warning("[docheck] RLS hook install skipped: %s", exc)

        try:
            from docheck.db.session import SessionLocal
            from docheck.services import policy_index

            async with SessionLocal() as db:
                n = await policy_index.reindex_all(db)
                log.info("policy_index.reindex_complete", rules_indexed=n)
        except Exception as exc:
            log.warning("policy_index.reindex_skipped", error=str(exc))

        log.info("docheck.startup", version=settings.version)

    async def shutdown(self) -> None:
        try:
            from docheck.core.logging import log

            log.info("docheck.shutdown")
        except Exception:
            logger.info("[docheck] bye")
        await super().shutdown()

    # -- middleware integration ------------------------------------------

    @classmethod
    def setup_app_middleware(cls, app: Any) -> None:
        """Plugin hook invoked by ``core.api.factory.create_app``.

        Defers to :meth:`apply_app_middleware` so the helper stays callable
        manually (e.g. from a custom factory or a test harness).
        """
        cls.apply_app_middleware(app)

    @staticmethod
    def apply_app_middleware(app: FastAPI) -> None:
        """Apply the docheck-specific app-level middleware stack.

        Registration order mirrors the original ``main.py``. Starlette wraps
        in reverse, so the effective request flow becomes::

            request → CORS → RequestId → Tenant → SecurityHeaders → routes
        """
        from fastapi.middleware.cors import CORSMiddleware

        from docheck.api.middleware import (
            RequestIdMiddleware,
            SecurityHeadersMiddleware,
            TenantMiddleware,
        )

        # Innermost first (Starlette inverts order on add_middleware).
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(TenantMiddleware)
        app.add_middleware(RequestIdMiddleware)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:3000",
                "http://localhost:3100",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3100",
                "app://docheck",
            ],
            allow_origin_regex=r"^(vscode-webview://[^/]+|app://[^/]+|tauri://[^/]+|file://)$",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*", "X-User-Id", "X-Tenant-Id", "X-Request-Id"],
            expose_headers=["X-Request-Id", "X-Tenant-Id"],
        )
