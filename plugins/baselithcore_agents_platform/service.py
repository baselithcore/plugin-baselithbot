"""Application service binding the platform's subsystems together.

This is the plugin's core seam: the builder, runtime, documentation indexer, and
registry are composed here once and exposed through a small, intention-revealing
API. The FastAPI router and the MCP bridge are both thin adapters over this
object, which keeps transport concerns out of the domain logic.
"""

from __future__ import annotations

from pathlib import Path

from core.observability.logging import get_logger

from .builder import BlueprintBuilder
from .docs_index import DocIndexer
from .executor import AgentExecutor
from .providers import describe_models
from .registry import AgentRegistry
from .runtime import AgentRuntime
from .scheduler import IntervalScheduler
from .tools_runtime import ToolConfig, available_tool_names
from .types import (
    AgentBlueprint,
    AgentCapability,
    AgentRunResult,
    DocCitation,
    ModelProvider,
    ScheduleSpec,
)
import uuid

logger = get_logger(__name__)

__all__ = ["AgentPlatformService"]

# plugins/baselithcore_agents_platform/service.py -> repository root.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class AgentPlatformService:
    """Facade over blueprint synthesis, scoped execution, and documentation.

    Args:
        default_provider: Provider used for blueprint synthesis and as the
            default for generated agents.
        ollama_base: Optional Ollama base URL for local-model runs.
        repo_root: Override for the documentation index root (defaults to the
            repository root inferred from this module's location).
    """

    def __init__(
        self,
        default_provider: ModelProvider = ModelProvider.OLLAMA,
        ollama_base: str | None = None,
        repo_root: Path | None = None,
        tool_config: ToolConfig | None = None,
    ) -> None:
        self._docs = DocIndexer(repo_root or _REPO_ROOT)
        self._builder = BlueprintBuilder(default_provider, ollama_base)
        self._executor = AgentExecutor(tool_config or ToolConfig(), ollama_base)
        self._runtime = AgentRuntime(self._docs, ollama_base, self._executor)
        self._registry = AgentRegistry()
        self._scheduler = IntervalScheduler(self._on_schedule_fire)
        logger.info("agent_platform_service_ready", provider=default_provider.value)

    # -- Lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        """Start the interval scheduler (called from plugin initialize)."""
        await self._scheduler.start()

    async def stop(self) -> None:
        """Stop the interval scheduler (called from plugin shutdown)."""
        await self._scheduler.stop()

    # -- Blueprints --------------------------------------------------------

    async def create_blueprint(self, description: str) -> AgentBlueprint:
        """Synthesise a blueprint from natural language and persist it."""
        blueprint = await self._builder.build(description)
        return await self._registry.save_blueprint(blueprint)

    async def save_blueprint(self, blueprint: AgentBlueprint) -> AgentBlueprint:
        """Persist an externally constructed blueprint."""
        return await self._registry.save_blueprint(blueprint)

    async def get_blueprint(self, blueprint_id: str) -> AgentBlueprint | None:
        """Fetch a blueprint by id."""
        return await self._registry.get_blueprint(blueprint_id)

    async def list_blueprints(self) -> list[AgentBlueprint]:
        """List all known blueprints."""
        return await self._registry.list_blueprints()

    async def delete_blueprint(self, blueprint_id: str) -> bool:
        """Delete a blueprint by id."""
        return await self._registry.delete_blueprint(blueprint_id)

    # -- Runs --------------------------------------------------------------

    async def run_agent(
        self,
        blueprint_id: str,
        capability: AgentCapability,
        task: str,
        extra_context: str = "",
    ) -> AgentRunResult | None:
        """Execute a capability of a stored agent.

        Returns:
            The run result, or None if the blueprint id is unknown.
        """
        blueprint = await self._registry.get_blueprint(blueprint_id)
        if blueprint is None:
            return None
        result = await self._runtime.run(blueprint, capability, task, extra_context)
        return await self._registry.record_run(result)

    async def list_runs(self, blueprint_id: str | None = None) -> list[AgentRunResult]:
        """List recent runs, optionally filtered by blueprint."""
        return await self._registry.list_runs(blueprint_id)

    # -- Schedules ---------------------------------------------------------

    async def create_schedule(
        self,
        blueprint_id: str,
        capability: AgentCapability,
        task: str,
        interval_seconds: float,
    ) -> ScheduleSpec | None:
        """Register a recurring run; returns None if the blueprint is unknown."""
        if await self._registry.get_blueprint(blueprint_id) is None:
            return None
        spec = ScheduleSpec(
            id=uuid.uuid4().hex,
            blueprint_id=blueprint_id,
            capability=capability,
            task=task,
            interval_seconds=interval_seconds,
        )
        return self._scheduler.add(spec)

    def list_schedules(self) -> list[ScheduleSpec]:
        """Return all registered schedules."""
        return self._scheduler.list()

    def delete_schedule(self, schedule_id: str) -> bool:
        """Cancel and remove a schedule."""
        return self._scheduler.remove(schedule_id)

    async def _on_schedule_fire(self, spec: ScheduleSpec) -> AgentRunResult | None:
        """Scheduler callback: execute the scheduled capability."""
        return await self.run_agent(spec.blueprint_id, spec.capability, spec.task)

    # -- Documentation -----------------------------------------------------

    async def search_docs(
        self, query: str, namespaces: list[str] | None = None, top_k: int = 4
    ) -> list[DocCitation]:
        """Search the framework documentation index."""
        return await self._docs.search(query, namespaces, top_k)

    async def get_doc(self, namespace: str) -> str | None:
        """Return the full text of an indexed document."""
        return await self._docs.get_document(namespace)

    async def doc_namespaces(self) -> list[str]:
        """List all indexed documentation namespaces."""
        return await self._docs.namespaces()

    # -- Catalogue ---------------------------------------------------------

    @staticmethod
    def describe_models() -> list[dict[str, object]]:
        """Return the provider/model catalogue for the UI."""
        return describe_models()

    @staticmethod
    def describe_tools() -> list[str]:
        """Return the names of the built-in runtime tools for the UI."""
        return available_tool_names()
