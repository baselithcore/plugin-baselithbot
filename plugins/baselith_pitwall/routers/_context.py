"""Mutating surface: telemetry, radio, race-control, weather, rivals, simulate.

All mutations are strategist-guarded, per-tenant rate-limited, and (for the
discrete acts) recorded in the audit ledger with the acting principal. Telemetry
and radio honour an ``Idempotency-Key`` header so a network retry can't
double-submit. High-rate telemetry frames are not audited individually (only
rate-limited); the discrete context changes are.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from ..models import (
    RaceControlStatus,
    RadioMessage,
    RivalCar,
    TelemetryFrame,
    WeatherState,
)
from ..session_models import AuditAction
from ._deps import Ctx, RouterContext, use_ctx


class RaceControlUpdate(BaseModel):
    """Request body for setting the race-control flag."""

    status: RaceControlStatus
    lap: int = 0


def register_context(router: APIRouter, rc: RouterContext) -> None:
    """Attach the mutating context endpoints to ``router``."""
    strategist = Depends(rc.strategist())
    viewer = Depends(rc.viewer())

    @router.post("/telemetry", dependencies=[strategist])
    async def ingest_telemetry(
        frame: TelemetryFrame,
        ctx: Ctx = use_ctx(rc),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        """Submit a single validated telemetry frame (external feed integration)."""
        rc.rate_check(ctx)
        cached = rc.idem_get(ctx, idempotency_key)
        if cached is not None:
            return cached
        await rc.live_service(ctx).bus.submit_frame(frame)
        return rc.idem_put(
            ctx,
            idempotency_key,
            {"accepted": True, "lap": frame.lap, "car_id": frame.car_id},
        )

    @router.post("/radio", dependencies=[strategist])
    async def ingest_radio(
        message: RadioMessage,
        ctx: Ctx = use_ctx(rc),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        """Submit a team-radio transmission; may trigger a recommendation."""
        rc.rate_check(ctx)
        cached = rc.idem_get(ctx, idempotency_key)
        if cached is not None:
            return cached
        service = rc.live_service(ctx)
        rec = await service.ingest_radio(message)
        await service.record_audit(
            AuditAction.RADIO_INGESTED, actor=ctx.actor, car_id=message.car_id
        )
        return rc.idem_put(
            ctx,
            idempotency_key,
            {
                "accepted": True,
                "recommendation": rec.model_dump(mode="json") if rec else None,
            },
        )

    @router.post("/race-control", dependencies=[strategist])
    async def set_race_control(
        update: RaceControlUpdate, ctx: Ctx = use_ctx(rc)
    ) -> dict[str, Any]:
        """Set the race-control flag (green/yellow/VSC/SC)."""
        service = rc.live_service(ctx)
        service.set_race_control(update.status, update.lap)
        await service.record_audit(
            AuditAction.RACE_CONTROL_SET,
            actor=ctx.actor,
            detail={"status": update.status.value, "lap": update.lap},
        )
        return {"status": update.status.value, "lap": update.lap}

    @router.post("/weather", dependencies=[strategist])
    async def set_weather(
        weather: WeatherState, ctx: Ctx = use_ctx(rc)
    ) -> dict[str, Any]:
        """Set the session weather state (drives wet/dry compound crossover)."""
        service = rc.live_service(ctx)
        service.set_weather(weather)
        await service.record_audit(
            AuditAction.WEATHER_SET,
            actor=ctx.actor,
            detail={"is_dry": weather.is_dry},
        )
        return {"accepted": True, "is_dry": weather.is_dry}

    @router.post("/rivals/{car_id}", dependencies=[strategist])
    async def set_rivals(
        car_id: str, rivals: list[RivalCar], ctx: Ctx = use_ctx(rc)
    ) -> dict[str, Any]:
        """Set the nearby competitors for battle/undercut analysis."""
        service = rc.live_service(ctx)
        service.set_rivals(car_id, rivals)
        await service.record_audit(
            AuditAction.RIVALS_SET,
            actor=ctx.actor,
            car_id=car_id,
            detail={"count": len(rivals)},
        )
        return {"accepted": True, "count": len(rivals)}

    @router.post("/simulate/{car_id}", dependencies=[viewer])
    async def simulate(
        car_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Run an on-demand MCTS race scenario for a car (no state change)."""
        service = rc.live_service(ctx)
        state = service.get_stint(car_id)
        if state is None:
            raise rc.error(404, "error.unknown_car", accept_language)
        scenario = await service.simulator.explore(state)
        if scenario is None:
            raise rc.error(422, "sim.no_scenario", accept_language)
        return scenario.model_dump(mode="json")


__all__ = ["register_context", "RaceControlUpdate"]
