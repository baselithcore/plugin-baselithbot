"""DbviewPlugin — host wrapper around the dbview TypeScript stack.

Why this plugin exists
----------------------
dbview is a TypeScript/NestJS + React application — a database visualisation
and NL→Query workbench for 18 engines (PostgreSQL, MySQL, MariaDB, MSSQL,
SQLite, Oracle, ClickHouse, DuckDB, CockroachDB, Neo4j, FalkorDB, Ultipa,
MongoDB, Redis, Elasticsearch, Qdrant, Salesforce, Salesforce Data Cloud).
A Python rewrite of its NestJS surface, engine adapters and AST-level query
safety would inevitably regress, so the upstream monorepo is vendored
verbatim under ``plugins/dbview/dbview/`` and hosted as a managed Node child
process behind a FastAPI reverse proxy:

1. ``initialize()`` composes the child environment (central-gateway auth
   secret, data dir, JWT fallback), spawns ``node dist/main.js`` and gates on
   ``GET /api/health``.
2. ``get_routers()`` exposes one streaming reverse-proxy router at
   ``/api/dbview`` (see :mod:`.proxy_router`).
3. ``get_static_assets_path()`` serves the built SPA from
   ``dbview/apps/web/dist`` (mounted at ``/dbview``).
4. ``shutdown()`` SIGTERMs the child (SIGKILL on grace expiry).

Central auth & tenancy (platform conventions)
---------------------------------------------
Identity is owned by the central ``auth`` plugin. The proxy authenticates via
the shared ``get_current_user`` chokepoint, enforces the central per-tab
policy for ``(dbview, dbview)``, and forwards the identity to the upstream as
trusted gateway headers signed with a **per-boot secret** generated here and
injected into the child env (``DBVIEW_GATEWAY_AUTH`` / ``DBVIEW_GATEWAY_SECRET``).
The upstream JIT-mirrors users, disables its local login/registration, and
confines connection sharing to the identity-derived tenancy scope key
(:func:`core.context.resolve_plugin_tenant_key` — honours the runtime
``shared``/``personal`` override from the auth console).

Operational notes
-----------------
* Node ≥ 20 on PATH. pnpm is auto-provisioned as 10.15.0 via the vendored
  ``package.json`` ``packageManager`` field (Node-20 compatible) — do not pin
  pnpm 11.x while on Node 20 (pnpm 11 needs Node ≥ 22.13).
* ``DBVIEW_SECRET`` (≥ 16 chars) is **mandatory** — it keys the AES-256-GCM
  encryption of stored connection strings and must stay stable across boots.
* ``DBVIEW_JWT_SECRET`` is auto-generated per boot when unset (the local JWT
  flow is disabled under gateway auth); set it explicitly only for
  standalone-style deployments.
* Build once before first prod boot::

      cd plugins/dbview/dbview && pnpm install && pnpm -r build
      VITE_API_BASE_URL=/api/dbview VITE_BASE_PATH=/dbview/ \
        VITE_AUTH_MODE=gateway pnpm --filter @dbview/web build
"""

from __future__ import annotations

import logging
import os
import secrets
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


class DbviewConfigurationError(RuntimeError):
    """Raised when a mandatory operator setting is missing or invalid."""


