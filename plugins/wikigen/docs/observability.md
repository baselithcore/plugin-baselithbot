# Observability

Stack: **Prometheus + Grafana + Loki + Tempo + OpenTelemetry**. Tutto opt-in, deployabile come compose separato indipendente dall'app principale.

## Architettura

```text
                ┌────────────── App (uvicorn :8000) ──────────────┐
                │                                                   │
                │  /metrics  (prometheus_client)                   │
                │  stdout JSON logs (LOG_FORMAT=json)              │
                │  OTLP traces (OTEL_EXPORTER_OTLP_ENDPOINT)       │
                └───────┬───────────────┬──────────────────┬───────┘
                        │               │                  │
                ┌───────▼──────┐ ┌──────▼─────┐  ┌─────────▼────────┐
                │  Prometheus  │ │  Promtail  │  │  OTel Collector  │
                │   (scrape)   │ │ (file/dock)│  │   (OTLP recv)    │
                └───────┬──────┘ └─────┬──────┘  └────┬─────────┬───┘
                        │              │              │         │
                ┌───────▼──────────────▼──────────────▼────┐    │
                │              Loki   /   Tempo            │    │ exporters
                │  (logs)            (traces)              │    │ → Prometheus :8889
                └───────────────────────┬──────────────────┘    │
                                        │                       │
                                ┌───────▼───────┐               │
                                │    Grafana    │◀──────────────┘
                                │   :3000 UI    │  (datasources)
                                └───────────────┘
                                        │
                                ┌───────▼───────┐
                                │ AlertManager  │  (Slack, email)
                                └───────────────┘
```

## Avvio stack osservabilità

```bash
cd deploy/observability
./bootstrap.sh                # genera secret Grafana, dirs, perms
docker compose up -d
```

Servizi:

| Servizio | Image | Porta host | Scopo |
|----------|-------|-----------|-------|
| prometheus | `prom/prometheus:v2.55.1` | 127.0.0.1:9090 | Metrics TSDB; scrape `/metrics` |
| grafana | `grafana/grafana:11.3.1` | 0.0.0.0:3000 | UI + alert |
| loki | `grafana/loki:3.2.1` | 127.0.0.1:3100 | Log aggregation |
| tempo | `grafana/tempo:2.6.1` | 127.0.0.1:3200 | Trace store |
| otel-collector | `otel/opentelemetry-collector-contrib:0.113.0` | 4317 (gRPC), 4318 (HTTP), 8889 (Prom) | OTLP ingress |
| promtail | `grafana/promtail:3.2.1` | — | Log shipper |
| alertmanager | `prom/alertmanager:v0.27.0` | 127.0.0.1:9093 | Alert routing |
| node-exporter | `prom/node-exporter:v1.8.2` | — | Host metrics |

> Login Grafana iniziale: `admin / <pwd in .env generato da bootstrap.sh>`. Cambiala al primo accesso.

## Configurazione lato app

In `.env` dell'app:

```ini
# Logging strutturato JSON per Promtail
LOG_FORMAT=json
LOG_LEVEL_CONSOLE=INFO

# OpenTelemetry (opzionale)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=llm-wiki
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=prod,service.version=0.1.0

# Prometheus endpoint
PROMETHEUS_METRICS_ENABLED=true
```

Installa l'extra `obs`:

```bash
pip install -e ".[obs]"
```

→ aggiunge OpenTelemetry SDK + auto-instrumentations (FastAPI, httpx, psycopg, redis).

## Metriche esposte

Endpoint: `GET /metrics` (formato Prometheus text).

### Counter

| Metric | Labels | Significato |
|--------|--------|-------------|
| `wiki_events_total` | `name` | Eventi domain (`ingest_started`, `ingest_done`, `chat_turn`, `auth.login`, ecc.) |
| `http_requests_total` | `method`, `path`, `status` | Conteggio richieste |
| `token_refresh_total` | `success` | Refresh JWT (true/false) |
| `rate_limit_hit_total` | `endpoint`, `limit_type` | Violazioni rate-limit |
| `pg_rls_violations_total` | — | Tentativi cross-tenant bloccati |

### Histogram

| Metric | Labels | Significato |
|--------|--------|-------------|
| `http_request_duration_seconds` | `method`, `path`, `status` | Latenza richiesta |
| `rag_retrieval_latency_seconds` | `pack_name`, `method` | Tempo retrieve+rerank |
| `ingest_stage_duration_seconds` | `stage` (extract/classify/plan/generate/lint/critic) | Tempo per stage pipeline |
| `pg_query_duration_seconds` | `operation` | Query DB |

### Gauge

| Metric | Labels | Significato |
|--------|--------|-------------|
| `ingest_jobs_in_flight` | — | Job ingest attivi |
| `pg_pool_connections` | `state` (idle/active/waiting) | Stato pool psycopg |
| `qdrant_collection_points` | `collection` | Documenti indicizzati |

