"""Official API Routers plugin."""

from typing import Any, List

from core.plugins import Plugin


class ApiRoutersPlugin(Plugin):
    """Plugin packaging the framework's default HTTP routers.

    The legacy routers (chat, admin, status, tenant, …) are mounted at app
    build time via the grandfathered ``core.routers`` compatibility shims.
    Newer surfaces that wrap recently-added core subsystems are exposed here
    through the standard dynamic plugin-router mechanism so they mount at the
    root prefix alongside the legacy ones — no new ``core -> plugins`` import
    and no edit to the frozen ``core/routers`` package.
    """

    def get_router_prefix(self) -> str:
        """Mount routers at the root, matching the legacy router style."""
        return ""

    def get_routers(self) -> List[Any]:
        """Expose the dynamically-mounted routers (privacy, webhooks)."""
        from .privacy import router as privacy_router
        from .webhooks import router as webhooks_router

        return [privacy_router, webhooks_router]

    async def initialize(self, config: dict) -> None:
        await super().initialize(config)
