"""Structured logging configuration for the CLI.

Supports two formats — ``text`` (human-friendly, default) and ``json``
(one record per line, suitable for log aggregators). Idempotent: calling
``configure_logging`` multiple times replaces any handlers installed on
the root logger so the CLI can be imported in tests without leaking
configuration.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per record. Keeps fields stable for parsers."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(*, level: str, fmt: str) -> None:
    """Configure the root logger. ``level`` is case-insensitive."""
    norm = level.upper()
    if norm not in _VALID_LEVELS:
        norm = "INFO"
    fmt_lower = (fmt or "text").lower()
    handler = logging.StreamHandler(stream=sys.stderr)
    if fmt_lower == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    root = logging.getLogger()
    for old in list(root.handlers):
        root.removeHandler(old)
    root.addHandler(handler)
    root.setLevel(getattr(logging, norm))
