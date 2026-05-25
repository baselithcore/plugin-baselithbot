"""
Structured JSON logging con tenant_id e request_id sempre presenti.

Sprint 10 — Observability. Sostituisce il formatter testuale di backend.py
con un formatter JSON compatibile con aggregatori (Datadog, ELK, Loki).

Abilitazione:
- LOG_FORMAT=json nell'env (default: json in multi-tenant mode)
- LOG_FORMAT=text per retrocompat

Ogni record include:
  timestamp, level, logger, message, request_id, tenant_id,
  process, thread, module, funcName, lineno, exception (se presente)
"""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """
    Formatter JSON-lines: una riga per record, chiavi stabili per parsing.

    Campi base + eventuali `extra` passati ai log statement vengono merged.
    `request_id` e `tenant_id` sono risolti dinamicamente dal contextvar
    se non presenti nel record.
    """

    # Chiavi standard di LogRecord che non vanno serializzate come custom.
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
        payload: Dict[str, Any] = {
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

        # request_id e tenant_id: preferisci record attr, altrimenti contextvar.
        payload["request_id"] = (
            getattr(record, "request_id", None) or _safe_request_id()
        )
        payload["tenant_id"] = getattr(record, "tenant_id", None) or _safe_tenant_id()

        # Eccezione
        if record.exc_info:
            exc_type, exc_val, exc_tb = record.exc_info
            payload["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_val) if exc_val else None,
                "traceback": "".join(
                    traceback.format_exception(exc_type, exc_val, exc_tb)
                ),
            }

        # Extra fields passati via logger.info("...", extra={"foo": "bar"})
        for key, value in record.__dict__.items():
            if key in self._STANDARD_ATTRS or key.startswith("_"):
                continue
            if key in payload:
                continue
            try:
                json.dumps(value)  # test serializability
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)

        try:
            return json.dumps(payload, ensure_ascii=False, default=str)
        except Exception:
            # Fallback: record minimale se la serializzazione totale fallisce
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
        from backend import request_id_ctx

        return request_id_ctx.get("-") or "-"
    except Exception:
        return "-"


def _safe_tenant_id() -> str:
    try:
        from agent_jira.tenant_context import get_current_tenant_id

        return get_current_tenant_id() or "-"
    except Exception:
        return "-"


class TenantContextFilter(logging.Filter):
    """
    Arricchisce ogni record con tenant_id corrente.
    Da applicare su ogni handler di produzione.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "tenant_id"):
            record.tenant_id = _safe_tenant_id()
        return True
