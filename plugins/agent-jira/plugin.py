"""AgentJiraPlugin — full port of agent-jira (Agile Project Manager + Jira automation)
into BaselithCore.

Mirrors the upstream :file:`backend.py` 1:1:

Lifespan
--------
1. Configure logging (RequestIdFilter, SensitiveDataFilter, optional JSON formatter).
2. Initialize Postgres (if ``POSTGRES_ENABLED``).
3. If ``MULTI_TENANT_ENABLED``: ensure tenant + users schemas.
4. Create / refresh the Qdrant collection.
5. If ``GRAPH_DB_ENABLED``: ping FalkorDB.
6. Bootstrap document index (background if ``INDEX_BOOTSTRAP_BACKGROUND``, else sync).

Shutdown closes the Postgres pool, GraphDB connection, and stops the bootstrapper.

Routing
-------
The original ``backend.py`` mounts these routers at root: ``auth``, ``chat``,
``index``, ``metrics``, ``status``, ``console``, ``console.public_router``.
When ``ENABLE_FEEDBACK`` is true, ``feedback`` and ``admin`` are also mounted.
Each router carries its own absolute prefix (``/auth``, ``/chat``, ``/console``,
…), so :meth:`get_router_prefix` returns ``""`` and routes preserve their
upstream URL surface verbatim.

Two app-level routes (``GET /`` redirect to ``/console/`` and ``GET /favicon.svg``)
are exposed via an internal router so the plugin works standalone behind a
BaselithCore-managed app.

Middleware + static mounts
--------------------------
The original ``backend.py`` registers seven app-level middlewares and two
static mounts. BaselithCore's plugin loader does not auto-apply app-level
middleware — integrators that need full parity invoke
:meth:`apply_app_middleware` once at app construction (BaselithCore's
``core.api.factory.create_app`` calls it automatically via the
:meth:`setup_app_middleware` classmethod hook).
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# sys.path bootstrap — MUST run before any ``from agent_jira...`` import.
#
# The plugin dir holds the ``agent_jira`` package one level down. Adding the
# plugin dir to sys.path ensures imports like ``from agent_jira.routers
# import chat`` resolve when this module is loaded both by the BaselithCore
# loader (``importlib.spec_from_file_location``) and by alembic/uvicorn-style
# direct invocations.
# ---------------------------------------------------------------------------
_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from fastapi import APIRouter, FastAPI  # noqa: E402
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402
from fastapi.responses import FileResponse, RedirectResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.types import ASGIApp, Receive, Scope, Send  # noqa: E402

from core.plugins import RouterPlugin  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Logging infrastructure (mirrors backend.py module-level setup).
# ---------------------------------------------------------------------------

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s"
_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)
_old_record_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):  # pragma: no cover - logging infra
    record = _old_record_factory(*args, **kwargs)
    if not hasattr(record, "request_id"):
        try:
            record.request_id = _request_id_ctx.get("-")
        except Exception:
            record.request_id = "-"
    return record


logging.setLogRecordFactory(_record_factory)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        record.request_id = _request_id_ctx.get("-")
        return True


class _SensitiveDataFilter(logging.Filter):
    """Redact sensitive tokens that may leak into log records."""

    MARKERS = ("authorization", "api-key", "api_key", "bearer", "token")

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        try:
            msg = str(record.getMessage())
        except Exception:
            return True

        lowered = msg.lower()
        if any(marker in lowered for marker in self.MARKERS):
            for marker in self.MARKERS:
                msg = msg.replace(marker, f"{marker}=[redacted]")
            record.msg = msg
            record.args = ()
        return True


class _RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = _request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers["x-request-id"] = request_id
        return response


class _StaticCacheMiddleware(BaseHTTPMiddleware):
    """Add Cache-Control headers for static / console assets without touching APIs."""

    def __init__(self, app, max_age: int = 86400):
        super().__init__(app)
        self.max_age = max_age

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path or ""
        content_type = (response.headers.get("content-type") or "").lower()

        if path.startswith("/static"):
            response.headers.setdefault(
                "cache-control", f"public, max-age={self.max_age}"
            )
        elif path.startswith("/console"):
            if "application/json" in content_type:
                response.headers["cache-control"] = "no-store"
            else:
                response.headers.setdefault(
                    "cache-control", f"public, max-age={self.max_age}"
                )
        return response


def _ensure_logging_configured() -> None:
    """Idempotent root-logger setup mirroring ``backend._ensure_logging_configured``."""

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    log_dir = "logs"
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        pass

    from agent_jira.config import (
        LOG_FORMAT_MODE,
        LOG_LEVEL_CONSOLE,
        LOG_LEVEL_FILE,
    )

    level_console = getattr(logging, LOG_LEVEL_CONSOLE, logging.INFO)
    level_file = getattr(logging, LOG_LEVEL_FILE, logging.INFO)
    min_level = min(level_console, level_file)
    root_logger.setLevel(min_level)

    if LOG_FORMAT_MODE == "json":
        from agent_jira.logging_config import JsonFormatter, TenantContextFilter

        formatter: logging.Formatter = JsonFormatter()
        tenant_filter = TenantContextFilter()
    else:
        formatter = logging.Formatter(_LOG_FORMAT)
        tenant_filter = None

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level_console)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_RequestIdFilter())
    console_handler.addFilter(_SensitiveDataFilter())
    if tenant_filter is not None:
        console_handler.addFilter(tenant_filter)
    root_logger.addHandler(console_handler)

    try:
        file_handler = logging.FileHandler(os.path.join(log_dir, "app.log"))
        file_handler.setLevel(level_file)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(_RequestIdFilter())
        file_handler.addFilter(_SensitiveDataFilter())
        if tenant_filter is not None:
            file_handler.addFilter(tenant_filter)
        root_logger.addHandler(file_handler)
    except Exception:
        pass


class AgentJiraPlugin(RouterPlugin):
    """BaselithCore plugin wrapping the agent-jira FastAPI surface."""

    # -- routing ----------------------------------------------------------

    def get_router_prefix(self) -> str:
        # agent-jira routers carry their own absolute prefixes (``/auth``,
        # ``/chat``, ``/console`` …); mount at root to preserve URLs.
        return ""

    def get_router_tags(self) -> List[str]:
        return ["agent-jira"]

    def create_router(self) -> APIRouter:
        # Required by RouterPlugin abstract contract. Real routers are
        # returned by ``get_routers``; this stub is never mounted.
        return APIRouter()

    def get_routers(self) -> List[APIRouter]:
        """Return agent-jira routers, gated by ENABLE_FEEDBACK."""
        from agent_jira import config as aj_config
        from agent_jira.routers import (
            admin,
            auth,
            chat,
            console,
            feedback,
            index,
            metrics,
            status,
        )

        routers: List[APIRouter] = [
            auth.router,
            chat.router,
            index.router,
            metrics.router,
            status.router,
            console.router,
            console.public_router,
            self._build_root_router(),
        ]

        if aj_config.ENABLE_FEEDBACK:
            routers.extend([feedback.router, admin.router])
            logger.info("[agent-jira] feedback + admin routers mounted")
        else:
            logger.info(
                "[agent-jira] ENABLE_FEEDBACK=false — feedback/admin routers skipped"
            )

        return routers

    def _build_root_router(self) -> APIRouter:
        """Expose the two app-level routes from upstream ``backend.py``.

        ``GET /`` redirects to ``/console/`` and ``GET /favicon.svg`` serves
        the React favicon. Wrapped in a router so the plugin contract handles
        registration; collisions with a host-app root are a deployment concern.
        """

        router = APIRouter()
        favicon_path = _PLUGIN_DIR / "agent_jira" / "static" / "frontend" / "favicon.svg"

        @router.get("/", include_in_schema=False)
        async def root_redirect() -> RedirectResponse:
            return RedirectResponse(url="/console/")

        @router.get("/favicon.svg", include_in_schema=False)
        async def frontend_favicon() -> FileResponse:
            return FileResponse(str(favicon_path))

        return router

    # -- static frontend --------------------------------------------------

    def get_static_assets_path(self):
        """Expose the legacy ``app/static`` tree to the host loader.

        BaselithCore mounts the returned directory at
        ``/plugins/agent-jira/static`` (and ``/agent-jira`` if ``index.html``
        is present). The legacy URL surface (``/static``, ``/assets``,
        ``/console``) is preserved by :meth:`apply_app_middleware`.
        """

        static_dir = _PLUGIN_DIR / "agent_jira" / "static"
        return static_dir if static_dir.exists() else None

    # -- lifespan ---------------------------------------------------------

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Boot order: logging -> DB -> tenant/users schema -> Qdrant -> GraphDB -> index bootstrap.

        Mirrors :file:`backend.py` ``lifespan`` 1:1.
        """

        await super().initialize(config)
        _ensure_logging_configured()

        from agent_jira import config as aj_config
        from agent_jira.db import init_db
        from agent_jira.graphdb import graph_db
        from agent_jira.index_bootstrap import ensure_startup_bootstrap
        from agent_jira.vectorstore import create_collection

        logger.info(
            "[agent-jira] lifecycle start (postgres=%s)",
            "on" if aj_config.POSTGRES_ENABLED else "off",
        )

        if aj_config.POSTGRES_ENABLED:
            logger.info("[agent-jira] Postgres init")
            init_db()
            if aj_config.MULTI_TENANT_ENABLED:
                from agent_jira.db.tenants import ensure_tenant_schema
                from agent_jira.db.users import ensure_users_schema

                ensure_tenant_schema()
                ensure_users_schema()
                logger.info("[agent-jira] multi-tenant + users schema ready")
        else:
            logger.info("[agent-jira] Postgres disabled: skipping DB init")

        logger.info("[agent-jira] creating/refreshing Qdrant collection")
        create_collection()

        if aj_config.GRAPH_DB_ENABLED:
            graph_ok = graph_db.ping()
            if graph_ok:
                logger.info(
                    "[agent-jira] GraphDB up on %s (graph=%s)",
                    aj_config.GRAPH_DB_URL,
                    aj_config.GRAPH_DB_NAME,
                )
            else:
                logger.warning(
                    "[agent-jira] GraphDB enabled but unreachable (%s, graph=%s)",
                    aj_config.GRAPH_DB_URL,
                    aj_config.GRAPH_DB_NAME,
                )
        else:
            logger.info("[agent-jira] GraphDB disabled (GRAPH_DB_ENABLED=false)")

        if aj_config.INDEX_BOOTSTRAP_BACKGROUND:
            logger.info(
                "[agent-jira] scheduling background index bootstrap (non-blocking)"
            )
            asyncio.create_task(ensure_startup_bootstrap())
        else:
            logger.info("[agent-jira] running synchronous index bootstrap (blocking)")
            await ensure_startup_bootstrap()

    async def shutdown(self) -> None:
        """Mirror ``backend.lifespan`` shutdown branch."""

        try:
            from agent_jira import config as aj_config
            from agent_jira.db import close_pool
            from agent_jira.graphdb import graph_db
            from agent_jira.index_bootstrap import bootstrapper

            if aj_config.POSTGRES_ENABLED:
                close_pool()
            if aj_config.GRAPH_DB_ENABLED:
                graph_db.close()
            await bootstrapper.shutdown()
        except Exception as exc:  # pragma: no cover - shutdown is best-effort
            logger.warning("[agent-jira][shutdown] cleanup error: %s", exc)
        logger.info("[agent-jira] bye")
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
        """Register agent-jira's middleware stack + legacy static mounts.

        Mirrors :file:`backend.py` add order (Starlette wraps in reverse,
        producing this effective request flow)::

            request -> CORS -> SecurityHeaders -> SmartGzip -> StaticCache
                                                            -> CostControl
                                                            -> TenantMiddleware*
                                                            -> RequestId
                                                            -> routes
            (* TenantMiddleware only when MULTI_TENANT_ENABLED)

        Legacy URL surface (``/static``, ``/assets``) is preserved here so
        routers and templates that hardcode those paths keep working.
        """

        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.middleware.gzip import GZipMiddleware

        from agent_jira import config as aj_config
        from agent_jira.cost_control import CostControlMiddleware
        from agent_jira.security import SecurityHeadersMiddleware
        from agent_jira.tenant_context import TenantMiddleware

        # === OpenTelemetry opt-in ===
        try:
            from agent_jira.tracing import setup_tracing

            setup_tracing(app)
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "[agent-jira] OpenTelemetry setup failed (proceeding without): %s",
                exc,
            )

        # === Middleware (Starlette inverts add order) ===
        app.add_middleware(_RequestIdMiddleware)
        if aj_config.MULTI_TENANT_ENABLED:
            app.add_middleware(TenantMiddleware)
        app.add_middleware(CostControlMiddleware)
        app.add_middleware(_StaticCacheMiddleware, max_age=86400)
        app.add_middleware(
            _SmartGzipMiddleware,
            minimum_size=500,
            excluded_paths=["/chat/stream"],
        )
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=aj_config.ALLOW_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # === Static mounts (legacy URL surface) ===
        static_root = _PLUGIN_DIR / "agent_jira" / "static"
        assets_root = static_root / "frontend" / "assets"
        if static_root.exists():
            app.mount("/static", StaticFiles(directory=str(static_root)), name="static")
        if assets_root.exists():
            app.mount(
                "/assets", StaticFiles(directory=str(assets_root)), name="assets"
            )


class _SmartGzipMiddleware(GZipMiddleware):
    """Gzip everywhere EXCEPT streaming endpoints (preserves typewriter effect)."""

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compresslevel: int = 9,
        excluded_paths: list[str] | None = None,
    ):
        super().__init__(app, minimum_size=minimum_size, compresslevel=compresslevel)
        self.excluded_paths = excluded_paths or []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            for excluded in self.excluded_paths:
                if path.startswith(excluded):
                    await self.app(scope, receive, send)
                    return

        await super().__call__(scope, receive, send)
