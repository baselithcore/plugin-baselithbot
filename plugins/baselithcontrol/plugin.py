"""Plugin entry point for BaselithControl.

Exposes the framework as a single command bridge:

* :class:`RouterPlugin` — the fully-async aggregation/control API (REST + SSE)
  under ``/api/baselithcontrol``.
* a mounted React/Vite dashboard SPA at ``/baselithcontrol`` (built artifacts
  only; the source under ``ui/src`` never ships in the wheel).

The plugin discovers every other loaded plugin dynamically through the core
registry — there is no per-plugin hardcoding. ``core/`` is never modified
(Sacred Core); only framework primitives are imported.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.observability.logging import get_logger
from core.plugins import RouterPlugin

from .config import ControlConfig

logger = get_logger(__name__)
MOUNT_PATH = "/baselithcontrol"
_UI_DIST = Path(__file__).resolve().parent / "ui" / "dist"

__all__ = ["BaselithControlPlugin"]


class BaselithControlPlugin(RouterPlugin):
    """Centralized control-plane dashboard: discover, monitor, and govern plugins."""

    def __init__(self) -> None:
        super().__init__()
        self._control_config: ControlConfig | None = None

    @property
    def config(self) -> ControlConfig:
        """The validated runtime configuration (built on first access)."""
        if self._control_config is None:
            self._control_config = ControlConfig()
        return self._control_config

    async def initialize(self, config: dict[str, Any]) -> None:
        """Validate config and publish it for request-time service construction."""
        await super().initialize(config)
        self._control_config = ControlConfig.from_plugin_config(config)
        logger.info(
            "BaselithControl initialized (gate=%s, require_admin=%s)",
            self._control_config.gate_level.value,
            self._control_config.require_admin,
        )

    def create_router(self) -> Any:
        """Build the aggregation/control router mounted at ``/api/baselithcontrol``."""
        from fastapi import APIRouter

        from .router import build_control_router

        router = APIRouter()
        router.include_router(build_control_router())
        return router

    def get_ui_tabs(self) -> list[dict[str, str]]:
        """Expose each dashboard section as an individually gateable tab.

        Tab ids mirror the SPA's top-nav ids (``dashboard``/``events``/
        ``system``) so the central RBAC matrix can restrict any one of them and
        the SPA hides what the caller may not access (default-allow otherwise).
        """
        return [
            {"id": "dashboard", "label": "Overview", "url": MOUNT_PATH},
            {"id": "events", "label": "Events", "url": MOUNT_PATH},
            {"id": "system", "label": "System Console", "url": MOUNT_PATH},
        ]

    @classmethod
    def setup_app_middleware(cls, app: Any) -> None:
        """Mount the built SPA before the middleware stack freezes.

        Runs at app-construction time. The plugin config is also stashed on
        ``app.state`` here so request-time dependencies can read it without a
        registry round-trip. Missing build output degrades gracefully — the API
        still serves; only the bundled UI is unavailable.
        """
        try:
            app.state.baselithcontrol_config = ControlConfig()
        except Exception as exc:  # noqa: BLE001 — config errors must not block boot
            logger.warning("BaselithControl config load failed: %s", exc)

        # Per-plugin request telemetry: a pure-ASGI meter wrapping the whole app.
        # It attributes each request to a plugin via the registry's own route
        # matcher and records count/latency/errors — the honest per-plugin signal
        # (CPU/RAM can't be split across in-process plugins). Best-effort: a
        # metering failure must never block app construction or a request.
        try:
            from .service.plugin_meter import PluginMeterMiddleware

            app.add_middleware(PluginMeterMiddleware)
            logger.info("BaselithControl per-plugin request meter installed")
        except Exception as exc:  # noqa: BLE001 — telemetry is optional
            logger.warning("BaselithControl meter install failed: %s", exc)

        # Retained lifecycle timeline: construct the buffer now so it subscribes
        # to the event bus at boot and captures activity from the first event
        # (the SSE bridge only serves live, per-connection frames). Best-effort.
        try:
            from .service.lifecycle import get_lifecycle_buffer

            get_lifecycle_buffer()
            logger.info("BaselithControl lifecycle timeline attached")
        except Exception as exc:  # noqa: BLE001 — telemetry is optional
            logger.warning("BaselithControl lifecycle attach failed: %s", exc)

        if not _UI_DIST.exists():
            logger.info(
                "BaselithControl UI not built; SPA mount skipped (%s)", _UI_DIST
            )
            return
        try:
            from fastapi.staticfiles import StaticFiles

            app.mount(
                MOUNT_PATH,
                StaticFiles(directory=str(_UI_DIST), html=True),
                name="baselithcontrol",
            )
            logger.info("BaselithControl SPA mounted at %s", MOUNT_PATH)
        except Exception as exc:  # noqa: BLE001 — never break app construction
            logger.error("BaselithControl SPA mount failed: %s", exc, exc_info=True)
