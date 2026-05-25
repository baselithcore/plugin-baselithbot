from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# buckets per latenze più granulari per SLO
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

# === Chat ===
CHAT_REQUESTS_TOTAL = Counter(
    "chatbot_chat_requests_total",
    "Conteggio delle richieste ricevute dal chatbot.",
    ["route"],
)
CHAT_REQUEST_LATENCY_SECONDS = Histogram(
    "chatbot_chat_request_latency_seconds",
    "Distribuzione della latenza delle richieste del chatbot.",
    ["route"],
    buckets=LATENCY_BUCKETS,
)
CHAT_REQUEST_ERRORS_TOTAL = Counter(
    "chatbot_chat_request_errors_total",
    "Conteggio delle richieste chat fallite.",
    ["route", "reason"],
)

# === Agent SLO & Failures ===
AGENT_STEP_LATENCY_SECONDS = Histogram(
    "chatbot_agent_step_latency_seconds",
    "Latenza dei singoli step dell'agente (retrieval, synthesis, jira_sync).",
    ["step_name", "agent_type"],
    buckets=LATENCY_BUCKETS,
)
AGENT_FAILURE_TOTAL = Counter(
    "chatbot_agent_failure_total",
    "Conteggio fallimenti specifici degli agenti.",
    ["agent_type", "failure_type"],
)
SLO_VIOLATIONS_TOTAL = Counter(
    "chatbot_slo_violations_total",
    "Richieste che superano la soglia di latenza desiderata (SLO).",
    ["route", "slo_type"],
)

# === Rerank ===
RERANK_REQUESTS_TOTAL = Counter(
    "chatbot_rerank_requests_total",
    "Conteggio delle richieste di rerank.",
)
RERANK_LATENCY_SECONDS = Histogram(
    "chatbot_rerank_latency_seconds",
    "Distribuzione della latenza del reranker (CrossEncoder).",
)
RERANK_CACHE_HIT_TOTAL = Counter(
    "chatbot_rerank_cache_hit_total",
    "Conteggio hit cache rerank.",
)
RERANK_CACHE_MISS_TOTAL = Counter(
    "chatbot_rerank_cache_miss_total",
    "Conteggio miss cache rerank.",
)

# === Indexing ===
INDEXING_RUNS_TOTAL = Counter(
    "chatbot_indexing_runs_total",
    "Numero di esecuzioni dell'indicizzazione dei documenti.",
    ["mode"],
)
INDEXING_DURATION_SECONDS = Histogram(
    "chatbot_indexing_duration_seconds",
    "Distribuzione della durata delle indicizzazioni.",
    ["mode"],
)
RETRIEVAL_LATENCY_SECONDS = Histogram(
    "chatbot_retrieval_latency_seconds",
    "Distribuzione della latenza delle ricerche Qdrant.",
)
INDEXED_DOCUMENTS_TOTAL = Counter(
    "chatbot_indexed_documents_total",
    "Numero di documenti indicizzati conteggiati cumulativamente.",
)
INDEXED_DOCUMENTS_GAUGE = Gauge(
    "chatbot_indexed_documents_current",
    "Numero corrente di documenti indicizzati disponibili.",
)

# === Feedback ===
FEEDBACK_RECEIVED_TOTAL = Counter(
    "chatbot_feedback_total",
    "Conteggio dei feedback ricevuti, suddivisi per tipo.",
    ["sentiment"],
)

# === Per-tenant (Sprint 10 — Observability) ===
# La cardinalità del label `tenant_id` cresce linearmente col numero di workspace.
# Per piani SaaS con <10k tenant attivi questa cardinalità è gestibile in Prometheus;
# per volumi maggiori, migrare a label `tenant_plan` + usare metriche aggregate.
TENANT_HTTP_REQUESTS_TOTAL = Counter(
    "chatbot_tenant_http_requests_total",
    "HTTP requests partizionate per tenant, route e status.",
    ["tenant_id", "method", "route", "status_bucket"],
)
TENANT_HTTP_ERRORS_TOTAL = Counter(
    "chatbot_tenant_http_errors_total",
    "HTTP errors (4xx/5xx) partizionate per tenant, route e status code preciso.",
    ["tenant_id", "route", "status"],
)
TENANT_HTTP_LATENCY_SECONDS = Histogram(
    "chatbot_tenant_http_latency_seconds",
    "Latenza richieste HTTP per tenant e route.",
    ["tenant_id", "route"],
    buckets=LATENCY_BUCKETS,
)
TENANT_QUOTA_USAGE = Gauge(
    "chatbot_tenant_quota_usage",
    "Utilizzo quota corrente per tenant, separata per tipo (api_calls, storage_mb, documents).",
    ["tenant_id", "quota_type", "plan"],
)
TENANT_ACTIVE_USERS = Gauge(
    "chatbot_tenant_active_users",
    "Numero di utenti attivi per tenant (sempre 1 nel modello 1:1).",
    ["tenant_id"],
)

# === Backend health gauges (aggiornate da /health/ready) ===
POSTGRES_UP = Gauge(
    "chatbot_postgres_up",
    "1 se Postgres risponde al SELECT 1, 0 altrimenti.",
)
REDIS_UP = Gauge(
    "chatbot_redis_up",
    "1 se Redis risponde al PING, 0 altrimenti.",
)
QDRANT_UP = Gauge(
    "chatbot_qdrant_up",
    "1 se Qdrant risponde, 0 altrimenti.",
)
GRAPHDB_UP = Gauge(
    "chatbot_graphdb_up",
    "1 se FalkorDB risponde al PING, 0 altrimenti.",
)

__all__ = [
    "CHAT_REQUESTS_TOTAL",
    "CHAT_REQUEST_LATENCY_SECONDS",
    "CHAT_REQUEST_ERRORS_TOTAL",
    "AGENT_STEP_LATENCY_SECONDS",
    "AGENT_FAILURE_TOTAL",
    "SLO_VIOLATIONS_TOTAL",
    "RERANK_REQUESTS_TOTAL",
    "RERANK_LATENCY_SECONDS",
    "RERANK_CACHE_HIT_TOTAL",
    "RERANK_CACHE_MISS_TOTAL",
    "INDEXING_RUNS_TOTAL",
    "INDEXING_DURATION_SECONDS",
    "RETRIEVAL_LATENCY_SECONDS",
    "INDEXED_DOCUMENTS_TOTAL",
    "INDEXED_DOCUMENTS_GAUGE",
    "FEEDBACK_RECEIVED_TOTAL",
    "TENANT_HTTP_REQUESTS_TOTAL",
    "TENANT_HTTP_ERRORS_TOTAL",
    "TENANT_HTTP_LATENCY_SECONDS",
    "TENANT_QUOTA_USAGE",
    "TENANT_ACTIVE_USERS",
    "POSTGRES_UP",
    "REDIS_UP",
    "QDRANT_UP",
    "GRAPHDB_UP",
]
