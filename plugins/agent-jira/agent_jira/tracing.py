"""
OpenTelemetry setup opt-in (Sprint 10).

Attivazione via env:
  OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
  OTEL_SERVICE_NAME=agent-jira
  OTEL_RESOURCE_ATTRIBUTES="deployment.environment=prod"

Se la variabile non è impostata, l'init è no-op e l'app funziona invariata.
Le dipendenze `opentelemetry-*` sono optional extras.

Instrumentazione automatica:
  - FastAPI (request → span)
  - Httpx (chiamate Jira/Ollama)
  - Psycopg (query Postgres)
  - Redis (cache + queue future)

Ogni span è arricchito con attributi `tenant.id` e `request.id` dal contextvar.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_initialized = False


def setup_tracing(app) -> None:
    """
    Inizializza OpenTelemetry se OTEL_EXPORTER_OTLP_ENDPOINT è configurato.
    Chiamare una volta al boot passando l'istanza FastAPI.
    """
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
            "OpenTelemetry package mancanti (%s). Installa con:\n"
            "  pip install opentelemetry-distro opentelemetry-exporter-otlp \\\n"
            "    opentelemetry-instrumentation-fastapi \\\n"
            "    opentelemetry-instrumentation-httpx \\\n"
            "    opentelemetry-instrumentation-psycopg \\\n"
            "    opentelemetry-instrumentation-redis",
            exc,
        )
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "agent-jira")
    resource = Resource.create(
        {"service.name": service_name, **_parse_resource_attrs()}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)

    # Instrumentazioni
    FastAPIInstrumentor.instrument_app(
        app,
        server_request_hook=_enrich_span_with_tenant,
    )
    HTTPXClientInstrumentor().instrument()

    # Psycopg e Redis sono opzionali (solo se i package sono installati).
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


def _enrich_span_with_tenant(span, scope):
    """Aggiunge tenant_id e request_id allo span server-side."""
    try:
        from agent_jira.tenant_context import get_current_tenant_id

        tid = get_current_tenant_id()
        if tid:
            span.set_attribute("tenant.id", tid)
    except Exception:
        pass
    try:
        from backend import request_id_ctx

        rid = request_id_ctx.get("-")
        if rid and rid != "-":
            span.set_attribute("request.id", rid)
    except Exception:
        pass
