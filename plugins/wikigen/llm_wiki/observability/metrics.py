"""Definizioni Prometheus metrics per il wiki engine.

Prefisso ``wiki_`` (allineato all'identità di prodotto). I record vivono
nel registry di processo di ``prometheus_client``; nessuna I/O sincrona —
solo strutture in memoria. Senza ``prometheus_client`` installato il modulo
fornisce stub no-op (gli increment / observe non sollevano).

Cardinalità label
=================

- ``tenant_id`` cresce linearmente col numero di workspace; per fleet
  con > 10k tenant attivi ridurre a ``tenant_plan`` o aggregati.
- ``route`` deve essere il *template* (``/api/wiki/{slug}``), non il path
  espanso, altrimenti high-cardinality. FastAPIInstrumentor gestisce ok.
"""

from __future__ import annotations

try:  # pragma: no cover - fallback se prometheus-client non installato
    from prometheus_client import Counter, Gauge, Histogram

    _PROM_AVAILABLE = True
except Exception:  # pragma: no cover

    class _NoopMetric:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def dec(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

    Counter = Gauge = Histogram = _NoopMetric  # type: ignore[misc,assignment]
    _PROM_AVAILABLE = False


# Buckets latenza con risoluzione fine sotto 1s (HTTP) e fino a 60s
# (LLM/ingest). Allineato a agent-jira.
LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
    15.0,
    20.0,
    30.0,
    45.0,
    60.0,
    float("inf"),
)


