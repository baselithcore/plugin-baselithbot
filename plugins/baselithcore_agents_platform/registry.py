"""In-process store for blueprints and run history.

A deliberately small, async-safe registry. Persistence is intentionally out of
scope for v1: blueprints are cheap to regenerate and run history is advisory.
The interface is storage-shaped, so a Postgres-backed implementation can drop in
behind it later without touching callers.
"""

from __future__ import annotations

import asyncio
from collections import deque

from .types import AgentBlueprint, AgentRunResult

__all__ = ["AgentRegistry"]


class AgentRegistry:
    """Thread/async-safe in-memory registry of blueprints and recent runs.

    Args:
        max_runs: Ring-buffer capacity for retained run results.
    """

    def __init__(self, max_runs: int = 200) -> None:
        self._blueprints: dict[str, AgentBlueprint] = {}
        self._runs: deque[AgentRunResult] = deque(maxlen=max_runs)
        self._lock = asyncio.Lock()

    async def save_blueprint(self, blueprint: AgentBlueprint) -> AgentBlueprint:
        """Insert or replace a blueprint by id."""
        async with self._lock:
            self._blueprints[blueprint.id] = blueprint
            return blueprint

    async def get_blueprint(self, blueprint_id: str) -> AgentBlueprint | None:
        """Return a blueprint by id, or None when absent."""
        async with self._lock:
            return self._blueprints.get(blueprint_id)

    async def list_blueprints(self) -> list[AgentBlueprint]:
        """Return all blueprints, most recently created first."""
        async with self._lock:
            return sorted(
                self._blueprints.values(),
                key=lambda b: b.created_at,
                reverse=True,
            )

    async def delete_blueprint(self, blueprint_id: str) -> bool:
        """Remove a blueprint; return True if it existed."""
        async with self._lock:
            return self._blueprints.pop(blueprint_id, None) is not None

    async def record_run(self, run: AgentRunResult) -> AgentRunResult:
        """Append a run result to the bounded history buffer."""
        async with self._lock:
            self._runs.append(run)
            return run

    async def list_runs(self, blueprint_id: str | None = None) -> list[AgentRunResult]:
        """Return recent runs, newest first, optionally filtered by blueprint."""
        async with self._lock:
            runs = list(self._runs)
        runs.reverse()
        if blueprint_id is None:
            return runs
        return [r for r in runs if r.blueprint_id == blueprint_id]
