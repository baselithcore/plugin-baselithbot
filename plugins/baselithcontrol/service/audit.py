"""Append-only audit trail for lifecycle actions.

A minimal :class:`AuditSink` Protocol with an in-memory ring-buffer default. The
Protocol keeps the storage swappable — a Postgres-backed sink can be dropped in
later (mirroring the BOP persistence pattern) without touching the routers or
the control service.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Protocol, runtime_checkable

from ..api_models import AuditEntryView
from ..config import get_runtime_config


@runtime_checkable
class AuditSink(Protocol):
    """Records governed lifecycle actions; never raises into the caller."""

    async def record(
        self,
        *,
        actor: str,
        plugin: str,
        op: str,
        ok: bool,
        reason: str | None,
    ) -> None: ...

    def tail(self, limit: int = 50) -> list[AuditEntryView]: ...


class InMemoryAuditSink:
    """Bounded in-memory audit log (newest-last ring buffer)."""

    def __init__(self, max_events: int = 500) -> None:
        self._events: deque[AuditEntryView] = deque(maxlen=max(0, max_events) or 1)

    @property
    def capacity(self) -> int:
        """The ring-buffer capacity currently in effect."""
        return self._events.maxlen or 0

    def resize(self, max_events: int) -> None:
        """Change capacity, preserving the newest events."""
        capacity = max(0, max_events) or 1
        if capacity == self.capacity:
            return
        self._events = deque(self._events, maxlen=capacity)

    async def record(
        self,
        *,
        actor: str,
        plugin: str,
        op: str,
        ok: bool,
        reason: str | None,
    ) -> None:
        self._events.append(
            AuditEntryView(
                actor=actor,
                plugin=plugin,
                operation=op,
                ok=ok,
                reason=reason,
                timestamp=time.time(),
            )
        )

    def tail(self, limit: int = 50) -> list[AuditEntryView]:
        items = list(self._events)
        return items[-limit:] if limit > 0 else items


_sink: InMemoryAuditSink | None = None


def get_audit_sink(max_events: int | None = None) -> InMemoryAuditSink:
    """Return the process-wide in-memory audit sink (lazy singleton).

    With no argument the configured ``audit_max_events`` applies; passing an
    explicit capacity resizes the live sink (preserving the newest events), so
    the configured value is honoured no matter which caller constructs the
    singleton first.
    """
    global _sink
    if _sink is None:
        capacity = (
            max_events
            if max_events is not None
            else get_runtime_config().audit_max_events
        )
        _sink = InMemoryAuditSink(max_events=capacity)
    elif max_events is not None:
        _sink.resize(max_events)
    return _sink


__all__ = ["AuditSink", "InMemoryAuditSink", "get_audit_sink"]
