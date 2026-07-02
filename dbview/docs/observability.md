# Observability

dbview ships three pillars in-process — structured logs, traces, and metrics — plus a complete `docker-compose` stack under [deploy/observability/](../deploy/observability/) that mirrors the agent-jira layout (Prometheus, Grafana, Loki, Promtail, Tempo, OTel Collector contrib, Alertmanager, node-exporter).

## Logs

[`nestjs-pino`](https://github.com/iamolegga/nestjs-pino) with a Fastify integration.

- **Format** — controlled by `LOG_FORMAT`. `json` in prod (Promtail-parseable), pretty in dev.
- **Level** — controlled by `LOG_LEVEL`.
- **Request ID** — a Fastify `onRequest` hook reads `X-Request-Id` (or generates a UUID v4), echoes it as a response header, and stashes it in `AsyncLocalStorage`. The pino binding emits `request_id` on every log line.
- **Health and metrics noise** — `/api/health*` and `/api/metrics` are excluded from request logging.

### Redaction list

Pino's `redact` config strips secrets out of any log line:

```
req.headers.authorization
req.headers["x-api-key"]
req.headers.cookie
res.headers["set-cookie"]
connectionString
connectionStringCipher
password
passwordHash
accessToken
refreshToken
clientSecret
apiKey
```

If you add a sensitive field anywhere, add it to the redact list in `apps/api/src/app.module.ts`.

## Tracing — OpenTelemetry

Opt-in. Tracing initializes only if `OTEL_EXPORTER_OTLP_ENDPOINT` is set. Bootstrap order matters: the OTel SDK must load before any instrumented module, so `apps/api/src/observability/otel.ts` is imported as the first statement in `main.ts`.

- **Exporter** — OTLP HTTP, default path `/v1/traces`.
- **Processor** — Batch (queue 2048, batch 128, scheduled delay 2 s).
- **Auto-instrumentations** — `http`, `fastify`, `pg`, `redis`, plus the standard set from `@opentelemetry/auto-instrumentations-node`. `fs` is disabled (noisy).
- **Filtered routes** — `/api/health*` and `/api/metrics` produce no spans.
- **Resource attributes** — `service.name = OTEL_SERVICE_NAME` (default `dbview-api`), `service.version = APP_VERSION`.

The OTel collector configured in `deploy/observability/otel-collector/otel-collector-config.yaml` applies tail-sampling: 100 % of errors, 100 % of spans > 1.5 s, 10 % baseline.

## Metrics — Prometheus

`prom-client` with a shared registry. Exposition at `GET /api/metrics`, admin-only (or `X-API-Key` for the scraper).

### Default metrics

Node and process metrics from `collectDefaultMetrics()`: heap, gc, event loop lag, CPU, file descriptors, etc.

### Custom `dbview_*` metrics

| Metric                                       | Type      | Labels                                       | Purpose                                                                              |
| -------------------------------------------- | --------- | -------------------------------------------- | ------------------------------------------------------------------------------------ |
| `dbview_http_request_latency_seconds`        | Histogram | `method`, `route`, `status_bucket`           | HTTP latency. Buckets up to 30 s.                                                    |
| `dbview_http_request_errors_total`           | Counter   | `method`, `route`, `status_bucket`, `reason` | 4xx/5xx counts with reason tag.                                                      |
| `dbview_llm_calls_total`                     | Counter   | `provider`, `model`, `mode`, `status`        | NL2SQL / explain / summarize calls.                                                  |
| `dbview_llm_call_latency_seconds`            | Histogram | `provider`, `model`, `mode`                  | LLM latency.                                                                         |
| `dbview_llm_tokens_total`                    | Counter   | `provider`, `model`, `type`                  | Input/output tokens, when provider returns counts.                                   |
| `dbview_query_executions_total`              | Counter   | `dialect`, `status`                          | Query executor outcomes.                                                             |
| `dbview_query_execution_latency_seconds`     | Histogram | `dialect`                                    | Query latency.                                                                       |
| `dbview_schema_introspection_failures_total` | Counter   | `dialect`, `reason`                          | Introspector errors by reason.                                                       |
| `dbview_auth_events_total`                   | Counter   | `event`                                      | `login_success`, `login_fail`, `register`, `token_rotate`, `token_replay`, `logout`. |
| `dbview_connections_up`                      | Gauge     | `connection_id`, `dialect`                   | Reserved for future periodic reachability probe.                                     |

`status_bucket` is `1xx`/`2xx`/`3xx`/`4xx`/`5xx` to keep cardinality bounded.

### Prometheus scrape

The bundled Prometheus config (`deploy/observability/prometheus/prometheus.yml.tpl`) authenticates with the service API key:

```yaml
scrape_configs:
  - job_name: dbview-api
    metrics_path: /api/metrics
    static_configs: [{ targets: ['dbview-api:3001'] }]
    authorization:
      type: ApiKey
      credentials_file: /etc/prometheus/dbview-api-key
```

Templated with `envsubst`; supply via `deploy/observability/.env`.

## Health probes

| Endpoint                | Probe                                                                                                                                         |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/health`       | Legacy: returns `{ status, uptime, version }`. Used by docker-compose healthcheck.                                                            |
| `GET /api/health/live`  | Kubernetes liveness. 200 if the process is up.                                                                                                |
| `GET /api/health/ready` | Kubernetes readiness. Deep — checks `DBVIEW_DATA_DIR` writable, `DBVIEW_JWT_SECRET` ≥ 32 chars, `DBVIEW_SECRET` ≥ 16 chars. 503 if any fails. |

All three are public and skip request logging.

## Frontend telemetry — Grafana Faro

[`@grafana/faro-web-sdk`](https://github.com/grafana/faro-web-sdk) plus `@grafana/faro-web-tracing`. Init in `apps/web/src/lib/observability.ts`, called from `main.tsx`. No-op unless `VITE_OTLP_ENDPOINT` is set at build/dev time.

Captures:

- Web vitals (LCP, FID, CLS, INP, TTFB).
- Navigation timing.
- Fetch instrumentation (linked to backend traces via traceparent header).
- Errors (unhandled exceptions, unhandled rejections).
- Console (`error`, `warn`).

Batching: 250 ms timeout, max 50 events.

## Bundled observability stack

`deploy/observability/` is self-contained. Bring it up:

```bash
cd deploy/observability
cp .env.example .env             # fill in secrets, especially DBVIEW_API_KEY
envsubst < prometheus/prometheus.yml.tpl > prometheus/prometheus.yml
docker compose up -d
```

Layout:

```
deploy/observability/
├── docker-compose.yml
├── .env.example
├── README.md
├── prometheus/{prometheus.yml.tpl, alerts.yml}
├── grafana/provisioning/{datasources,dashboards}/*.yml
├── grafana/dashboards/         # JSON dashboards
├── loki/loki-config.yml
├── promtail/promtail-config.yml
├── tempo/tempo-config.yml
├── otel-collector/otel-collector-config.yaml
└── alertmanager/alertmanager.yml
```

Wire-up details in [deploy/observability/README.md](../deploy/observability/README.md).

## Alerts

`deploy/observability/prometheus/alerts.yml` ships baseline SLO + infra rules. Notable:

- HTTP error rate sustained above 5 % over 5 min.
- p99 latency above 2 s over 5 min.
- LLM error rate above 10 % over 10 min.
- `dbview_auth_events_total{event="token_replay"}` non-zero — refresh-token theft signal.
- Standard node-exporter rules (memory, disk, CPU).

Alertmanager routes to whatever `alertmanager.yml` is configured for — Slack, PagerDuty, webhook.
