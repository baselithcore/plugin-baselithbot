"""Plugin entry point for BaselithOptimizeProcess (BOP).

Wires the BOP service into the framework across three capability surfaces:

* :class:`AgentPlugin` — the optimizer agent that turns bottlenecks into
  advisory, human-in-the-loop proposals.
* :class:`RouterPlugin` — the fully-async REST + SSE monitoring API.
* :class:`GraphPlugin` — the knowledge-graph schema that lets a mapped business
  process live as a first-class execution graph.

The service is constructed lazily on first access so plugin discovery and
type-checking stay cheap. All domain logic lives under this package — ``core/``
is never touched (Sacred Core).
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger
from core.plugins import AgentPlugin, GraphPlugin, RouterPlugin

from .agent import BopOptimizerAgent
from .mcp_tools import build_bop_mcp_tools
from .router import create_router
from .service import BopService

logger = get_logger(__name__)

__all__ = ["BopPlugin"]


class BopPlugin(AgentPlugin, RouterPlugin, GraphPlugin):
    """Map, monitor, and autonomously optimize complex business processes.

    Capabilities exposed to the framework:
        * A REST API + real-time SSE metrics feed (``RouterPlugin``).
        * An advisory optimizer agent (``AgentPlugin``).
        * Process-graph entity/relationship schema (``GraphPlugin``).
    """

    def __init__(self) -> None:
        super().__init__()
        self._service: BopService | None = None
        self._config: dict[str, Any] = {}

    @property
    def service(self) -> BopService:
        """Lazily construct and cache the BOP service with the chosen backend."""
        if self._service is None:
            from .store import build_store

            self._service = BopService(store=build_store(self._config))
        return self._service

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialise the plugin and register its service in the DI container.

        Eager-constructs the service (so config errors surface at boot) and
        prepares its storage backend — for Postgres persistence this creates the
        schema. Registers it under :class:`BopService` so other plugins / the MCP
        layer can resolve the shared instance via ``ServiceRegistry``.
        """
        await super().initialize(config)
        self._config = config or {}
        await self.service.initialize()
        from core.di.container import ServiceRegistry

        ServiceRegistry.register(BopService, self.service)

    async def shutdown(self) -> None:
        """Release resources (in-memory backend needs no teardown in v0)."""
        await super().shutdown()

    # -- Agent plugin ------------------------------------------------------

    def create_agent(self, service: Any, **kwargs: Any) -> BopOptimizerAgent:
        """Create the optimizer agent, bound to the supplied LLM service."""
        return BopOptimizerAgent(service)

    def get_intent_patterns(self) -> list[dict[str, Any]]:
        """Route process-optimization requests to this plugin's agent."""
        return [
            {
                "name": "bop_optimize_process",
                "patterns": [
                    "optimize process",
                    "improve workflow",
                    "find bottleneck",
                    "process efficiency",
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
        """Expose process-health and optimization tools to the MCP server."""
        return build_bop_mcp_tools(self.service)

    # -- UI ----------------------------------------------------------------

    def get_ui_tabs(self) -> list[dict[str, str]]:
        """Expose each workspace section as an individually gateable tab.

        Tab ids mirror the SPA's ``TABS`` (workspace/types.ts) so the central
        RBAC matrix can restrict any one of them; the SPA hides denied sections
        (default-allow otherwise).
        """
        # Literal dicts (not a comprehension) so the RBAC static AST scanner can
        # discover every tab even when the plugin is disabled.
        url = f"/api/{self.metadata.name}/ui/"
        return [
            {"id": "map", "label": "Map", "url": url, "icon": "activity"},
            {"id": "monitor", "label": "Monitor", "url": url, "icon": "activity"},
            {"id": "analytics", "label": "Analyze", "url": url, "icon": "activity"},
            {"id": "variants", "label": "Variants", "url": url, "icon": "activity"},
            {
                "id": "performance",
                "label": "Performance",
                "url": url,
                "icon": "activity",
            },
            {"id": "rootcause", "label": "Root Cause", "url": url, "icon": "activity"},
            {"id": "predict", "label": "Predict", "url": url, "icon": "activity"},
            {"id": "conformance", "label": "Conform", "url": url, "icon": "activity"},
            {"id": "optimize", "label": "Optimize", "url": url, "icon": "activity"},
            {"id": "resources", "label": "Resources", "url": url, "icon": "activity"},
            {"id": "automation", "label": "Automate", "url": url, "icon": "activity"},
            {"id": "history", "label": "Govern", "url": url, "icon": "activity"},
        ]

    # -- Graph plugin ------------------------------------------------------

    def register_entity_types(self) -> list[dict[str, Any]]:
        """Register the process-graph node types in the knowledge graph."""
        return [
            {
                "type": "bop_process",
                "display_name": "Business Process",
                "schema": {"name": str, "description": str},
                "icon": "🛠️",
            },
            {
                "type": "bop_process_step",
                "display_name": "Process Step",
                "schema": {"name": str, "kind": str, "role": str},
                "icon": "⚙️",
            },
            {
                "type": "bop_kpi",
                "display_name": "Process KPI",
                "schema": {"name": str, "unit": str, "direction": str},
                "icon": "📈",
            },
        ]

    def register_relationship_types(self) -> list[dict[str, Any]]:
        """Register the transitions and measurement edges of a process."""
        return [
            {
                "type": "BOP_NEXT",
                "source_types": ["bop_process_step"],
                "target_types": ["bop_process_step"],
                "properties_schema": {"condition": str},
                "bidirectional": False,
            },
            {
                "type": "BOP_HAS_STEP",
                "source_types": ["bop_process"],
                "target_types": ["bop_process_step"],
                "properties_schema": {},
                "bidirectional": False,
            },
            {
                "type": "BOP_MEASURES",
                "source_types": ["bop_kpi"],
                "target_types": ["bop_process", "bop_process_step"],
                "properties_schema": {},
                "bidirectional": False,
            },
        ]

    # -- Config schema -----------------------------------------------------

    def get_config_schema(self) -> dict[str, Any]:
        """JSON Schema for plugin configuration, validated before initialize."""
        return {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether the plugin is active.",
                },
                "persistence": {
                    "type": "string",
                    "enum": ["memory", "postgres"],
                    "default": "memory",
                    "description": (
                        "Storage backend. 'memory' (default) is ephemeral; "
                        "'postgres' is durable and requires POSTGRES_ENABLED=true."
                    ),
                },
                "auth_enabled": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Opt-in RBAC. When true, endpoints are gated via the "
                        "auth plugin and tenant comes from the JWT (the tenant "
                        "header is ignored). When false (default) the API is "
                        "open and tenancy is header-based."
                    ),
                },
                "tenant_header": {
                    "type": "string",
                    "default": "X-Tenant-ID",
                    "description": (
                        "Request header carrying the tenant id in lightweight "
                        "(non-auth) mode."
                    ),
                },
                "rate_limit_per_min": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": (
                        "Per-tenant requests/minute on mutating endpoints "
                        "(ingest, optimize). 0 disables rate limiting."
                    ),
                },
            },
            "additionalProperties": True,
        }
