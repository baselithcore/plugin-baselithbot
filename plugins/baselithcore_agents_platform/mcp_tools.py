"""MCP tool surface for the Agents Platform.

These definitions are returned from :meth:`Plugin.get_mcp_tools` and registered
with the core MCP server, so an external client (Claude Desktop, an IDE) can
both read BaselithCore documentation and drive the platform's agents over the
native Model Context Protocol. Documentation grounding is the primary contract:
``search_baselith_docs`` is how a coding model stays inside the framework's scope.

Every handler is async and returns a JSON-serialisable dict — never raising —
so a tool error degrades to a structured ``{"status": "error"}`` payload rather
than tearing down the JSON-RPC connection.
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger
from core.plugins.result import fail, ok

from .service import AgentPlatformService
from .types import AgentCapability

logger = get_logger(__name__)

__all__ = ["build_platform_mcp_tools"]


def build_platform_mcp_tools(service: AgentPlatformService) -> list[dict[str, Any]]:
    """Build MCP tool definitions bound to a platform service instance.

    Args:
        service: The shared :class:`AgentPlatformService`.

    Returns:
        Tool definitions in the framework's ``{name, description, input_schema,
        handler}`` shape.
    """

    async def search_baselith_docs(
        query: str, namespace_prefix: str = "", top_k: int = 4
    ) -> dict[str, Any]:
        try:
            namespaces = [namespace_prefix] if namespace_prefix else None
            hits = await service.search_docs(query, namespaces, top_k)
            return ok(
                [h.model_dump() for h in hits],
                message=f"{len(hits)} documentation section(s) matched",
            ).model_dump()
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.error("mcp_tool_error", tool="search_baselith_docs", error=str(exc))
            return fail(str(exc), error_code="docs_search_failed").model_dump()

    async def get_baselith_doc(namespace: str) -> dict[str, Any]:
        try:
            text = await service.get_doc(namespace)
            if text is None:
                return fail(
                    f"document '{namespace}' not found", error_code="not_found"
                ).model_dump()
            return ok({"namespace": namespace, "content": text}).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="get_baselith_doc", error=str(exc))
            return fail(str(exc), error_code="doc_read_failed").model_dump()

    async def create_agent(description: str) -> dict[str, Any]:
        try:
            blueprint = await service.create_blueprint(description)
            return ok(
                blueprint.model_dump(mode="json"),
                message=f"agent '{blueprint.id}' created",
            ).model_dump()
        except Exception as exc:
            logger.error("mcp_tool_error", tool="create_agent", error=str(exc))
            return fail(str(exc), error_code="create_agent_failed").model_dump()

    async def run_agent(
        blueprint_id: str, capability: str, task: str, code: str = ""
    ) -> dict[str, Any]:
        try:
            cap = AgentCapability(capability.strip().lower())
        except ValueError:
            return fail(
                f"unknown capability '{capability}'", error_code="bad_capability"
            ).model_dump()
        try:
            result = await service.run_agent(blueprint_id, cap, task, code)
            if result is None:
                return fail(
                    f"blueprint '{blueprint_id}' not found", error_code="not_found"
                ).model_dump()
            payload = result.model_dump(mode="json")
            if result.status.value in ("succeeded",):
                return ok(payload, message=result.explanation).model_dump()
            return fail(
                result.error or f"run {result.status.value}",
                error_code=f"run_{result.status.value}",
                data=payload,
            ).model_dump()
        except Exception as exc:
            logger.error("mcp_tool_error", tool="run_agent", error=str(exc))
            return fail(str(exc), error_code="run_agent_failed").model_dump()

    async def schedule_agent(
        blueprint_id: str, capability: str, task: str, interval_seconds: float
    ) -> dict[str, Any]:
        try:
            cap = AgentCapability(capability.strip().lower())
        except ValueError:
            return fail(
                f"unknown capability '{capability}'", error_code="bad_capability"
            ).model_dump()
        try:
            spec = await service.create_schedule(
                blueprint_id, cap, task, interval_seconds
            )
            if spec is None:
                return fail(
                    f"blueprint '{blueprint_id}' not found", error_code="not_found"
                ).model_dump()
            return ok(
                spec.model_dump(mode="json"),
                message=f"scheduled every {interval_seconds:.0f}s",
            ).model_dump()
        except Exception as exc:
            logger.error("mcp_tool_error", tool="schedule_agent", error=str(exc))
            return fail(str(exc), error_code="schedule_failed").model_dump()

    return [
        {
            "name": "search_baselith_docs",
            "description": (
                "Search the BaselithCore framework documentation. Use this to "
                "ground code in the framework's conventions and stay in-scope."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "namespace_prefix": {
                        "type": "string",
                        "description": "Optional doc path prefix filter",
                        "default": "",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 4,
                    },
                },
                "required": ["query"],
            },
            "handler": search_baselith_docs,
        },
        {
            "name": "get_baselith_doc",
            "description": "Fetch the full text of an indexed framework document.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Document namespace, e.g. 'CLAUDE.md'",
                    }
                },
                "required": ["namespace"],
            },
            "handler": get_baselith_doc,
        },
        {
            "name": "create_agent",
            "description": (
                "Synthesise a scoped coding agent from a natural-language "
                "description and register it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What the agent should do",
                    }
                },
                "required": ["description"],
            },
            "handler": create_agent,
        },
        {
            "name": "run_agent",
            "description": (
                "Run a registered agent capability (generate, fix, test, "
                "refactor, explain) against a task, grounded in framework docs."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "blueprint_id": {"type": "string"},
                    "capability": {
                        "type": "string",
                        "enum": [c.value for c in AgentCapability],
                    },
                    "task": {"type": "string"},
                    "code": {
                        "type": "string",
                        "description": "Source code for fix/test capabilities",
                        "default": "",
                    },
                },
                "required": ["blueprint_id", "capability", "task"],
            },
            "handler": run_agent,
        },
        {
            "name": "schedule_agent",
            "description": (
                "Schedule a registered agent capability to run on a recurring "
                "interval (e.g. operate every 8 hours)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "blueprint_id": {"type": "string"},
                    "capability": {
                        "type": "string",
                        "enum": [c.value for c in AgentCapability],
                    },
                    "task": {"type": "string"},
                    "interval_seconds": {
                        "type": "number",
                        "description": "Seconds between runs (5 … 604800).",
                    },
                },
                "required": ["blueprint_id", "capability", "task", "interval_seconds"],
            },
            "handler": schedule_agent,
        },
    ]
