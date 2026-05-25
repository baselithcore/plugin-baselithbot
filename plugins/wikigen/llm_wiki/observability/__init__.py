"""Observability stack: structured logging, request-id propagation,
Prometheus metrics, OpenTelemetry tracing, telemetry counters.

Pattern allineato a ``agent-jira/app/`` (Sprint 10 — Observability):

- :mod:`logging_config` — formatter JSON con tenant_id/request_id
- :mod:`request_id` — middleware UUID + contextvar + filtri
- :mod:`tracing` — setup OTel (opt-in via ``OTEL_EXPORTER_OTLP_ENDPOINT``)
- :mod:`metrics` — Counters / Histograms / Gauges Prometheus (prefisso ``wiki_``)
- :mod:`telemetry` — collector contatori thread-safe (snapshot in /api/status)

L'intero stack è opt-in: senza dipendenze installate o env-var l'app
funziona invariata. Vedi ``deploy/observability/`` per Grafana/Prom/Loki/Tempo.
"""

from __future__ import annotations

from llm_wiki.observability.request_id import (
    RequestIdFilter,
    RequestIdMiddleware,
    SensitiveDataFilter,
    request_id_ctx,
)
from llm_wiki.observability.telemetry import telemetry

__all__ = [
    "RequestIdFilter",
    "RequestIdMiddleware",
    "SensitiveDataFilter",
    "request_id_ctx",
    "telemetry",
]
