"""OpenTelemetry setup opt-in.

Attivazione via env::

    OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
    OTEL_SERVICE_NAME=llm-wiki
    OTEL_RESOURCE_ATTRIBUTES="deployment.environment=prod,service.version=0.1.0"

Senza ``OTEL_EXPORTER_OTLP_ENDPOINT`` l'init è no-op. Le dipendenze
``opentelemetry-*`` sono ``[obs]`` extras opzionali.

Instrumentazioni automatiche caricate quando i package sono presenti:
FastAPI, Httpx, Psycopg, Redis. Ogni span server riceve gli attributi
``tenant.id`` e ``request.id`` dal contextvar.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_initialized = False


def setup_tracing(app) -> None:
    """Inizializza OTel se ``OTEL_EXPORTER_OTLP_ENDPOINT`` è configurato."""
    global _initialized
    if _initialized:
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        logger.info("OpenTelemetry disabled (OTEL_EXPORTER_OTLP_ENDPOINT not set)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        logger.warning(
            "OpenTelemetry package mancanti (%s). Installa con:\n  pip install -e '.[obs]'",
            exc,
        )
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "llm-wiki")
    resource = Resource.create(
        {"service.name": service_name, **_parse_resource_attrs()}
    )
    traces_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").strip()
    if not traces_endpoint:
        traces_endpoint = endpoint.rstrip("/") + "/v1/traces"

    provider = TracerProvider(resource=resource)
    # schedule_delay 2s + batch piccolo: span arrivano al collector prima
    # che tail_sampling.decision_wait scada — evita "<root span not yet
    # received>" sui trace HTTP server (root chiude per ultimo).
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=traces_endpoint),
            max_export_batch_size=128,
            schedule_delay_millis=2000,
            export_timeout_millis=10000,
        )
    )
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(
        app,
        server_request_hook=_enrich_span_with_context,
    )
    HTTPXClientInstrumentor().instrument()

    try:
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor

        PsycopgInstrumentor().instrument(enable_commenter=True)
    except ImportError:
        pass
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
    except ImportError:
        pass

    logger.info("OpenTelemetry inizializzato → %s (service=%s)", endpoint, service_name)
    _initialized = True


def _parse_resource_attrs() -> dict:
    raw = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")
    out: dict = {}
    for pair in raw.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k:
                out[k] = v
    return out


def _enrich_span_with_context(span, scope):
    """Aggiunge ``tenant.id`` e ``request.id`` allo span server-side."""
    try:
        from llm_wiki.auth.tenant_context import get_current_tenant_id

        tid = get_current_tenant_id()
        if tid:
            span.set_attribute("tenant.id", tid)
    except Exception:
        pass
    try:
        from llm_wiki.observability.request_id import request_id_ctx

        rid = request_id_ctx.get("-")
        if rid and rid != "-":
            span.set_attribute("request.id", rid)
    except Exception:
        pass


__all__ = ["setup_tracing"]
