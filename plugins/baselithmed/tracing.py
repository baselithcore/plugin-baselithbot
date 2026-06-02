"""OpenTelemetry tracing helpers for the BaselithMed plugin.

Exposes one decorator + one context-manager helper backed by the global
OpenTelemetry tracer. When OTel is not installed (lightweight test
environments), the helpers degrade to no-ops so the call sites can stay
unconditional.

The tracer is named ``baselithmed`` so exporters can filter spans by
plugin without inspecting per-span attributes.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

_TRACER: Any | None
_Status: Any | None
_StatusCode: Any | None
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode

    _TRACER = trace.get_tracer("baselithmed")
    _Status = Status
    _StatusCode = StatusCode
    _OTEL_AVAILABLE = True
except Exception:  # noqa: BLE001 — degrade gracefully
    _TRACER = None
    _Status = None
    _StatusCode = None
    _OTEL_AVAILABLE = False


@contextmanager
def clinical_span(name: str, **attributes: Any) -> Iterator[Any]:
    """Open a span named ``name`` with the supplied attributes.

    Attributes are coerced to strings on the way in so callers don't need
    to worry about OTel's strict attribute typing.
    """
    if not _OTEL_AVAILABLE or _TRACER is None:
        yield None
        return
    with _TRACER.start_as_current_span(name) as span:
        for key, value in attributes.items():
            try:
                if isinstance(value, (bool, int, float, str)) or value is None:
                    span.set_attribute(key, value if value is not None else "")
                else:
                    span.set_attribute(key, str(value))
            except Exception:  # noqa: BLE001 — never break the span
                continue
        try:
            yield span
        except Exception as exc:  # noqa: BLE001
            try:
                span.record_exception(exc)
                if _Status is not None and _StatusCode is not None:
                    span.set_status(_Status(_StatusCode.ERROR, str(exc)))
            except Exception:  # noqa: BLE001
                pass
            raise


def is_tracing_enabled() -> bool:
    """``True`` when the OpenTelemetry SDK is importable and a tracer ready."""
    return _OTEL_AVAILABLE
