"""Session retention policy.

Implements the ``BASELITHMED_RETENTION_DAYS`` knob already declared in
``manifest.yaml``. The policy:

    * Tracks the most-recent activity timestamp per session.
    * On demand, surfaces sessions whose last-activity timestamp is older
      than the configured retention window.
    * Crypto-shreds (drops) all per-session state across every plugin
      store: ``_sessions``, ``_reports``, ``_vitals``, ``_validations``,
      the in-memory symptom graph repository.

Purges are recorded in the audit ledger as ``SESSION_CREATED`` events
with ``actor="system:retention"`` and ``summary={"purged": true}`` so the
durable chain proves data lifecycle compliance even after the underlying
session rows are gone.

The retention runner is **idempotent** and never raises — call sites
(admin endpoint, future cron task) can invoke it without defensive
wrappers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Protocol


class _PluginStores(Protocol):
    _sessions: dict[str, Any]
    _validations: dict[str, Any]
    _reports: dict[str, Any]
    _vitals: dict[str, Any]
    _graph_repo: Any
    _audit: Any


@dataclass
class RetentionPolicy:
    """Per-plugin retention book-keeper."""

    retention_days: int = 30
    _last_activity: dict[str, datetime] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def mark_touched(self, session_id: str, *, now: datetime | None = None) -> None:
        """Record activity on ``session_id`` (idempotent, latest-wins)."""
        ts = now or datetime.now(timezone.utc)
        with self._lock:
            self._last_activity[session_id] = ts

    def last_seen(self, session_id: str) -> datetime | None:
        with self._lock:
            return self._last_activity.get(session_id)

    def expired_sessions(self, *, now: datetime | None = None) -> list[str]:
        """Return session IDs whose last-touched timestamp is past expiry."""
        if self.retention_days <= 0:
            # ``retention_days <= 0`` disables retention (used by tests +
            # by deployments that defer expiry to an external job).
            return []
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(
            days=self.retention_days
        )
        with self._lock:
            return [sid for sid, ts in self._last_activity.items() if ts < cutoff]


@dataclass
class PurgeReport:
    purged_sessions: list[str] = field(default_factory=list)
    skipped_sessions: list[str] = field(default_factory=list)

    @property
    def total_purged(self) -> int:
        return len(self.purged_sessions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "purged_sessions": list(self.purged_sessions),
            "skipped_sessions": list(self.skipped_sessions),
            "total_purged": self.total_purged,
        }


def purge_expired(
    plugin: _PluginStores,
    policy: RetentionPolicy,
    *,
    now: datetime | None = None,
) -> PurgeReport:
    """Remove all per-session state for expired sessions. Idempotent."""
    expired = policy.expired_sessions(now=now)
    report = PurgeReport()
    for session_id in expired:
        try:
            plugin._sessions.pop(session_id, None)
            plugin._validations.pop(session_id, None)
            plugin._reports.pop(session_id, None)
            plugin._vitals.pop(session_id, None)
            graph = getattr(plugin, "_graph_repo", None)
            if graph is not None and hasattr(graph, "clear"):
                graph.clear(session_id)
            policy._last_activity.pop(session_id, None)
            # Audit the purge — the entry itself survives the data drop.
            audit = getattr(plugin, "_audit", None)
            if audit is not None and hasattr(audit, "append"):
                # Import lazily to avoid circular import.
                from .audit import AuditEventType

                audit.append(
                    event_type=AuditEventType.SESSION_CREATED,
                    session_id=session_id,
                    actor="system:retention",
                    payload={"retention_purge": True},
                    summary={"purged": True, "reason": "retention_expired"},
                )
            report.purged_sessions.append(session_id)
        except Exception:  # noqa: BLE001 — retention must never raise
            report.skipped_sessions.append(session_id)
    return report


class RetentionRunner:
    """Background asyncio task driving :func:`purge_expired` periodically.

    The runner is a thin wrapper around ``asyncio.create_task`` plus a
    bounded sleep loop. It is **opt-in**: callers must invoke
    :meth:`start` after the plugin's ``initialize()`` so the task lives on
    the running event loop. A non-positive interval disables the runner
    so unit tests / CLI invocations can construct it without scheduling
    real wake-ups.
    """

    def __init__(
        self,
        plugin: _PluginStores,
        policy: RetentionPolicy,
        *,
        interval_seconds: float = 86400.0,
    ) -> None:
        self._plugin = plugin
        self._policy = policy
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self.last_report: PurgeReport | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.last_report = purge_expired(self._plugin, self._policy)
            except Exception:  # noqa: BLE001 — never let the loop die
                pass
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval)
            except asyncio.TimeoutError:
                continue
            else:
                return

    def start(self) -> None:
        """Schedule the background purge loop. Safe to call twice."""
        if self._interval <= 0 or self.running:
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._loop(), name="baselithmed-retention")

    async def stop(self) -> None:
        """Stop the loop and await task completion."""
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await self._task
        except Exception:  # noqa: BLE001 — shutdown must never raise
            pass
        finally:
            self._task = None
