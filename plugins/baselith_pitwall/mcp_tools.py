"""MCP tools exposing the pit wall's read/advisory surface.

Read-only and advisory tools only: status, per-car stint state, on-demand race
simulation, and recent recommendations. Submitting telemetry/radio stays on the
authenticated HTTP surface so an agent cannot inject unvalidated race state over
MCP. The MCP surface operates on the ``default`` tenant; an optional
``session_id`` selects which live session (defaulting to the bundled demo).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.plugins.result import SkillResult, fail, ok

from .session_manager import DEFAULT_SESSION_ID

if TYPE_CHECKING:
    from .service import PitwallService
    from .session_manager import PitwallSessionManager

_CAR_SCHEMA = {
    "type": "object",
    "properties": {
        "car_id": {"type": "string", "description": "Car identifier."},
        "session_id": {
            "type": "string",
            "description": "Optional live session id (default: demo).",
        },
    },
    "required": ["car_id"],
}


def build_pitwall_mcp_tools(
    manager: "PitwallSessionManager", version: str
) -> list[dict[str, Any]]:
    """Build the MCP tool descriptors bound to the session manager."""

    def _svc(session_id: str | None) -> "PitwallService | None":
        return manager.get_service("default", session_id or DEFAULT_SESSION_ID)

    async def pitwall_status(session_id: str | None = None) -> SkillResult:
        """Report the pit wall's health and configuration."""
        service = _svc(session_id)
        if service is None:
            return fail("No live session.")
        return ok(service.status(version).model_dump(mode="json"), message="status")

    async def pitwall_stint(car_id: str, session_id: str | None = None) -> SkillResult:
        """Return the current belief state for a car."""
        service = _svc(session_id)
        state = service.get_stint(car_id) if service else None
        if state is None:
            return fail(f"No telemetry for car '{car_id}'.")
        return ok(state.model_dump(mode="json"), message="stint")

    async def pitwall_simulate(
        car_id: str, session_id: str | None = None
    ) -> SkillResult:
        """Run an MCTS race scenario for a car and return the best path."""
        service = _svc(session_id)
        state = service.get_stint(car_id) if service else None
        if state is None or service is None:
            return fail(f"No telemetry for car '{car_id}'.")
        scenario = await service.simulator.explore(state)
        if scenario is None:
            return fail("No viable scenario within the horizon.")
        return ok(scenario.model_dump(mode="json"), message="scenario")

    async def pitwall_recommendations(
        car_id: str | None = None, session_id: str | None = None
    ) -> SkillResult:
        """List recent confirmed, FIA-validated recommendations."""
        service = _svc(session_id)
        if service is None:
            return fail("No live session.")
        recs = service.recent_recommendations(car_id=car_id, limit=20)
        return ok(
            [r.model_dump(mode="json") for r in recs], message=f"{len(recs)} recs"
        )

    async def pitwall_battle(car_id: str, session_id: str | None = None) -> SkillResult:
        """Battle Forecast vs the closest rival (laps-to-strike + undercut delta)."""
        service = _svc(session_id)
        forecast = service.battle_forecast(car_id) if service else None
        if forecast is None:
            return fail(f"No rival/telemetry for car '{car_id}'.")
        return ok(forecast.model_dump(mode="json"), message="battle forecast")

    async def pitwall_outcome(
        car_id: str, session_id: str | None = None
    ) -> SkillResult:
        """Monte-Carlo outcome distribution: P(win/podium) + expected finish."""
        service = _svc(session_id)
        dist = service.outcome(car_id) if service else None
        if dist is None:
            return fail(f"No telemetry for car '{car_id}'.")
        return ok(dist.model_dump(mode="json"), message="outcome distribution")

    async def pitwall_indicators(
        car_id: str, session_id: str | None = None
    ) -> SkillResult:
        """Fused, cross-source indicator set with provenance for a car."""
        service = _svc(session_id)
        indicators = service.indicators(car_id) if service else None
        if indicators is None:
            return fail(f"No telemetry for car '{car_id}'.")
        return ok(indicators.model_dump(mode="json"), message="fused indicators")

    async def pitwall_intel(car_id: str, session_id: str | None = None) -> SkillResult:
        """AI-synthesised intelligence brief over the fused indicators."""
        service = _svc(session_id)
        if service is None:
            return fail(f"No telemetry for car '{car_id}'.")
        brief = await service.intelligence(car_id)
        if brief is None:
            return fail(f"No telemetry for car '{car_id}'.")
        return ok({"brief": brief}, message="intelligence brief")

    return [
        {
            "name": "pitwall_status",
            "description": "Get the digital pit wall's health and configuration.",
            "handler": pitwall_status,
            "input_schema": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Optional live session id (default: demo).",
                    }
                },
            },
        },
        {
            "name": "pitwall_stint",
            "description": "Get the current derived stint/belief state for a car.",
            "handler": pitwall_stint,
            "input_schema": _CAR_SCHEMA,
        },
        {
            "name": "pitwall_simulate",
            "description": "Run an MCTS race-strategy simulation for a car.",
            "handler": pitwall_simulate,
            "input_schema": _CAR_SCHEMA,
        },
        {
            "name": "pitwall_recommendations",
            "description": "List recent FIA-validated pit-wall recommendations.",
            "handler": pitwall_recommendations,
            "input_schema": {
                "type": "object",
                "properties": {
                    "car_id": {
                        "type": "string",
                        "description": "Optional car id to filter by.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional live session id (default: demo).",
                    },
                },
            },
        },
        {
            "name": "pitwall_battle",
            "description": "Battle Forecast vs the closest rival for a car.",
            "handler": pitwall_battle,
            "input_schema": _CAR_SCHEMA,
        },
        {
            "name": "pitwall_outcome",
            "description": "Monte-Carlo race-outcome distribution for a car.",
            "handler": pitwall_outcome,
            "input_schema": _CAR_SCHEMA,
        },
        {
            "name": "pitwall_indicators",
            "description": "Fused cross-source indicators with provenance for a car.",
            "handler": pitwall_indicators,
            "input_schema": _CAR_SCHEMA,
        },
        {
            "name": "pitwall_intel",
            "description": "AI intelligence brief over a car's fused indicators.",
            "handler": pitwall_intel,
            "input_schema": _CAR_SCHEMA,
        },
    ]


__all__ = ["build_pitwall_mcp_tools"]
