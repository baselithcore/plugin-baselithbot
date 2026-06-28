"""In-memory ring buffer of application logs for the live log viewer.

structlog renders through stdlib ``logging`` (the core config uses
``structlog.stdlib.LoggerFactory`` + a root ``StreamHandler``), so a plain
:class:`logging.Handler` attached to the **root** logger captures every record —
core, plugins, and uvicorn alike — without touching ``core/``. The handler keeps
a bounded, thread-safe ring and serves a newest-first tail with level / plugin /
text filters.

Logs can carry sensitive detail, so the route that exposes this is admin-gated
(core log-masking still applies upstream). ``emit`` never logs — that would
recurse through this very handler.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Any

from ..config import ControlConfig

# Numeric order for the "minimum level" filter (include this level and above).
_LEVEL_ORDER: dict[str, int] = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


def plugin_of(logger_name: str) -> str:
    """Attribute a logger name to a plugin/subsystem (``plugins.auth.x`` → auth)."""
    parts = logger_name.split(".")
    if parts[0] == "plugins" and len(parts) > 1:
        return parts[1]
    if parts[0] == "core":
        return "core"
    return parts[0] or "root"


class LogRingHandler(logging.Handler):
    """A root-attached log handler retaining recent records in a bounded ring."""

    def __init__(self, capacity: int) -> None:
        super().__init__(level=logging.NOTSET)
        self._ring: deque[dict[str, Any]] = deque(maxlen=max(1, capacity))
        self._lock = threading.Lock()
        self._seq = 0

    def emit(self, record: logging.LogRecord) -> None:
        """Capture one record. Best-effort; never raises, never logs."""
        try:
            message = record.getMessage()
            if len(message) > 2000:
                message = message[:2000] + "…"
            entry = {
                "timestamp": round(record.created, 3),
                "level": record.levelname,
                "logger": record.name,
                "plugin": plugin_of(record.name),
                "message": message,
            }
            with self._lock:
                self._seq += 1
                entry["seq"] = self._seq
                self._ring.append(entry)
        except Exception:  # noqa: BLE001 — logging must never break the app
            pass

    def tail(
        self,
        *,
        limit: int = 200,
        level: str | None = None,
        plugin: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return up to ``limit`` matching records, newest first."""
        with self._lock:
            items = list(self._ring)
        threshold = _LEVEL_ORDER.get((level or "").upper())
        if threshold is not None:
            items = [e for e in items if _LEVEL_ORDER.get(e["level"], 0) >= threshold]
        if plugin:
            items = [e for e in items if e["plugin"] == plugin]
        if query:
            q = query.lower()
            items = [
                e
                for e in items
                if q in e["message"].lower() or q in e["logger"].lower()
            ]
        if limit > 0:
            items = items[-limit:]
        return list(reversed(items))

    def known_plugins(self) -> list[str]:
        """Distinct plugin/subsystem facets currently in the ring (sorted)."""
        with self._lock:
            return sorted({e["plugin"] for e in self._ring})

    @property
    def capacity(self) -> int:
        return self._ring.maxlen or 0


_HANDLER: LogRingHandler | None = None
_LOCK = threading.Lock()


def get_log_buffer() -> LogRingHandler:
    """Return the singleton log handler, attaching it to the root logger once."""
    global _HANDLER
    if _HANDLER is None:
        with _LOCK:
            if _HANDLER is None:
                handler = LogRingHandler(ControlConfig().log_buffer_capacity)
                logging.getLogger().addHandler(handler)
                _HANDLER = handler
    return _HANDLER


__all__ = ["LogRingHandler", "get_log_buffer", "plugin_of"]
