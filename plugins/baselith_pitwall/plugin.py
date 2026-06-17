"""Plugin entry point for BaselithPitwall.

Wires the sentient digital pit wall into the framework across four surfaces:

* :class:`AgentPlugin` — intent patterns route race-strategy questions here.
* :class:`RouterPlugin` — the fully-async REST + SSE API under
  ``/api/baselith_pitwall`` (RBAC-guarded, tenant- and session-scoped).
* MCP tools — read/advisory strategy tools for the core MCP server.
* a mounted React/Vite dashboard SPA at ``/baselith_pitwall`` (built artifacts
  only; ``ui/src`` never ships in the wheel).

Enterprise wiring: a :class:`PitwallSessionManager` owns one live engine per
:class:`RaceSession` over a pluggable :class:`PitwallStore` (in-memory default,
opt-in Postgres). Tenancy, RBAC, rate limiting, and idempotency are configured
here and consumed by the router package. ``core/`` is never modified (Sacred
Core) — only framework primitives are used.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.observability.logging import get_logger
from core.plugins import AgentPlugin, RouterPlugin

from .config import PitwallConfig
from .idempotency import IdempotencyCache
from .mcp_tools import build_pitwall_mcp_tools
from .ratelimit import RateLimiter
from .routers import build_pitwall_router
from .session_manager import PitwallSessionManager
from .store import PitwallStore, build_store

logger = get_logger(__name__)
MOUNT_PATH = "/baselith_pitwall"
_UI_DIST = Path(__file__).resolve().parent / "ui" / "dist"

__all__ = ["BaselithPitwallPlugin"]


class BaselithPitwallPlugin(AgentPlugin, RouterPlugin):
    """Sentient digital pit wall: telemetry → swarm → MCTS → FIA-checked calls."""

    def __init__(self) -> None:
        super().__init__()
        self._config: PitwallConfig | None = None
        self._store: PitwallStore | None = None
        self._manager: PitwallSessionManager | None = None
        self._idempotency = IdempotencyCache()
        self._rate_limiter: RateLimiter | None = None

    @property
    def config(self) -> PitwallConfig:
        """The validated runtime configuration (built on first access)."""
        if self._config is None:
            self._config = PitwallConfig()
        return self._config

    @property
    def store(self) -> PitwallStore:
        """The persistence backend (built on first access)."""
        if self._store is None:
            self._store = build_store(self.config.model_dump())
        return self._store

    @property
    def manager(self) -> PitwallSessionManager:
        """The multi-session orchestration registry."""
        if self._manager is None:
            self._manager = PitwallSessionManager(self.config, self.store)
        return self._manager

    @property
    def idempotency(self) -> IdempotencyCache:
        """The per-tenant idempotency cache for safe POST retries."""
        return self._idempotency

    @property
    def rate_limiter(self) -> RateLimiter:
        """The per-tenant rate limiter (disabled unless configured)."""
        if self._rate_limiter is None:
            self._rate_limiter = RateLimiter(self.config.rate_limit_per_min)
        return self._rate_limiter

    async def initialize(self, config: dict[str, Any]) -> None:
        """Build config/store/manager, start the demo session, register in DI."""
        await super().initialize(config)
        self._config = PitwallConfig.from_plugin_config(config)
        self._store = build_store(self._config.model_dump())
        self._rate_limiter = RateLimiter(self._config.rate_limit_per_min)
        self._manager = PitwallSessionManager(self._config, self._store)
        await self._manager.initialize()
        try:
            from core.di.container import ServiceRegistry

            ServiceRegistry.register(PitwallSessionManager, self._manager)
        except Exception as exc:  # noqa: BLE001 — DI is optional at boot
            logger.debug("pitwall_di_register_skipped", error=str(exc))
        logger.info(
            "pitwall_initialized",
            persistence=self._config.persistence,
            auth=self._config.auth_enabled,
            llm=self._config.use_llm,
        )

    async def shutdown(self) -> None:
        """Stop all live sessions and release resources."""
        if self._manager is not None:
            await self._manager.shutdown()
        await super().shutdown()

    # -- Agent plugin ------------------------------------------------------

    def create_agent(self, service: Any, **kwargs: Any) -> Any:
        """No bespoke conversational agent; strategy lives in the service swarm."""
        del service, kwargs
        return None

    def get_intent_patterns(self) -> list[dict[str, Any]]:
        """Route pit-strategy questions toward the pit-wall surface."""
        return [
            {
                "name": "pitwall_strategy",
                "patterns": [
                    "pit strategy",
                    "should we box",
                    "when to pit",
                    "tyre strategy",
                    "strategia gara",
                    "quando fermarsi",
                    "strategia gomme",
                ],
                "description": "Race strategy / pit-stop decision queries.",
                "priority": 5,
            }
        ]

    # -- Router plugin -----------------------------------------------------

    def create_router(self) -> Any:
        """Build the plugin's FastAPI router (REST + SSE)."""
        return build_pitwall_router(self)

    def get_router_prefix(self) -> str:
        """Mount the API under the plugin namespace."""
        return f"/api/{self.metadata.name}"

    # -- MCP ---------------------------------------------------------------

    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Expose read/advisory pit-wall tools to the MCP server."""
        return build_pitwall_mcp_tools(self.manager, self.metadata.version)

    # -- UI ----------------------------------------------------------------

    def get_ui_tabs(self) -> list[dict[str, str]]:
        """Register a sidebar entry pointing at the bundled dashboard.

        A single, statically-readable tab id (the plugin name) so the central
        Access Control matrix can key per-tab RBAC on ``(baselith_pitwall, …)``.
        """
        return [
            {
                "id": self.metadata.name,
                "label": "Pit Wall",
                "url": MOUNT_PATH,
                "icon": "activity",
            }
        ]

    @classmethod
    def setup_app_middleware(cls, app: Any) -> None:
        """Mount the built SPA before the middleware stack freezes.

        Missing build output degrades gracefully — the API still serves; only
        the bundled UI is unavailable.
        """
        if not _UI_DIST.exists():
            logger.info("pitwall_ui_not_built", path=str(_UI_DIST))
            return
        try:
            from fastapi.staticfiles import StaticFiles

            app.mount(
                MOUNT_PATH,
                StaticFiles(directory=str(_UI_DIST), html=True),
                name="baselith_pitwall",
            )
            logger.info("pitwall_spa_mounted", path=MOUNT_PATH)
        except Exception as exc:  # noqa: BLE001 — never break app construction
            logger.error("pitwall_spa_mount_failed", error=str(exc))
