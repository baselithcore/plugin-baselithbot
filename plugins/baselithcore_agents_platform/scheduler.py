"""Self-contained interval scheduler for recurring agent runs.

A minimal, dependency-free asyncio scheduler: each schedule owns one background
task that sleeps for its interval then fires a callback. It is intentionally
independent of baselithbot's CronScheduler so the plugin stays self-contained
and boots without any other plugin present.

The scheduler owns timing only; what a fire *does* is the injected callback —
the service wires it to ``run_agent`` and folds the outcome back into the spec.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from core.observability.logging import get_logger

from .types import AgentRunResult, ScheduleSpec, utcnow

logger = get_logger(__name__)

__all__ = ["IntervalScheduler", "ScheduleCallback"]

# Invoked on each tick; returns the run result (or None when the blueprint is
# gone) so the scheduler can update the spec's bookkeeping fields.
ScheduleCallback = Callable[[ScheduleSpec], Awaitable[AgentRunResult | None]]


class IntervalScheduler:
    """Runs registered :class:`ScheduleSpec` jobs on their intervals.

    Args:
        callback: Coroutine invoked on each fire with the schedule spec.
    """

    def __init__(self, callback: ScheduleCallback) -> None:
        self._callback = callback
        self._specs: dict[str, ScheduleSpec] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._running = False

    async def start(self) -> None:
        """Mark the scheduler running and (re)arm any enabled specs."""
        self._running = True
        for spec in self._specs.values():
            if spec.enabled and spec.id not in self._tasks:
                self._arm(spec)
        logger.info("scheduler_started", schedules=len(self._specs))

    async def stop(self) -> None:
        """Cancel all running jobs; specs are retained for restart."""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        for task in list(self._tasks.values()):
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        self._tasks.clear()
        logger.info("scheduler_stopped")

    def add(self, spec: ScheduleSpec) -> ScheduleSpec:
        """Register a schedule and arm it if the scheduler is running."""
        self._specs[spec.id] = spec
        if self._running and spec.enabled:
            self._arm(spec)
        return spec

    def remove(self, schedule_id: str) -> bool:
        """Cancel and drop a schedule; return True if it existed."""
        task = self._tasks.pop(schedule_id, None)
        if task is not None:
            task.cancel()
        return self._specs.pop(schedule_id, None) is not None

    def list(self) -> list[ScheduleSpec]:
        """Return all schedules, newest first."""
        return sorted(self._specs.values(), key=lambda s: s.created_at, reverse=True)

    def get(self, schedule_id: str) -> ScheduleSpec | None:
        """Return a schedule by id."""
        return self._specs.get(schedule_id)

    def _arm(self, spec: ScheduleSpec) -> None:
        """Spawn the background loop task for a spec."""
        self._tasks[spec.id] = asyncio.create_task(self._run_loop(spec))

    async def _run_loop(self, spec: ScheduleSpec) -> None:
        """Sleep-then-fire loop for a single schedule."""
        while self._running and spec.enabled:
            try:
                await asyncio.sleep(spec.interval_seconds)
            except asyncio.CancelledError:
                raise
            if not (self._running and spec.enabled):
                break
            await self._fire(spec)

    async def _fire(self, spec: ScheduleSpec) -> None:
        """Invoke the callback once and update the spec's bookkeeping."""
        spec.runs += 1
        spec.last_run_at = utcnow()
        try:
            result = await self._callback(spec)
        except Exception as exc:  # a job failure must not kill the loop
            spec.last_error = str(exc)
            logger.error("schedule_fire_error", schedule=spec.id, error=str(exc))
            return
        if result is None:
            spec.last_error = "blueprint not found"
            return
        spec.last_status = result.status
        spec.last_error = result.error
