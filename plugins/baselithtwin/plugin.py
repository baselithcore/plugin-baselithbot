"""Plugin entry point for BaselithTwin.

Wires the digital twin into the framework across three capability surfaces:

* :class:`AgentPlugin` — a persona agent that drafts replies in the owner's voice.
* :class:`RouterPlugin` — the fully-async REST + SSE + webhook API for the
  monitoring dashboard and the OpenWA integration.
* :class:`GraphPlugin` — knowledge-graph schema so contacts and salient facts can
  live as first-class graph entities.

The service is constructed lazily on first access so plugin discovery and
type-checking stay cheap. All domain logic lives under this package — ``core/``
is never modified (Sacred Core).
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger
from core.plugins import AgentPlugin, GraphPlugin, RouterPlugin

from .agent import TwinAgent
from .config import TwinConfig
from .mcp_tools import build_twin_mcp_tools
from .router import create_router
from .service import TwinService

logger = get_logger(__name__)

__all__ = ["BaselithTwinPlugin"]


class BaselithTwinPlugin(AgentPlugin, RouterPlugin, GraphPlugin):
    """An engineered WhatsApp digital twin: learn, remember, and reply as the owner."""

    def __init__(self) -> None:
        super().__init__()
        self._service: TwinService | None = None
        self._twin_config: TwinConfig | None = None

    @property
    def config(self) -> TwinConfig:
        """The validated runtime configuration (built on first access)."""
        if self._twin_config is None:
            self._twin_config = TwinConfig()
        return self._twin_config

    @property
    def service(self) -> TwinService:
        """Lazily construct and cache the twin service with the chosen backends."""
        if self._service is None:
            self._service = TwinService(self.config)
        return self._service

    async def initialize(self, config: dict[str, Any]) -> None:
        """Build config/service from the plugin block and prepare backends.

        Eager-constructs the service (so config errors surface at boot) and
        registers it in the DI container so the MCP layer and other plugins can
        resolve the shared instance.
        """
        await super().initialize(config)
        # NB: the base class binds the raw dict to ``self._config``; the typed
        # twin settings live under ``self._twin_config`` (read by the ``config``
        # property). Build them *before* the service is first touched, otherwise
        # the plugin block (owner_name/autonomy/…) is silently ignored and only
        # env overrides apply.
        self._twin_config = TwinConfig.from_plugin_config(config)
        await self.service.initialize()
        try:
            from core.di.container import ServiceRegistry

            ServiceRegistry.register(TwinService, self.service)
        except Exception as exc:  # noqa: BLE001 — DI is optional at boot
            logger.debug("twin_di_register_skipped", error=str(exc))
        logger.info("twin_initialized", autonomy=self.config.autonomy.value)

    async def shutdown(self) -> None:
        """Disconnect the gateway and release resources."""
        if self._service is not None:
            await self._service.shutdown()
        await super().shutdown()

    # -- Agent plugin ------------------------------------------------------

    def create_agent(self, service: Any, **kwargs: Any) -> TwinAgent:
        """Create the persona agent bound to the supplied LLM service."""
        return TwinAgent(service, owner_name=self.config.owner_name)

    def get_intent_patterns(self) -> list[dict[str, Any]]:
        """Route persona/reply-as-me requests to the twin agent."""
        return [
            {
                "name": "twin_reply_as_me",
                "patterns": [
                    "reply as me",
                    "draft a whatsapp reply",
                    "respond like me",
                    "rispondi come me",
                    "scrivi come me",
                ],
                "handler": "execute",
                "priority": 1,
            }
        ]

    # -- Router plugin -----------------------------------------------------

    def create_router(self) -> Any:
        """Create the plugin's FastAPI router."""
        return create_router(self)

    def get_router_prefix(self) -> str:
        """Mount the API under the plugin namespace."""
        return f"/api/{self.metadata.name}"

    # -- MCP ---------------------------------------------------------------

    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Expose read/advisory twin tools to the MCP server (no send/approve)."""
        return build_twin_mcp_tools(self.service, self.metadata.version)

    # -- UI ----------------------------------------------------------------

    def get_ui_tabs(self) -> list[dict[str, str]]:
        """Register a sidebar entry pointing at the bundled dashboard."""
        return [
            {
                "id": self.metadata.name,
                "label": "Digital Twin",
                "url": f"/api/{self.metadata.name}/ui/",
                "icon": "user",
            }
        ]

    # -- Graph plugin ------------------------------------------------------

    def register_entity_types(self) -> list[dict[str, Any]]:
        """Register contact and salient-fact node types in the knowledge graph."""
        return [
            {
                "type": "twin_contact",
                "display_name": "WhatsApp Contact",
                "schema": {"contact_id": str, "display_name": str},
                "icon": "💬",
            },
            {
                "type": "twin_fact",
                "display_name": "Salient Fact",
                "schema": {"text": str, "salience": str},
                "icon": "🧠",
            },
        ]

    def register_relationship_types(self) -> list[dict[str, Any]]:
        """Register the contact→fact memory edge."""
        return [
            {
                "type": "TWIN_KNOWS",
                "source_types": ["twin_contact"],
                "target_types": ["twin_fact"],
                "properties_schema": {},
                "bidirectional": False,
            }
        ]

    # -- Config schema -----------------------------------------------------

    def get_config_schema(self) -> dict[str, Any]:
        """JSON Schema for plugin configuration, validated before initialize."""
        return {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "default": True},
                "owner_name": {"type": "string", "default": "Owner"},
                "autonomy": {
                    "type": "string",
                    "enum": ["suggest", "whitelist", "full"],
                    "default": "whitelist",
                    "description": "Reply autonomy; 'whitelist' is the safe default.",
                },
                "gateway": {
                    "type": "string",
                    "enum": ["fake", "openwa"],
                    "default": "fake",
                },
                "persistence": {
                    "type": "string",
                    "enum": ["memory", "postgres"],
                    "default": "memory",
                },
                "semantic_enabled": {"type": "boolean", "default": False},
            },
            "additionalProperties": True,
        }
