"""OpenTelemetry tracing — local file exporter only. No cloud egress."""

from pathlib import Path
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

from .config import settings

_initialized = False


def setup_tracing() -> None:
    """Init OTel with local file/console exporter. Idempotent."""
    global _initialized
    if _initialized:
        return

    resource = Resource.create(
        {
            "service.name": settings.app_name,
            "service.version": settings.version,
            "deployment.environment": "local",
        }
    )
    provider = TracerProvider(resource=resource)

    trace_dir: Path = settings.storage_root / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_file = trace_dir / "spans.jsonl"
    exporter = ConsoleSpanExporter(out=open(trace_file, "a", encoding="utf-8"))  # noqa: SIM115
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer(name: str = "docheck") -> Any:
    return trace.get_tracer(name)