class DbviewPlugin(RouterPlugin):
    """BaselithCore plugin that hosts the dbview TypeScript stack."""

    def __init__(self) -> None:
        super().__init__()
        self._supervisor: NodeSupervisor | None = None
        self._proxy_router: APIRouter | None = None
        self._gateway_secret: str | None = None

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
        # ``RouterPlugin`` abstract method. The real router is supplied by
        # :meth:`get_routers` after ``initialize`` wires the supervisor.
        return APIRouter()

    def get_routers(self) -> List[APIRouter]:
        if self._proxy_router is None:
            # The loader may call this during registration, before
            # ``initialize`` completes. Return a placeholder; it is
            # re-fetched after activation.
            return [APIRouter()]
        return [self._proxy_router]

    # ------------------------------------------------------------------
    # UI surface
    # ------------------------------------------------------------------

    def get_ui_tabs(self) -> list[dict[str, str]]:
        # Single-surface SPA. The literal id keys the central Access Control
        # matrix as ``(dbview, dbview)`` — keep it stable.
        return [{"id": "dbview", "label": "DBView"}]

    def get_static_assets_path(self) -> Optional[Path]:
        """Serve the built dbview web SPA when present.

        The lifespan mounts the returned directory at
        ``/plugins/dbview/static`` and — because the SPA ships an
        ``index.html`` — also at ``/dbview`` with HTML auto-routing.
        """
        dist = _PLUGIN_DIR / "dbview" / "apps" / "web" / "dist"
        if dist.exists():
            return dist
        logger.info(
            "[dbview] web bundle not found at %s — SPA will not be mounted. "
            "Build it with: VITE_API_BASE_URL=/api/dbview VITE_BASE_PATH=/dbview/ "
            "VITE_AUTH_MODE=gateway pnpm --filter @dbview/web build",
            dist,
        )
        return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _compose_child_env(self) -> dict[str, str]:
        """Plugin-owned child env: gateway auth contract + safe defaults.

        * ``DBVIEW_SECRET`` must be operator-provided and stable — it
          encrypts persisted connection strings; generating it here would
          silently orphan all stored connections on every restart.
        * ``DBVIEW_JWT_SECRET`` is only consumed by the (disabled) local JWT
          flow, so a per-boot value is a safe default.
        * ``DBVIEW_DATA_DIR`` defaults to ``plugins/dbview/var/data`` so
          runtime state never lands inside the vendored source tree.
        """
        if len(os.environ.get("DBVIEW_SECRET", "")) < 16:
            raise DbviewConfigurationError(
                "DBVIEW_SECRET (>= 16 chars) is required by the dbview plugin: "
                "it encrypts stored connection strings at rest and must remain "
                "stable across restarts. Set it in the host environment."
            )

        extra_env: dict[str, str] = {}

        self._gateway_secret = secrets.token_urlsafe(32)
        extra_env["DBVIEW_GATEWAY_AUTH"] = "true"
        extra_env["DBVIEW_GATEWAY_SECRET"] = self._gateway_secret

        if len(os.environ.get("DBVIEW_JWT_SECRET", "")) < 32:
            extra_env["DBVIEW_JWT_SECRET"] = secrets.token_urlsafe(48)

        if not os.environ.get("DBVIEW_DATA_DIR"):
            data_dir = _PLUGIN_DIR / "var" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            extra_env["DBVIEW_DATA_DIR"] = str(data_dir)

        return extra_env

    async def initialize(self, config: Dict[str, Any]) -> None:
        await super().initialize(config)

        supervisor_overrides = {
            key: value
            for key, value in (config or {}).items()
            if key in {"mode", "host", "port"}
        }
        supervisor_config = build_supervisor_config(
            _PLUGIN_DIR,
            extra_env=self._compose_child_env(),
            overrides=supervisor_overrides,
        )
        supervisor = NodeSupervisor(supervisor_config)
        self._supervisor = supervisor

        try:
            await supervisor.start()
        except (NodeNotAvailableError, FileNotFoundError) as exc:
            # Misconfigured host: re-raise so the loader marks the plugin
            # FAILED — that's how operators discover the issue early.
            logger.error("[dbview] activation aborted: %s", exc)
            self._supervisor = None
            raise
        except StartupTimeoutError as exc:
            logger.error("[dbview] startup timeout: %s", exc)
            try:
                await supervisor.stop()
            finally:
                self._supervisor = None
            raise

        self._proxy_router = build_proxy_router(
            upstream_base_url_provider=lambda: supervisor.base_url,
            healthy_provider=supervisor.is_healthy,
            gateway_secret_provider=lambda: self._gateway_secret,
            proxy_prefix=_PROXY_PREFIX,
        )
        logger.info(
            "[dbview] plugin ready (upstream=%s, prefix=%s, central-auth=on)",
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
        self._gateway_secret = None
        await super().shutdown()

    # ------------------------------------------------------------------
    # Convenience for tests / diagnostics
    # ------------------------------------------------------------------

    @property
    def supervisor(self) -> NodeSupervisor | None:
        """Expose the supervisor for integration tests and admin tooling."""
        return self._supervisor