Esempio scrape Prometheus (`prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'llm-wiki'
    scrape_interval: 15s
    static_configs:
      - targets: ['host.docker.internal:8000']  # se app sull'host
```

## Logging

### Formato JSON

Con `LOG_FORMAT=json` ogni record è una riga JSON:

```json
{
  "timestamp": "2026-05-02T20:14:31.123Z",
  "level": "INFO",
  "logger": "llm_wiki.api.routers.chat",
  "message": "chat turn completed",
  "request_id": "01HXY...",
  "trace_id": "4bf92f3577b34da6...",
  "span_id": "00f067aa0ba902b7",
  "user_id": "uuid...",
  "tenant_id": "uuid...",
  "extra": {"latency_ms": 412, "sources_count": 5}
}
```

Promtail lo ingesta con label automatici (`container_name`, `level`, `request_id`).

### Correlazione log↔trace↔metric

`request_id` (header `X-Request-ID`, generato dal middleware `request_id.py` se assente) propaga lungo:

- log: campo `request_id`
- trace: span attribute
- metric: exemplar (se OTLP histogram)

In Grafana → click su una latenza alta in una histogram → ti porta direttamente al trace su Tempo → da lì pivot ai log su Loki.

### Filtri sensibili

Logger config maschera automaticamente:

- `password`, `token`, `secret_key`, `api_key`, `Authorization` → `***REDACTED***`

## Tracing (OpenTelemetry)

Auto-instrumentations attivate (extra `obs`):

- `opentelemetry-instrumentation-fastapi` — span per request
- `opentelemetry-instrumentation-httpx` — chiamate LLM (Ollama/OpenAI)
- `opentelemetry-instrumentation-psycopg` — query DB
- `opentelemetry-instrumentation-redis` — rate-limit ops

Span manuali in codice (es. RAG):

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("rag.retrieve") as span:
    span.set_attribute("top_k", top_k)
    span.set_attribute("hybrid", True)
    hits = await search(query)
    span.set_attribute("hits.count", len(hits))
```

Sampling default: `parentbased_traceidratio` con ratio 0.1 (10%). Override:

```ini
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1
```

## Dashboard Grafana

Auto-provisioned in `deploy/observability/grafana/provisioning/dashboards/`:

| Dashboard | Cosa monitora |
|-----------|---------------|
| **System Overview** | CPU, RAM, disk, rete (node-exporter) |
| **App Metrics** | RPS, p50/p95/p99 latency, error rate, status code distribution |
| **Ingest Pipeline** | Job queue, throughput, duration per stage, failure rate |
| **RAG Performance** | Retrieval latency, rerank score histogram, generation time, tokens/s |
| **Auth & Security** | Login rate, rate-limit hits, audit event volume, refresh anomalies |
| **Database** | Pool utilization, query latency, RLS violations, slow queries |
| **Logs Explorer** | Loki queries con saved view per livello/servizio |
| **Traces Explorer** | Tempo search per service.name + duration |

## Alerting

Regole in `prometheus/alerts.yml`:

| Alert | Condizione | Severità |
|-------|------------|----------|
| `HighErrorRate` | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05` | warning |
| `HighLatency` | p95 > 1s per 5m | warning |
| `IngestJobFailureSpike` | `rate(wiki_events_total{name="ingest_failed"}[10m]) > 0.1` | warning |
| `AuthBruteForce` | `rate(rate_limit_hit_total{endpoint="login"}[5m]) > 0.5` | critical |
| `RLSViolation` | `increase(pg_rls_violations_total[1m]) > 0` | critical |
| `DBPoolExhausted` | `pg_pool_connections{state="waiting"} > 0` per 2m | warning |
| `QdrantDown` | `up{job="qdrant"} == 0` per 1m | critical |
| `DiskFillingFast` | proiezione full < 7d | warning |

Routing in `alertmanager/alertmanager.yml`:

```yaml
route:
  receiver: default
  group_by: [alertname, severity]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - matchers: [severity="critical"]
      receiver: pagerduty
      continue: false

receivers:
  - name: default
    slack_configs:
      - api_url: ${SLACK_WEBHOOK_URL}
        channel: '#alerts-llm-wiki'
  - name: pagerduty
    pagerduty_configs:
      - service_key: ${PAGERDUTY_KEY}
```

## SLO suggeriti

| Indicatore | Target |
|-----------|--------|
| Disponibilità API | 99.5% mensile |
| p95 latenza chat (no streaming) | < 3s |
| p95 latenza retrieval | < 500ms |
| Job ingest success rate | > 95% |
| RLS violations | 0 |

Burn rate alert (Prometheus):

```promql
(1 - (rate(http_requests_total{status!~"5.."}[1h]) / rate(http_requests_total[1h]))) > (1-0.995) * 14.4
```

## Retention

| Dato | Default | Override |
|------|---------|----------|
| Prometheus TSDB | 30 giorni | `--storage.tsdb.retention.time=` |
| Loki | 72 ore | `loki-config.yml` `retention_period` |
| Tempo | 48 ore | `tempo-config.yml` `block_retention` |
| App audit_events | 90 giorni | Job cleanup (vedi `operations.md`) |
| Grafana dashboards | persistenti | `grafana_data` volume |

## Troubleshooting osservabilità

| Sintomo | Diagnosi | Azione |
|---------|----------|--------|
| `/metrics` 404 | `PROMETHEUS_METRICS_ENABLED=false` | Settare `true` + restart |
| Niente trace su Tempo | OTLP endpoint sbagliato | `curl http://localhost:4318/v1/traces` deve dare 405 (non 404) |
| Log non in Loki | Promtail non vede stdout container | Verifica volume `/var/lib/docker/containers` montato |
| Grafana non carica datasource | provisioning bug | `docker compose logs grafana \| grep -i provisioning` |
| AlertManager silente | Webhook scaduto | `docker compose exec alertmanager wget -qO- localhost:9093/api/v2/alerts` |
| Cardinalità Prometheus esplosa | Label dinamiche (`path` con id) | Normalize path in middleware (`/users/123` → `/users/:id`) |

## Footprint risorse

Stack pieno (single host dev):

| Servizio | RAM tipica | Disco/giorno |
|----------|-----------|--------------|
| prometheus | 500MB | 200MB |
| loki | 300MB | 500MB |
| tempo | 250MB | 1GB |
| grafana | 200MB | 50MB |
| otel-collector | 100MB | — |
| promtail | 50MB | — |
| alertmanager | 50MB | 10MB |
| node-exporter | 30MB | — |

Tot: ~1.5GB RAM + 2GB/giorno disk. Ridurre retention prima di scalare.
