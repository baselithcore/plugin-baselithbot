"""Thread-safe counter collector usato in /api/status.

Fallback: se ``prometheus_client`` non è installato, restituisce solo
snapshot in-process (no Prometheus export). Pattern porting da
``agent-jira/app/telemetry.py``.
"""

from __future__ import annotations

import datetime
import threading
import time
from collections import Counter
from typing import Any

try:  # pragma: no cover
    from prometheus_client import Counter as PrometheusCounter
except Exception:  # pragma: no cover
    PrometheusCounter = None  # type: ignore[assignment,misc]


class TelemetryCollector:
    """Conta eventi (chiave=stringa) con timestamp ultimo update."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Counter[str] = Counter()
        self._last_updated: dict[str, float] = {}
        self._created_at = time.time()
        self._prom_counter = (
            PrometheusCounter(
                "wiki_events_total",
                "Conteggio degli eventi di telemetria del wiki engine.",
                ["name"],
            )
            if PrometheusCounter is not None
            else None
        )

    def increment(self, name: str, *, value: int = 1) -> None:
        if not name or value == 0:
            return
        with self._lock:
            self._counters[name] += value
            self._last_updated[name] = time.time()
        if self._prom_counter is not None and value > 0:
            self._prom_counter.labels(name=name).inc(value)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
            last_updated = {
                key: datetime.datetime.fromtimestamp(ts).isoformat()
                for key, ts in self._last_updated.items()
            }
            created_at = datetime.datetime.fromtimestamp(self._created_at).isoformat()
        return {
            "created_at": created_at,
            "counters": counters,
            "last_updated": last_updated,
        }


telemetry = TelemetryCollector()

__all__ = ["telemetry", "TelemetryCollector"]
