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
trusted gateway headers signed with a **worker-shared secret** (operator
``DBVIEW_GATEWAY_SECRET`` or one derived from ``DBVIEW_SECRET``; see
:meth:`_resolve_gateway_secret`) injected into the child env
(``DBVIEW_GATEWAY_AUTH`` / ``DBVIEW_GATEWAY_SECRET``).
The upstream JIT-mirrors users, disables its local login/registration, and
confines connection sharing to the identity-derived tenancy scope key
(:func:`core.context.resolve_plugin_tenant_key` — honours the runtime
``shared``/``personal`` override from the auth console).

LLM routing is centrally governed the same way: the operator's per-plugin LLM
pin (auth console; scopes ``nl2sql``/``explain``) is translated into child env
overrides at every spawn — see :mod:`.llm_governance`.

Multi-worker model (single Node child)
--------------------------------------
The embedded dbview app is single-instance: its state (connections, mirrored
users, sessions, engine pools) lives in per-process in-memory maps read once at
startup. Under a multi-worker deployment (``WEB_CONCURRENCY>1``) exactly one
worker is elected (Postgres advisory lock — see :mod:`.leader`) to spawn the
single Node child on a **fixed** loopback port (``DBVIEW_INTERNAL_PORT`` or the
plugin default); every other worker runs its proxy in *follower* mode and
forwards to that same child. Without this each worker span its own child with a
private store, so a connection created on one was *"not found"* on the next
request that round-robined to another. All workers sign gateway identity with a
**shared** secret (:meth:`_resolve_gateway_secret`) so the single child accepts
follower-forwarded requests. Degrades to one-child-per-worker only when Postgres
is unavailable (assumed single-worker/dev).

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

import hashlib
import hmac
import logging
import os
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from core.plugins import RouterPlugin

from .leader import DbviewLeadership, acquire_dbview_leadership
from .llm_governance import governed_child_env
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

# Fixed loopback rendezvous port used when cross-worker leadership is active:
# the single leader-owned Node child binds it and every follower worker's proxy
# forwards to it. Overridable with ``DBVIEW_INTERNAL_PORT`` if it collides on a
# given host. Only used under coordinated (Postgres-backed) leadership — a
# degraded single worker keeps the historical ephemeral allocation.
_DEFAULT_INTERNAL_PORT = 43117


class DbviewConfigurationError(RuntimeError):
    """Raised when a mandatory operator setting is missing or invalid."""


