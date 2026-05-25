"""DbviewPlugin — host wrapper around the dbview TypeScript stack.

Why this plugin exists
----------------------
dbview is a TypeScript/NestJS application — a database visualisation +
NL→Query workbench supporting 17 engines (Postgres, MySQL, MSSQL,
SQLite, Oracle, ClickHouse, DuckDB, Cockroach, Neo4j, FalkorDB,
Ultipa, MongoDB, Qdrant, Redis, Elasticsearch, Salesforce SOQL).
A faithful port of its 102-file NestJS surface + 97-file React frontend
to Python would inevitably regress non-trivial logic (AST-level SQL
safety, Cypher safety, deterministic alias auto-correction, refresh-
cookie rotation with replay detection). The user's brief was explicit:
no regressions, no rewrite — keep dbview itself byte-identical.

So we host it as a managed Node child process and expose it through
BaselithCore's standard plugin contract:

1. ``initialize()`` spawns the NestJS app (``node dist/main.js``),
   waits for ``GET /api/health`` to return < 500, and registers a
   keep-alive supervisor task.
2. ``get_routers()`` returns a single reverse-proxy ``APIRouter`` mounted
   at ``/api/dbview`` that streams every request to the child and
   rewrites the refresh-cookie path so JWT rotation keeps working
   behind the new prefix.
3. ``get_static_assets_path()`` exposes ``dbview/apps/web/dist/`` so
   the lifespan auto-mounts the SPA at ``/dbview`` and the raw assets
   at ``/plugins/dbview/static``.
4. ``shutdown()`` SIGTERMs the child (then SIGKILL on grace timeout)
   and tears the supervisor down so reloads stay clean.

Source layout
-------------
The full dbview monorepo lives byte-for-byte under
``plugins/dbview/dbview/`` (apps/, packages/, infra/, deploy/, docs/).
Only three host-aware patches were applied to the upstream UI, each
guarded by an environment variable whose default reproduces the
standalone behaviour exactly (zero regression on detached builds):

* ``apps/web/src/lib/api.ts`` — ``baseURL`` reads ``VITE_API_BASE_URL``,
  default ``/api``.
* ``apps/web/src/lib/auth.ts`` — refresh/me/logout fetches use the
  same env-driven base.
* ``apps/web/vite.config.ts`` — ``base`` reads ``VITE_BASE_PATH``,
  default ``/``.

Operators building the bundle for plugin mode set:

.. code:: shell

   VITE_API_BASE_URL=/api/dbview VITE_BASE_PATH=/dbview/ pnpm --filter @dbview/web build

Operational notes
-----------------
* Node ≥ 20 and (for dev mode) pnpm ≥ 11 must be on ``PATH``.
* ``DBVIEW_JWT_SECRET`` (≥32 chars) and ``DBVIEW_SECRET`` (≥16 chars)
  are mandatory; the plugin does NOT inject defaults — the upstream
  bootstrap validates and refuses to start without them.
* Everything else flows through the supervisor's env passthrough
  (``DBVIEW_*``, ``OLLAMA_*``, ``OPENAI_*``, ``ANTHROPIC_*``, ``OTEL_*``,
  ``LOG_*``, ``NODE_*``, ``APP_VERSION``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from core.plugins import RouterPlugin

from .proxy_router import build_proxy_router
from .supervisor import (
    NodeNotAvailableError,
    NodeSupervisor,
    StartupTimeoutError,
    build_supervisor_config,
)

logger = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).resolve().parent
_PROXY_PREFIX = "/api/dbview"


class DbviewPlugin(RouterPlugin):
    """BaselithCore plugin that hosts the dbview TypeScript stack."""

    def __init__(self) -> None:
        super().__init__()
        self._supervisor: NodeSupervisor | None = None
        self._proxy_router: APIRouter | None = None

    # ------------------------------------------------------------------
    # Router contract
    # ------------------------------------------------------------------

    def get_router_prefix(self) -> str:
        # Literal so the ResourceAnalyzer AST scan (which feeds the lazy
        # activation middleware) discovers the prefix without executing
        # plugin code at startup.
        return "/api/dbview"

    def get_router_tags(self) -> List[str]:
        return ["dbview"]

    def create_router(self) -> APIRouter:
        # ``RouterPlugin`` abstract method. The real router is supplied
        # by :meth:`get_routers` after ``initialize`` wires the supervisor.
        return APIRouter()

    def get_routers(self) -> List[APIRouter]:
        if self._proxy_router is None:
            # Plugin loader may call this before ``initialize`` completes
            # (registration step). Return a placeholder so lifespan
            # doesn't crash — it will be re-fetched after activation.
            return [APIRouter()]
        return [self._proxy_router]

    # ------------------------------------------------------------------
    # Static SPA
    # ------------------------------------------------------------------

    def get_static_assets_path(self) -> Optional[Path]:
        """Serve the built dbview web SPA when present.

        The lifespan mounts the returned directory at
        ``/plugins/dbview/static`` and — because the SPA ships an
        ``index.html`` — also at ``/dbview`` with HTML auto-routing
        for client-side navigation.
        """
        dist = _PLUGIN_DIR / "dbview" / "apps" / "web" / "dist"
        if dist.exists():
            return dist
        logger.info(
            "[dbview] web bundle not found at %s — SPA will not be mounted "
            "until you run `pnpm --filter @dbview/web build`.",
            dist,
        )
        return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self, config: Dict[str, Any]) -> None:
        await super().initialize(config)

        supervisor_overrides = {
            key: value
            for key, value in (config or {}).items()
            if key in {"mode", "host", "port"}
        }
        supervisor_config = build_supervisor_config(
            _PLUGIN_DIR, overrides=supervisor_overrides
        )
        self._supervisor = NodeSupervisor(supervisor_config)

        try:
            await self._supervisor.start()
        except (NodeNotAvailableError, FileNotFoundError) as exc:
            # Misconfigured host: the plugin is loaded but cannot serve.
            # We re-raise so the loader transitions the plugin to FAILED
            # state — that's how operators discover the issue early.
            logger.error("[dbview] activation aborted: %s", exc)
            self._supervisor = None
            raise
        except StartupTimeoutError as exc:
            logger.error("[dbview] startup timeout: %s", exc)
            # Try to tear down whatever we managed to spawn before re-raising.
            try:
                await self._supervisor.stop()
            finally:
                self._supervisor = None
            raise

        supervisor = self._supervisor

        self._proxy_router = build_proxy_router(
            upstream_base_url_provider=lambda: supervisor.base_url,
            healthy_provider=supervisor.is_healthy,
            proxy_prefix=_PROXY_PREFIX,
        )
        logger.info(
            "[dbview] plugin ready (upstream=%s, prefix=%s)",
            supervisor.base_url,
            _PROXY_PREFIX,
        )

    async def shutdown(self) -> None:
        if self._supervisor is not None:
            try:
                await self._supervisor.stop()
            except Exception as exc:  # pragma: no cover — defensive
                logger.warning("[dbview] supervisor stop raised: %s", exc)
            self._supervisor = None
        self._proxy_router = None
        await super().shutdown()

    # ------------------------------------------------------------------
    # Convenience for tests / diagnostics
    # ------------------------------------------------------------------

    @property
    def supervisor(self) -> NodeSupervisor | None:
        """Expose the supervisor for integration tests and admin tooling."""
        return self._supervisor