# === HTTP / Chat ===
CHAT_REQUESTS_TOTAL = Counter(
    "wiki_chat_requests_total",
    "Conteggio richieste chat / RAG.",
    ["route"],
)
CHAT_REQUEST_LATENCY_SECONDS = Histogram(
    "wiki_chat_request_latency_seconds",
    "Latenza richieste chat / RAG.",
    ["route"],
    buckets=LATENCY_BUCKETS,
)
CHAT_REQUEST_ERRORS_TOTAL = Counter(
    "wiki_chat_request_errors_total",
    "Conteggio richieste chat fallite.",
    ["route", "reason"],
)
CHAT_TTFB_SECONDS = Histogram(
    "wiki_chat_ttfb_seconds",
    "Time-to-first-byte streaming chat (primo chunk al client).",
    ["route"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf")),
)


# === LLM ===
LLM_CALLS_TOTAL = Counter(
    "wiki_llm_calls_total",
    "Conteggio chiamate LLM con esito.",
    ["provider", "model", "mode", "status"],
)
LLM_CALL_LATENCY_SECONDS = Histogram(
    "wiki_llm_call_latency_seconds",
    "Latenza chiamata LLM (tempo totale di generazione).",
    ["provider", "model", "mode"],
    buckets=LATENCY_BUCKETS,
)
LLM_TTFB_SECONDS = Histogram(
    "wiki_llm_ttfb_seconds",
    "Time-to-first-token streaming LLM.",
    ["provider", "model"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf")),
)
LLM_TOKENS_TOTAL = Counter(
    "wiki_llm_tokens_total",
    "Token consumati per provider / model / tipo (prompt|completion).",
    ["provider", "model", "type"],
)


# === Retrieval / Rerank ===
RETRIEVAL_LATENCY_SECONDS = Histogram(
    "wiki_retrieval_latency_seconds",
    "Latenza ricerche Qdrant (dense + hybrid prefetch).",
    buckets=LATENCY_BUCKETS,
)
RERANK_REQUESTS_TOTAL = Counter(
    "wiki_rerank_requests_total",
    "Numero richieste di rerank.",
)
RERANK_LATENCY_SECONDS = Histogram(
    "wiki_rerank_latency_seconds",
    "Latenza CrossEncoder reranker.",
    buckets=LATENCY_BUCKETS,
)
RERANK_CACHE_HIT_TOTAL = Counter(
    "wiki_rerank_cache_hit_total",
    "Hit cache rerank.",
)
RERANK_CACHE_MISS_TOTAL = Counter(
    "wiki_rerank_cache_miss_total",
    "Miss cache rerank.",
)


# === Ingest pipeline (PDF → wiki) ===
INGEST_RUNS_TOTAL = Counter(
    "wiki_ingest_runs_total",
    "Numero esecuzioni pipeline ingest.",
    ["mode"],
)
INGEST_DURATION_SECONDS = Histogram(
    "wiki_ingest_duration_seconds",
    "Durata totale di una pipeline ingest.",
    ["mode"],
)
INGEST_STAGE_DURATION_SECONDS = Histogram(
    "wiki_ingest_stage_duration_seconds",
    "Durata singole fasi ingest (extract|classify|plan|generate|lint|critic|write).",
    ["stage"],
    buckets=LATENCY_BUCKETS,
)
INGEST_FAILURES_TOTAL = Counter(
    "wiki_ingest_failures_total",
    "Fallimenti per fase pipeline ingest.",
    ["stage", "reason"],
)
INDEXED_DOCUMENTS_TOTAL = Counter(
    "wiki_indexed_documents_total",
    "Numero documenti indicizzati cumulativamente.",
)
INDEXED_DOCUMENTS_GAUGE = Gauge(
    "wiki_indexed_documents_current",
    "Documenti correntemente disponibili nella collection.",
)


# === Agent / SLO ===
AGENT_STEP_LATENCY_SECONDS = Histogram(
    "wiki_agent_step_latency_seconds",
    "Latenza step dell'agente RAG (retrieval, rerank, synthesis).",
    ["step_name", "agent_type"],
    buckets=LATENCY_BUCKETS,
)
AGENT_FAILURE_TOTAL = Counter(
    "wiki_agent_failure_total",
    "Fallimenti dell'agente RAG.",
    ["agent_type", "failure_type"],
)
SLO_VIOLATIONS_TOTAL = Counter(
    "wiki_slo_violations_total",
    "Richieste oltre la soglia SLO.",
    ["route", "slo_type"],
)


# === Feedback ===
FEEDBACK_RECEIVED_TOTAL = Counter(
    "wiki_feedback_total",
    "Feedback ricevuti suddivisi per sentiment.",
    ["sentiment"],
)


# === Per-tenant ===
TENANT_HTTP_REQUESTS_TOTAL = Counter(
    "wiki_tenant_http_requests_total",
    "HTTP requests partizionate per tenant, route e status bucket.",
    ["tenant_id", "method", "route", "status_bucket"],
)
TENANT_HTTP_ERRORS_TOTAL = Counter(
    "wiki_tenant_http_errors_total",
    "HTTP errors (4xx/5xx) per tenant, route e status code.",
    ["tenant_id", "route", "status"],
)
TENANT_HTTP_LATENCY_SECONDS = Histogram(
    "wiki_tenant_http_latency_seconds",
    "Latenza HTTP requests per tenant e route.",
    ["tenant_id", "route"],
    buckets=LATENCY_BUCKETS,
)


# === Health gauges (aggiornate da /health/ready) ===
POSTGRES_UP = Gauge(
    "wiki_postgres_up",
    "1 se Postgres risponde a SELECT 1, 0 altrimenti.",
)
QDRANT_UP = Gauge(
    "wiki_qdrant_up",
    "1 se Qdrant risponde con la collection attesa, 0 altrimenti.",
)
GRAPHDB_UP = Gauge(
    "wiki_graphdb_up",
    "1 se FalkorDB risponde al PING, 0 altrimenti.",
)
LLM_PROVIDER_UP = Gauge(
    "wiki_llm_provider_up",
    "1 se il provider LLM (Ollama/OpenAI) risponde all'healthcheck.",
)


# === Tenancy registry ===
TENANTS_REGISTERED_TOTAL = Gauge(
    "wiki_tenants_registered_total",
    "Numero tenant registrati nel database (snapshot).",
)


__all__ = [
    "LATENCY_BUCKETS",
    "CHAT_REQUESTS_TOTAL",
    "CHAT_REQUEST_LATENCY_SECONDS",
    "CHAT_REQUEST_ERRORS_TOTAL",
    "CHAT_TTFB_SECONDS",
    "LLM_CALLS_TOTAL",
    "LLM_CALL_LATENCY_SECONDS",
    "LLM_TTFB_SECONDS",
    "LLM_TOKENS_TOTAL",
    "RETRIEVAL_LATENCY_SECONDS",
    "RERANK_REQUESTS_TOTAL",
    "RERANK_LATENCY_SECONDS",
    "RERANK_CACHE_HIT_TOTAL",
    "RERANK_CACHE_MISS_TOTAL",
    "INGEST_RUNS_TOTAL",
    "INGEST_DURATION_SECONDS",
    "INGEST_STAGE_DURATION_SECONDS",
    "INGEST_FAILURES_TOTAL",
    "INDEXED_DOCUMENTS_TOTAL",
    "INDEXED_DOCUMENTS_GAUGE",
    "AGENT_STEP_LATENCY_SECONDS",
    "AGENT_FAILURE_TOTAL",
    "SLO_VIOLATIONS_TOTAL",
    "FEEDBACK_RECEIVED_TOTAL",
    "TENANT_HTTP_REQUESTS_TOTAL",
    "TENANT_HTTP_ERRORS_TOTAL",
    "TENANT_HTTP_LATENCY_SECONDS",
    "POSTGRES_UP",
    "QDRANT_UP",
    "GRAPHDB_UP",
    "LLM_PROVIDER_UP",
    "TENANTS_REGISTERED_TOTAL",
]