class DbviewPlugin(RouterPlugin):
    """BaselithCore plugin that hosts the dbview TypeScript stack."""

    def __init__(self) -> None:
        super().__init__()
        self._supervisor: NodeSupervisor | None = None
        self._proxy_router: APIRouter | None = None
        self._gateway_secret: str | None = None
        self._leadership: DbviewLeadership | None = None

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

    def _require_dbview_secret(self) -> None:
        """Fail fast unless the mandatory at-rest encryption key is present."""
        if len(os.environ.get("DBVIEW_SECRET", "")) < 16:
            raise DbviewConfigurationError(
                "DBVIEW_SECRET (>= 16 chars) is required by the dbview plugin: "
                "it encrypts stored connection strings at rest and must remain "
                "stable across restarts. Set it in the host environment."
            )

    def _resolve_gateway_secret(self) -> str:
        """The gateway secret **every** worker must sign identity headers with.

        Under multi-worker leadership only the leader spawns the single Node
        child, but *every* worker's proxy forwards identity to it — so all
        workers must present the exact secret that child validates against. A
        per-worker random value (the old behaviour) would make follower-signed
        requests fail the child's ``timingSafeEqual`` check with 401.

        Resolution order:
          1. An operator-provided ``DBVIEW_GATEWAY_SECRET`` (already shared via
             the environment across every forked worker) wins verbatim.
          2. Otherwise derive it deterministically from the stable, shared
             ``DBVIEW_SECRET`` via HMAC-SHA256 — same value in every worker,
             >= 16 chars, and not derivable by other local processes that don't
             already hold ``DBVIEW_SECRET``.
        """
        explicit = os.environ.get("DBVIEW_GATEWAY_SECRET", "")
        if len(explicit) >= 16:
            return explicit
        base = os.environ.get("DBVIEW_SECRET", "").encode("utf-8")
        return hmac.new(base, b"dbview-gateway-secret-v1", hashlib.sha256).hexdigest()

    def _resolve_internal_port(
        self, *, coordinated: bool, config: Dict[str, Any] | None
    ) -> int | None:
        """Pick the upstream port, pinning a shared one under leadership.

        Every worker runs this and must agree on the port so followers know
        where the single leader-owned child listens without any cross-worker
        publication. An explicit config/env port always wins; otherwise a
        coordinated (Postgres-backed) deployment pins the fixed default while a
        degraded single worker keeps the historical ephemeral allocation.
        """
        explicit = (config or {}).get("port")
        if explicit is not None:
            return int(explicit)
        env_port = os.environ.get("DBVIEW_INTERNAL_PORT")
        if env_port:
            try:
                return int(env_port)
            except ValueError:
                logger.warning(
                    "[dbview] invalid DBVIEW_INTERNAL_PORT=%r; ignoring", env_port
                )
        return _DEFAULT_INTERNAL_PORT if coordinated else None

    def _compose_child_env(self) -> dict[str, str]:
        """Plugin-owned child env: gateway auth contract + safe defaults.

        * ``DBVIEW_SECRET`` must be operator-provided and stable — it
          encrypts persisted connection strings; generating it here would
          silently orphan all stored connections on every restart.
        * ``DBVIEW_JWT_SECRET`` is only consumed by the (disabled) local JWT
          flow, so a per-boot value is a safe default.
        * ``DBVIEW_DATA_DIR`` defaults to ``plugins/dbview/var/data`` so
          runtime state never lands inside the vendored source tree.

        Assumes ``self._gateway_secret`` is already resolved by ``initialize``
        (shared across every worker so follower-forwarded identity is accepted
        by the single leader-owned child).
        """
        self._require_dbview_secret()

        extra_env: dict[str, str] = {}

        assert self._gateway_secret is not None  # set in initialize()
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
        self._require_dbview_secret()

        # Elect the single Node-child owner across workers. Only the leader
        # spawns the child; followers proxy to the leader-owned child on the
        # shared port. This keeps the (single-instance) dbview app's in-memory
        # stores — connections, mirrored users, sessions — consistent under a
        # multi-worker (WEB_CONCURRENCY>1) deployment.
        leadership = await acquire_dbview_leadership()
        self._leadership = leadership
        coordinated = not leadership.degraded

        # Shared identity-signing secret (must precede _compose_child_env).
        self._gateway_secret = self._resolve_gateway_secret()

        internal_port = self._resolve_internal_port(
            coordinated=coordinated, config=config
        )
        supervisor_overrides: Dict[str, Any] = {
            key: value
            for key, value in (config or {}).items()
            if key in {"mode", "host", "port"}
        }
        if internal_port is not None:
            supervisor_overrides["port"] = internal_port

        supervisor_config = build_supervisor_config(
            _PLUGIN_DIR,
            extra_env=self._compose_child_env(),
            # Central LLM governance: the operator's per-plugin pin (auth
            # console) is translated into child env overrides at every spawn.
            env_provider=governed_child_env,
            overrides=supervisor_overrides,
        )
        supervisor = NodeSupervisor(supervisor_config)
        self._supervisor = supervisor

        try:
            if leadership.is_leader:
                await supervisor.start()
            else:
                await supervisor.start_follower()
        except (NodeNotAvailableError, FileNotFoundError) as exc:
            # Misconfigured host: re-raise so the loader marks the plugin
            # FAILED — that's how operators discover the issue early.
            logger.error("[dbview] activation aborted: %s", exc)
            await self._release_leadership()
            self._supervisor = None
            raise
        except StartupTimeoutError as exc:
            logger.error("[dbview] startup timeout: %s", exc)
            try:
                await supervisor.stop()
            finally:
                await self._release_leadership()
                self._supervisor = None
            raise

        self._proxy_router = build_proxy_router(
            upstream_base_url_provider=lambda: supervisor.base_url,
            healthy_provider=supervisor.is_healthy,
            gateway_secret_provider=lambda: self._gateway_secret,
            proxy_prefix=_PROXY_PREFIX,
        )
        logger.info(
            "[dbview] plugin ready (upstream=%s, prefix=%s, central-auth=on, role=%s)",
            supervisor.base_url,
            _PROXY_PREFIX,
            "leader" if leadership.is_leader else "follower",
        )

    async def _release_leadership(self) -> None:
        """Release the advisory lock so another worker can win the child."""
        if self._leadership is not None:
            try:
                await self._leadership.release()
            except Exception as exc:  # pragma: no cover — best-effort cleanup
                logger.warning("[dbview] leadership release raised: %s", exc)
            self._leadership = None

    async def shutdown(self) -> None:
        if self._supervisor is not None:
            try:
                await self._supervisor.stop()
            except Exception as exc:  # pragma: no cover — defensive
                logger.warning("[dbview] supervisor stop raised: %s", exc)
            self._supervisor = None
        await self._release_leadership()
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
