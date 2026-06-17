"""Plugin entry point for the BaselithCore Agents Platform.

Wires the platform's service into the framework: it exposes the dashboard router
and the MCP tool surface, declares its config schema, and registers a sidebar
tab. The heavy service is constructed lazily on first access so plugin discovery
and type-checking stay cheap.
"""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from core.observability.logging import get_logger
from core.plugins import RouterPlugin

from .mcp_tools import build_platform_mcp_tools
from .router import create_router
from .service import AgentPlatformService
from .tools_runtime import ToolConfig
from .types import ModelProvider

logger = get_logger(__name__)

__all__ = ["AgentsPlatformPlugin"]


class AgentsPlatformPlugin(RouterPlugin):
    """Natural-language → scoped, doc-grounded coding agents.

    Capabilities exposed to the framework:
        * REST API + bundled React dashboard (``RouterPlugin``).
        * MCP tools for documentation grounding and agent control.
        * A configuration schema validated before ``initialize``.
    """

    def __init__(self) -> None:
        super().__init__()
        self._service: AgentPlatformService | None = None

    @property
    def service(self) -> AgentPlatformService:
        """Lazily construct and cache the platform service from config."""
        if self._service is None:
            provider_name = str(self.get_config("default_provider", "ollama")).lower()
            try:
                provider = ModelProvider(provider_name)
            except ValueError:
                logger.warning("invalid_default_provider", value=provider_name)
                provider = ModelProvider.OLLAMA
            self._service = AgentPlatformService(
                default_provider=provider,
                ollama_base=self.get_config("ollama_base", None),
                tool_config=self._build_tool_config(),
            )
        return self._service

    def _build_tool_config(self) -> ToolConfig:
        """Assemble runtime-tool credentials/policy from plugin config.

        Telegram bot token is wrapped in ``SecretStr`` so it never leaks via
        ``repr``/Sentry frames; it is unwrapped only at the moment of the API
        call inside the tool itself.
        """
        token = self.get_config("telegram_bot_token", None)
        return ToolConfig(
            telegram_bot_token=SecretStr(token) if token else None,
            telegram_chat_id=self.get_config("telegram_chat_id", None),
            allow_internal=bool(self.get_config("allow_internal_http", False)),
        )

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialise the plugin and start the interval scheduler."""
        await super().initialize(config)
        await self.service.start()

    async def shutdown(self) -> None:
        """Stop the scheduler and release resources."""
        if self._service is not None:
            await self._service.stop()
        await super().shutdown()

    # -- Router plugin -----------------------------------------------------

    def create_router(self) -> Any:
        """Create the plugin's FastAPI router."""
        return create_router(self)

    def get_router_prefix(self) -> str:
        """Mount the API under the plugin namespace."""
        return f"/api/{self.metadata.name}"

    # -- MCP ---------------------------------------------------------------

    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Expose documentation and agent-control tools to the MCP server."""
        return build_platform_mcp_tools(self.service)

    # -- UI ----------------------------------------------------------------

    def get_ui_tabs(self) -> list[dict[str, str]]:
        """Expose each dashboard section as an individually gateable tab.

        Tab ids mirror the SPA's router sections so the central RBAC matrix can
        restrict any one of them; the SPA hides denied sections (default-allow).
        """
        url = f"/api/{self.metadata.name}/ui/"
        return [
            {"id": "builder", "label": "Builder", "url": url, "icon": "sparkles"},
            {"id": "agents", "label": "Agents", "url": url, "icon": "sparkles"},
            {"id": "runs", "label": "Runs", "url": url, "icon": "sparkles"},
            {"id": "schedules", "label": "Schedules", "url": url, "icon": "sparkles"},
            {"id": "docs", "label": "Docs · MCP", "url": url, "icon": "sparkles"},
            {"id": "models", "label": "Models", "url": url, "icon": "sparkles"},
        ]

    # -- Config schema -----------------------------------------------------

    def get_config_schema(self) -> dict[str, Any]:
        """JSON Schema for plugin configuration, validated before initialize."""
        return {
            "type": "object",
            "properties": {
                "default_provider": {
                    "type": "string",
                    "enum": [p.value for p in ModelProvider],
                    "default": "ollama",
                    "description": "Default model backend for synthesis and runs.",
                },
                "ollama_base": {
                    "type": ["string", "null"],
                    "default": None,
                    "description": "Base URL for a local Ollama daemon.",
                },
                "telegram_bot_token": {
                    "type": ["string", "null"],
                    "default": None,
                    "description": "Bot token for the send_telegram runtime tool.",
                },
                "telegram_chat_id": {
                    "type": ["string", "null"],
                    "default": None,
                    "description": "Default Telegram chat id for outbound messages.",
                },
                "allow_internal_http": {
                    "type": "boolean",
                    "default": False,
                    "description": "Allow http_get to reach private/loopback hosts.",
                },
            },
            "additionalProperties": False,
        }
