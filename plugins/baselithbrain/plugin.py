"""BaselithBrain plugin entrypoint.

Embeds a self-contained second-brain backend (local Markdown vault + derived
search/graph index) and its compiled React/Vite SPA as one ASGI sub-application
mounted at ``/baselithbrain``.

Integration design mirrors the established sub-app-mount pattern:

* **Mount, don't re-export.** The backend ships its routers at canonical paths
  (``/api/*``); we mount the whole app under one prefix so Starlette strips it
  and the SPA (built with ``VITE_BASE_PATH=/baselithbrain/``) reaches them. The
  mount happens in :meth:`setup_app_middleware` because Starlette freezes the
  route table before the async plugin lifespan runs.

* **Drive the lifespan in the background.** A mounted sub-app never receives
  ASGI lifespan events, so :meth:`initialize` enters the backend's own lifespan
  (vault scan + index build) as a background task — a large vault can never
  block core boot; endpoints answer 503 until the first index build completes.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import yaml

from core.observability.logging import get_logger
from core.plugins import Plugin

from . import _bootstrap

logger = get_logger(__name__)

#: Path the backend + SPA are mounted under on the host application.
MOUNT_PATH = "/baselithbrain"

_CONFIG_FILE = Path(__file__).resolve().parents[2] / "configs" / "plugins.yaml"


def _plugin_enabled() -> bool:
    """Best-effort read of ``configs/plugins.yaml`` enablement.

    ``setup_app_middleware`` runs for every plugin that declares the hook,
    regardless of enablement, so we gate the mount ourselves. Defaults to
    enabled when the config is unreadable (mirrors loader leniency).
    """
    try:
        data = yaml.safe_load(_CONFIG_FILE.read_text(encoding="utf-8")) or {}
        entry = data.get("baselithbrain")
        if isinstance(entry, dict):
            return bool(entry.get("enabled", True))
    except (OSError, yaml.YAMLError):
        pass
    return True


class BaselithBrainPlugin(Plugin):
    """Embeds the second-brain backend + SPA under ``/baselithbrain``."""

    def __init__(self) -> None:
        super().__init__()
        self._lifespan_cm: Any | None = None
        self._boot_task: asyncio.Task[None] | None = None

    # ---- app-construction-time mount -------------------------------------
    @classmethod
    def setup_app_middleware(cls, app: Any) -> None:
        """Mount the backend sub-app + SPA on the host application."""
        if not _plugin_enabled():
            logger.info("BaselithBrain disabled in plugins.yaml — skipping mount")
            return
        try:
            _bootstrap.ensure_ready()
            from .app_factory import get_app

            app.mount(MOUNT_PATH, get_app(), name="baselithbrain")
            logger.info("🧠 BaselithBrain mounted at %s", MOUNT_PATH)
        except Exception as exc:  # noqa: BLE001 — never block host boot
            logger.error("BaselithBrain mount failed: %s", exc, exc_info=True)

    # ---- lifecycle -------------------------------------------------------
    async def initialize(self, config: dict[str, Any]) -> None:
        await super().initialize(config)
        _bootstrap.ensure_ready()
        try:
            from .app_factory import get_app

            brain_app = get_app()
        except Exception as exc:  # noqa: BLE001
            logger.error("BaselithBrain import failed: %s", exc, exc_info=True)
            return

        self._lifespan_cm = brain_app.router.lifespan_context(brain_app)

        async def _boot() -> None:
            try:
                await self._lifespan_cm.__aenter__()  # type: ignore[union-attr]
                logger.info("✅ BaselithBrain index ready")
            except Exception as exc:  # noqa: BLE001 — degraded, endpoints 503
                logger.error("BaselithBrain index build failed: %s", exc)

        self._boot_task = asyncio.create_task(_boot())
        logger.info("BaselithBrain initializing (index build in background)")

    async def shutdown(self) -> None:
        if self._boot_task is not None:
            self._boot_task.cancel()
            try:
                await self._boot_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if self._lifespan_cm is not None:
            try:
                await self._lifespan_cm.__aexit__(None, None, None)
            except Exception as exc:  # noqa: BLE001
                logger.warning("BaselithBrain shutdown: %s", exc)
        await super().shutdown()

    # ---- dashboard surface ----------------------------------------------
    def get_ui_tabs(self) -> list[dict[str, str]]:
        return [{"id": "baselithbrain", "label": "Second Brain", "url": MOUNT_PATH}]

    # ---- MCP surface -----------------------------------------------------
    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Expose the vault as MCP tools on the host's central MCP server.

        The host registers these on its stdio transport (Claude Desktop / IDEs);
        the same tools are also served over HTTP at ``/baselithbrain/api/mcp``.
        Failures degrade to an empty list so a missing index never breaks MCP
        discovery for other plugins.
        """
        try:
            _bootstrap.ensure_ready()
            from .backend.mcp_service import brain_tool_defs

            return brain_tool_defs()
        except Exception as exc:  # noqa: BLE001 — degraded, no brain tools
            logger.error("BaselithBrain MCP tools unavailable: %s", exc)
            return []
