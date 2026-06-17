"""FastAPI surface for BaselithTwin.

Assembles the configuration/control and real-time sub-routers, a health probe,
and the bundled dashboard mount into one router for the plugin gateway. The
router owns no business logic — it validates, delegates to :class:`TwinService`,
and shapes HTTP responses.
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger

from .i18n import negotiate_locale, translate
from .router_config import build_config_router
from .router_control import build_control_router
from .router_realtime import build_realtime_router
from .ui_static import mount_dashboard_ui

logger = get_logger(__name__)


def create_router(plugin_instance: Any) -> Any:
    """Build the plugin's API router bound to its service.

    Args:
        plugin_instance: The owning plugin, exposing ``.service``, ``.config``
            and ``.metadata``.

    Returns:
        A configured ``APIRouter``.
    """
    from fastapi import APIRouter, Header

    from .guards import build_guards

    service = plugin_instance.service
    config = plugin_instance.config
    version = plugin_instance.metadata.version
    guards = build_guards(config)

    router = APIRouter(prefix="", tags=["twin"])

    @router.get("/health")
    async def health(
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Liveness probe with a localized status message."""
        return {
            "plugin": plugin_instance.metadata.name,
            "version": version,
            "message": translate("twin.health.ok", negotiate_locale(accept_language)),
        }

    router.include_router(build_config_router(service, version, guards))
    router.include_router(build_control_router(service, guards))
    router.include_router(build_realtime_router(service, config))
    mount_dashboard_ui(router)
    return router


__all__ = ["create_router"]
