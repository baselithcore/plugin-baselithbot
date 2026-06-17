"""MCP tool surface for BaselithOptimizeProcess.

Returned from :meth:`Plugin.get_mcp_tools` and registered with the core MCP
server, so an external client (Claude Desktop, an IDE, another agent) can inspect
process health and drive optimization over the native Model Context Protocol —
making BOP a first-class participant in the framework's agent ecosystem.

Every handler is async and returns a JSON-serialisable dict via the framework's
:class:`~core.plugins.result.SkillResult` envelope (``ok``/``fail``) — never
raising, so a tool error degrades to a structured payload instead of tearing
down the JSON-RPC connection.
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger
from core.plugins.result import fail, ok

from .event_models import Event
from .mcp_insights import build_insight_mcp_tools
from .resources import Resource
from .service import BopService

logger = get_logger(__name__)

__all__ = ["build_bop_mcp_tools"]


def build_bop_mcp_tools(service: BopService) -> list[dict[str, Any]]:
    """Build MCP tool definitions bound to a BOP service instance.

    Args:
        service: The shared :class:`BopService`.

    Returns:
        Tool definitions in the framework's ``{name, description, input_schema,
        handler}`` shape.
    """

    async def list_processes() -> dict[str, Any]:
        try:
            processes = await service.list_processes()
            return ok(
                [p.model_dump(mode="json") for p in processes],
                message=f"{len(processes)} process(es) mapped",
            ).model_dump()
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.error("mcp_tool_error", tool="list_processes", error=str(exc))
            return fail(str(exc), error_code="list_failed").model_dump()

    async def get_process_health(process_id: str) -> dict[str, Any]:
        try:
            if await service.get_process(process_id) is None:
                return fail(
                    f"process '{process_id}' not found", error_code="not_found"
                ).model_dump()
            snapshots = await service.snapshots(process_id)
            bottlenecks = await service.list_bottlenecks(process_id)
            return ok(
                {
                    "snapshots": [s.model_dump(mode="json") for s in snapshots],
                    "bottlenecks": [b.model_dump(mode="json") for b in bottlenecks],
                },
                message=(
                    f"{len(bottlenecks)} bottleneck(s) across {len(snapshots)} KPI(s)"
                ),
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="get_process_health", error=str(exc))
            return fail(str(exc), error_code="health_failed").model_dump()

    async def optimize_process(
        process_id: str, context: str = "", max_proposals: int = 5
    ) -> dict[str, Any]:
        try:
            proposals = await service.optimize(process_id, context, max_proposals)
            if proposals is None:
                return fail(
                    f"process '{process_id}' not found", error_code="not_found"
                ).model_dump()
            return ok(
                [p.model_dump(mode="json") for p in proposals],
                message=f"{len(proposals)} advisory proposal(s) generated",
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="optimize_process", error=str(exc))
            return fail(str(exc), error_code="optimize_failed").model_dump()

    async def mine_event_log(
        process_id: str, events: list[dict[str, Any]], name: str = ""
    ) -> dict[str, Any]:
        try:
            parsed = [Event.model_validate(e) for e in events]
            result = await service.import_event_log(process_id, parsed, name)
            return ok(
                result.model_dump(mode="json"),
                message=(
                    f"Discovered {len(result.activity_stats)} activities, "
                    f"{len(result.variants)} variant(s) from {result.case_count} cases"
                ),
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="mine_event_log", error=str(exc))
            return fail(str(exc), error_code="mining_failed").model_dump()

    async def check_conformance(
        process_id: str, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        try:
            parsed = [Event.model_validate(e) for e in events]
            report = await service.run_conformance(process_id, parsed)
            if report is None:
                return fail(
                    f"process '{process_id}' not found", error_code="not_found"
                ).model_dump()
            return ok(
                report.model_dump(mode="json"),
                message=(
                    f"fitness {report.fitness:.2f}, alignment "
                    f"{report.alignment_fitness:.2f}, {report.deviating_cases} "
                    "deviating case(s)"
                ),
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="check_conformance", error=str(exc))
            return fail(str(exc), error_code="conformance_failed").model_dump()

    async def forecast(process_id: str) -> dict[str, Any]:
        try:
            forecasts = await service.forecasts(process_id)
            breaches = sum(1 for f in forecasts if f.will_breach)
            return ok(
                [f.model_dump(mode="json") for f in forecasts],
                message=f"{breaches} predicted breach(es) across {len(forecasts)} KPI(s)",
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="forecast", error=str(exc))
            return fail(str(exc), error_code="forecast_failed").model_dump()

    async def simulate(process_id: str) -> dict[str, Any]:
        try:
            result = await service.simulate(process_id)
            if result is None:
                return fail(
                    f"process '{process_id}' not found", error_code="not_found"
                ).model_dump()
            return ok(
                result.model_dump(mode="json"),
                message=(
                    f"cycle {result.cycle_time_seconds:.0f}s, cost "
                    f"{result.cost_per_case} {result.currency}/case"
                ),
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="simulate", error=str(exc))
            return fail(str(exc), error_code="simulate_failed").model_dump()

    async def list_proposals(process_id: str = "") -> dict[str, Any]:
        try:
            proposals = await service.list_proposals(process_id or None)
            return ok(
                [p.model_dump(mode="json") for p in proposals],
                message=f"{len(proposals)} proposal(s)",
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="list_proposals", error=str(exc))
            return fail(str(exc), error_code="list_failed").model_dump()

    async def report(process_id: str, format: str = "markdown") -> dict[str, Any]:
        try:
            fmt = "csv" if format == "csv" else "markdown"
            rendered = await service.report(process_id, fmt)
            if rendered is None:
                return fail(
                    f"process '{process_id}' not found", error_code="not_found"
                ).model_dump()
            return ok(
                {"format": fmt, "content": rendered},
                message=f"{fmt} report for '{process_id}'",
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="report", error=str(exc))
            return fail(str(exc), error_code="report_failed").model_dump()

    async def cost_report(process_id: str) -> dict[str, Any]:
        try:
            report = await service.cost_report(process_id)
            if report is None:
                return fail(
                    f"process '{process_id}' not found", error_code="not_found"
                ).model_dump()
            return ok(
                report.model_dump(mode="json"),
                message=(
                    f"{report.per_case_cost} {report.currency}/case "
                    f"({report.costed_nodes}/{report.total_nodes} steps costed)"
                ),
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="cost_report", error=str(exc))
            return fail(str(exc), error_code="cost_failed").model_dump()

    async def list_resources() -> dict[str, Any]:
        try:
            resources = await service.list_resources()
            return ok(
                [r.model_dump(mode="json") for r in resources],
                message=f"{len(resources)} resource(s) in pool",
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="list_resources", error=str(exc))
            return fail(str(exc), error_code="list_failed").model_dump()

    async def create_resource(
        name: str,
        role: str = "",
        cost_per_hour: float = 0.0,
        currency: str = "EUR",
    ) -> dict[str, Any]:
        try:
            import uuid

            resource = Resource(
                id=uuid.uuid4().hex,
                name=name,
                role=role,
                cost_per_hour=cost_per_hour,
                currency=currency,
            )
            saved = await service.create_resource(resource)
            return ok(
                saved.model_dump(mode="json"),
                message=f"resource '{saved.name}' created",
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="create_resource", error=str(exc))
            return fail(str(exc), error_code="create_failed").model_dump()

    async def assign_resource(
        process_id: str, node_id: str, resource_id: str | None = None
    ) -> dict[str, Any]:
        try:
            process = await service.assign_resource(process_id, node_id, resource_id)
            if process is None:
                return fail(
                    "process, step, or resource not found", error_code="not_found"
                ).model_dump()
            return ok(
                process.model_dump(mode="json"),
                message=(
                    f"resource assigned to step '{node_id}'"
                    if resource_id
                    else f"resource cleared from step '{node_id}'"
                ),
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="assign_resource", error=str(exc))
            return fail(str(exc), error_code="assign_failed").model_dump()

    _pid_schema = {
        "type": "object",
        "properties": {"process_id": {"type": "string"}},
        "required": ["process_id"],
    }
    _events_schema = {
        "type": "object",
        "properties": {
            "process_id": {"type": "string"},
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "case_id": {"type": "string"},
                        "activity": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "resource": {"type": "string"},
                    },
                    "required": ["case_id", "activity", "timestamp"],
                },
            },
        },
        "required": ["process_id", "events"],
    }

    return [
        *build_insight_mcp_tools(service),
        {
            "name": "bop_list_processes",
            "description": "List all business processes mapped in BOP.",
            "input_schema": {"type": "object", "properties": {}},
            "handler": list_processes,
        },
        {
            "name": "bop_get_process_health",
            "description": (
                "Get current KPI snapshots and detected bottlenecks for a process."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "process_id": {
                        "type": "string",
                        "description": "Id of the mapped process.",
                    }
                },
                "required": ["process_id"],
            },
            "handler": get_process_health,
        },
        {
            "name": "bop_optimize_process",
            "description": (
                "Run an advisory, human-in-the-loop optimization pass and return "
                "proposals grounded in detected bottlenecks."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "process_id": {"type": "string"},
                    "context": {
                        "type": "string",
                        "description": "Optional operator hints.",
                    },
                    "max_proposals": {
                        "type": "integer",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["process_id"],
            },
            "handler": optimize_process,
        },
        {
            "name": "bop_mine_event_log",
            "description": (
                "Discover a process model + variant analytics from a raw event "
                "log (process mining). Each event needs case_id, activity, and an "
                "ISO timestamp."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "process_id": {"type": "string"},
                    "name": {"type": "string"},
                    "events": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "case_id": {"type": "string"},
                                "activity": {"type": "string"},
                                "timestamp": {"type": "string"},
                                "resource": {"type": "string"},
                            },
                            "required": ["case_id", "activity", "timestamp"],
                        },
                    },
                },
                "required": ["process_id", "events"],
            },
            "handler": mine_event_log,
        },
        {
            "name": "bop_check_conformance",
            "description": (
                "Score an event log against a process model: frequency + "
                "alignment fitness, deviations, and deviation cost."
            ),
            "input_schema": _events_schema,
            "handler": check_conformance,
        },
        {
            "name": "bop_forecast",
            "description": (
                "Forecast which KPIs are trending toward a breach (predictive)."
            ),
            "input_schema": _pid_schema,
            "handler": forecast,
        },
        {
            "name": "bop_simulate",
            "description": (
                "Predict the current process's cycle time and cost-per-case."
            ),
            "input_schema": _pid_schema,
            "handler": simulate,
        },
        {
            "name": "bop_list_proposals",
            "description": (
                "List optimization proposals (read-only). Approving/rejecting is "
                "deliberately NOT an MCP tool — it requires a human via the "
                "authenticated, approver-gated HTTP endpoint."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"process_id": {"type": "string"}},
            },
            "handler": list_proposals,
        },
        {
            "name": "bop_cost_report",
            "description": "Per-case and annual cost rollup for a process.",
            "input_schema": _pid_schema,
            "handler": cost_report,
        },
        {
            "name": "bop_list_resources",
            "description": (
                "List the tenant's assignable resource pool (people/teams/machines "
                "with role and hourly rate)."
            ),
            "input_schema": {"type": "object", "properties": {}},
            "handler": list_resources,
        },
        {
            "name": "bop_create_resource",
            "description": (
                "Add a resource to the pool. Its hourly rate becomes the source of "
                "truth for the labour cost of any step it is assigned to."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "cost_per_hour": {"type": "number", "minimum": 0},
                    "currency": {"type": "string"},
                },
                "required": ["name"],
            },
            "handler": create_resource,
        },
        {
            "name": "bop_assign_resource",
            "description": (
                "Assign a resource to a process step (or clear it by omitting "
                "resource_id). The resource's rate/role materialize onto the step "
                "so cost rollups stay accurate."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "process_id": {"type": "string"},
                    "node_id": {"type": "string"},
                    "resource_id": {"type": "string"},
                },
                "required": ["process_id", "node_id"],
            },
            "handler": assign_resource,
        },
        {
            "name": "bop_report",
            "description": (
                "Render an executive report (structure, cost, cycle time, KPIs, "
                "bottlenecks, proposals) as 'markdown' (default) or 'csv'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "process_id": {"type": "string"},
                    "format": {"type": "string", "enum": ["markdown", "csv"]},
                },
                "required": ["process_id"],
            },
            "handler": report,
        },
    ]
