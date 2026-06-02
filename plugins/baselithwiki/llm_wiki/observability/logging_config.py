"""Structured JSON logging con tenant_id e request_id sempre presenti.

JSON-line format compatibile con aggregatori (Loki, ELK, Datadog).

Abilitazione via env:
    LOG_FORMAT=json    # default in deploy con observability stack
    LOG_FORMAT=text    # human-friendly (dev)
    LOG_LEVEL_CONSOLE=INFO|DEBUG|WARNING|ERROR
    LOG_LEVEL_FILE=INFO

Pattern porting da ``agent-jira/app/logging_config.py`` adattato al
``tenant_context`` di llm-wiki.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_wiki.observability.request_id import (
    RequestIdFilter,
    SensitiveDataFilter,
    request_id_ctx,
)


class JsonFormatter(logging.Formatter):
    """Una riga JSON per record. Chiavi stabili per parsing."""

    _STANDARD_ATTRS = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "getMessage",
        "message",
        "asctime",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }
        payload["request_id"] = (
            getattr(record, "request_id", None) or _safe_request_id()
        )
        payload["tenant_id"] = getattr(record, "tenant_id", None) or _safe_tenant_id()

        if record.exc_info:
            exc_type, exc_val, exc_tb = record.exc_info
            payload["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_val) if exc_val else None,
                "traceback": "".join(
                    traceback.format_exception(exc_type, exc_val, exc_tb)
                ),
            }

        for key, value in record.__dict__.items():
            if key in self._STANDARD_ATTRS or key.startswith("_"):
                continue
            if key in payload:
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)

        try:
            return json.dumps(payload, ensure_ascii=False, default=str)
        except Exception:
            return json.dumps(
                {
                    "timestamp": payload["timestamp"],
                    "level": payload["level"],
                    "logger": payload["logger"],
                    "message": str(record.getMessage()),
                }
            )


def _safe_request_id() -> str:
    try:
        return request_id_ctx.get("-") or "-"
    except Exception:
        return "-"


def _safe_tenant_id() -> str:
    try:
        from llm_wiki.auth.tenant_context import get_current_tenant_id

        return get_current_tenant_id() or "-"
    except Exception:
        return "-"


class TenantContextFilter(logging.Filter):
    """Inietta ``tenant_id`` su ogni record dal contextvar."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        if not hasattr(record, "tenant_id"):
            record.tenant_id = _safe_tenant_id()
        return True


def configure_logging(
    *,
    level_console: str | int = "INFO",
    level_file: str | int = "INFO",
    log_format: str | None = None,
    log_dir: str | Path = "logs",
    log_filename: str = "app.log",
) -> None:
    """Configura root logger idempotente.

    - Reset handlers (Uvicorn pre-installa propri sul root).
    - Console handler (stdout) + file handler (logs/app.log).
    - JSON o testo a seconda di ``log_format`` o env ``LOG_FORMAT``.
    - Redirige logger ``uvicorn.*`` sul root per uniformare il formato.

    Sicuro chiamare più volte (test, reload). Skipping file handler
    se la directory non è scrivibile (es. CI ephemeral, container ro).
    """
    root_logger = logging.getLogger()
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    fmt_mode = (log_format or os.getenv("LOG_FORMAT", "text") or "text").strip().lower()

    def _to_level(value: str | int) -> int:
        if isinstance(value, int):
            return value
        return getattr(logging, str(value).upper(), logging.INFO)

    lvl_console = _to_level(level_console)
    lvl_file = _to_level(level_file)
    root_logger.setLevel(min(lvl_console, lvl_file))

    if fmt_mode == "json":
        formatter: logging.Formatter = JsonFormatter()
        tenant_filter: logging.Filter | None = TenantContextFilter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s"
        )
        tenant_filter = None

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(lvl_console)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIdFilter())
    console_handler.addFilter(SensitiveDataFilter())
    if tenant_filter is not None:
        console_handler.addFilter(tenant_filter)
    root_logger.addHandler(console_handler)

    try:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path / log_filename)
        file_handler.setLevel(lvl_file)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIdFilter())
        file_handler.addFilter(SensitiveDataFilter())
        if tenant_filter is not None:
            file_handler.addFilter(tenant_filter)
        root_logger.addHandler(file_handler)
    except OSError:
        # ro filesystem o permessi: console-only è accettabile.
        pass

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        for h in list(lg.handlers):
            lg.removeHandler(h)
        lg.propagate = True
        lg.setLevel(lvl_console)


__all__ = [
    "JsonFormatter",
    "TenantContextFilter",
    "configure_logging",
]
