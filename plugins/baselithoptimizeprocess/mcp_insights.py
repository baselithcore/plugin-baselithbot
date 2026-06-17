"""MCP tools for the advanced insight lenses (variants, performance, root cause).

Split from :mod:`mcp_tools` to keep both files under the size cap; the result is
concatenated into the plugin's full MCP surface. Each handler reads the *stored*
event log via :class:`BopService` and returns a structured
:class:`~core.plugins.result.SkillResult` envelope — never raising, so a tool
error degrades to a payload instead of tearing down the JSON-RPC connection.
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger
from core.plugins.result import fail, ok

from .event_models import Event
from .service import BopService

logger = get_logger(__name__)

__all__ = ["build_insight_mcp_tools"]

_PID_SCHEMA = {
    "type": "object",
    "properties": {"process_id": {"type": "string"}},
    "required": ["process_id"],
}


def build_insight_mcp_tools(service: BopService) -> list[dict[str, Any]]:
    """Build the variant / performance / root-cause MCP tool definitions."""

    async def variants(process_id: str) -> dict[str, Any]:
        try:
            report = await service.variant_report(process_id)
            if report is None:
                return fail(
                    f"process '{process_id}' not found", error_code="not_found"
                ).model_dump()
            return ok(
                report.model_dump(mode="json"),
                message=(
                    f"{report.variant_count} variant(s) over {report.case_count} "
                    f"cases; {report.deviating_cases} deviating"
                ),
            ).model_dump()
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.error("mcp_tool_error", tool="variants", error=str(exc))
            return fail(str(exc), error_code="variants_failed").model_dump()

    async def performance(process_id: str) -> dict[str, Any]:
        try:
            report = await service.performance_report(process_id)
            if report is None:
                return fail(
                    f"process '{process_id}' not found", error_code="not_found"
                ).model_dump()
            breaching = sum(1 for s in report.slas if s.breaches > 0)
            return ok(
                report.model_dump(mode="json"),
                message=(
                    f"P90 cycle {report.cycle_time.p90:.0f}s over "
                    f"{report.case_count} cases; {breaching} SLA(s) breaching"
                ),
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="performance", error=str(exc))
            return fail(str(exc), error_code="performance_failed").model_dump()

    async def predict_case(
        process_id: str, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        try:
            parsed = [Event.model_validate(e) for e in events]
            prediction = await service.predict_case(process_id, parsed)
            if prediction is None:
                return fail(
                    f"process '{process_id}' not found or empty trace",
                    error_code="not_found",
                ).model_dump()
            nxt = (
                prediction.next_activities[0].activity
                if prediction.next_activities
                else "—"
            )
            return ok(
                prediction.model_dump(mode="json"),
                message=(
                    f"at '{prediction.current_activity}', ~"
                    f"{prediction.predicted_remaining_seconds:.0f}s left, "
                    f"next likely '{nxt}'"
                ),
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="predict_case", error=str(exc))
            return fail(str(exc), error_code="predict_failed").model_dump()

    async def root_cause(
        process_id: str, threshold_seconds: float | None = None
    ) -> dict[str, Any]:
        try:
            report = await service.root_cause_report(process_id, threshold_seconds)
            if report is None:
                return fail(
                    f"process '{process_id}' not found", error_code="not_found"
                ).model_dump()
            top = report.factors[0].factor if report.factors else "none"
            return ok(
                report.model_dump(mode="json"),
                message=(
                    f"{report.bad_cases}/{report.total_cases} slow case(s); "
                    f"{len(report.factors)} factor(s), top: {top}"
                ),
            ).model_dump()
        except Exception as exc:  # pragma: no cover
            logger.error("mcp_tool_error", tool="root_cause", error=str(exc))
            return fail(str(exc), error_code="root_cause_failed").model_dump()

    return [
        {
            "name": "bop_variants",
            "description": (
                "Variant explorer: every distinct process path with its case "
                "share, throughput percentiles, model conformance, and cost. "
                "Reads the stored event log (mine the process first)."
            ),
            "input_schema": _PID_SCHEMA,
            "handler": variants,
        },
        {
            "name": "bop_performance",
            "description": (
                "Throughput-time percentiles (P50/P90/P95/P99), per-activity "
                "waiting times, and SLA breach rates over the stored event log."
            ),
            "input_schema": _PID_SCHEMA,
            "handler": performance,
        },
        {
            "name": "bop_root_cause",
            "description": (
                "Root-cause analysis: rank the case attributes (resource, "
                "activity, variant, rework) most associated with slow cases. "
                "Optional threshold_seconds; defaults to the P75 case duration."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "process_id": {"type": "string"},
                    "threshold_seconds": {"type": "number", "minimum": 0},
                },
                "required": ["process_id"],
            },
            "handler": root_cause,
        },
        {
            "name": "bop_predict_case",
            "description": (
                "Predictive monitoring: forecast a running case from its events "
                "so far — remaining time, most-likely next activity, and SLA "
                "violation probability — using a model learned from history."
            ),
            "input_schema": {
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
            },
            "handler": predict_case,
        },
    ]
