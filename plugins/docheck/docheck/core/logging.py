"""Structured logging setup.

Best practices applied:
- Single pipeline for stdlib + structlog via ``ProcessorFormatter`` so
  uvicorn/sqlalchemy/httpx logs share format, level filtering and
  contextvars (request_id, tenant_id, ...) with application logs.
- Console renderer (colored, human-readable) when ``debug`` is on, JSON
  renderer otherwise. JSON keys: ``timestamp``, ``level``, ``logger``,
  ``event`` + arbitrary structured kwargs.
- ``CallsiteParameterAdder`` adds file/line/function for grep-friendly
  traces, without bloating the message.
- ``contextvars.merge_contextvars`` propagates request-scoped fields
  bound by middleware to every log line in the request.
- Exceptions rendered with ``format_exc_info`` so tracebacks are part of
  the structured payload, not lost on stderr.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_NOISY_LOGGERS = {
    "uvicorn.error": logging.INFO,
    "uvicorn.access": logging.INFO,
    "uvicorn": logging.INFO,
    "httpx": logging.WARNING,
    "httpcore": logging.WARNING,
    "openai": logging.WARNING,
    "sqlalchemy.engine": logging.WARNING,
    "watchfiles": logging.WARNING,
    "asyncio": logging.WARNING,
}


def _shared_processors() -> list[Any]:
    """Processors run for both structlog-native and stdlib log records."""
    callsite = structlog.processors.CallsiteParameterAdder(
        parameters=[
            structlog.processors.CallsiteParameter.FILENAME,
            structlog.processors.CallsiteParameter.LINENO,
            structlog.processors.CallsiteParameter.FUNC_NAME,
        ]
    )
    return [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        callsite,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    shared = _shared_processors()

    if debug and sys.stdout.isatty():
        renderer: Any = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    # Stdlib bridge: route every standard logger record through structlog
    # processors so format and contextvars stay consistent.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name, lvl in _NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(lvl)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger("docheck")
