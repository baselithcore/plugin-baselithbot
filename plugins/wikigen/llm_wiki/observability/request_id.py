"""Request-ID propagation: contextvar, middleware, logging filters.

Ogni richiesta HTTP riceve un UUID v4 (o riusa ``X-Request-ID`` in ingresso),
salvato in :data:`request_id_ctx` e ri-emesso nell'header di risposta. I
filtri logging arricchiscono ogni record con questo ID e redigono token /
api-key se accidentalmente loggati.

Pattern porting da ``agent-jira/backend.py``.
"""

from __future__ import annotations

import contextvars
import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)

# Hook record factory: ogni LogRecord nasce con `request_id` (anche
# fuori da una request, default "-").
_old_record_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):  # pragma: no cover - logging infra
    record = _old_record_factory(*args, **kwargs)
    if not hasattr(record, "request_id"):
        try:
            record.request_id = request_id_ctx.get("-")
        except Exception:
            record.request_id = "-"
    return record


logging.setLogRecordFactory(_record_factory)


class RequestIdFilter(logging.Filter):
    """Inietta ``request_id`` su ogni record dal contextvar."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        record.request_id = request_id_ctx.get("-")
        return True


class SensitiveDataFilter(logging.Filter):
    """Redige token / api-key se accidentalmente presenti nei log.

    Non fa parsing completo: copre i marker più comuni in messaggi
    formattati (``"Authorization: Bearer ..."``, ``"api_key=..."``).
    """

    MARKERS = ("authorization", "api-key", "api_key", "bearer", "token")

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        try:
            msg = str(record.getMessage())
        except Exception:
            return True
        lowered = msg.lower()
        if any(marker in lowered for marker in self.MARKERS):
            for marker in self.MARKERS:
                msg = msg.replace(marker, f"{marker}=[redacted]")
            record.msg = msg
            record.args = ()
        return True


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Genera/propaga ``X-Request-ID``.

    Reuse dell'header in ingresso (utile per tracciare richieste
    end-to-end attraverso un reverse proxy che già lo emette).
    Reset del contextvar in ``finally`` — niente leak fra request
    concorrenti su pool asyncio.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["x-request-id"] = request_id
        return response


__all__ = [
    "request_id_ctx",
    "RequestIdFilter",
    "SensitiveDataFilter",
    "RequestIdMiddleware",
]
