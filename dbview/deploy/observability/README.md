# dbview observability stack

Self-contained Prometheus + Grafana + Loki + Promtail + Tempo + OpenTelemetry Collector + Alertmanager + node-exporter for dbview. Mirrors `agent-jira`'s layout 1:1.

## Quick start

```bash
cd deploy/observability
cp .env.example .env       # edit DBVIEW_METRICS_TOKEN to match the api's DBVIEW_API_KEY
# Render prometheus.yml from the template
envsubst < prometheus/prometheus.yml.tpl > prometheus/prometheus.yml
docker compose up -d
```

UIs (bound to 127.0.0.1):

- Grafana: <http://localhost:3000> — login from `.env`
- Prometheus: <http://localhost:9090>
- Alertmanager: <http://localhost:9093>
- Tempo HTTP: <http://localhost:3200>

## Wiring the api

1. Set `DBVIEW_API_KEY=<the same as DBVIEW_METRICS_TOKEN>` on the api container.
2. Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://dbview-otelcol:4318` so traces flow.
3. Set `LOG_FORMAT=json` so Promtail can parse structured fields.
4. Add label `observability.scrape=true` on the api container for Promtail discovery.
5. Join the `dbview-obs-net` external network.

## Frontend (Faro)

Set `VITE_OTLP_ENDPOINT` to a URL the browser can reach (typically `http://localhost:4319`, exposed by the OTel Collector). Vite reads `.env` at build/dev time.

## Notes

- Prometheus scrapes `/api/metrics` every 30s using `X-API-Key`.
- The OTel Collector tail-samples: 100% errors, 100% slow (>1.5s), 10% baseline. Health and `/api/metrics` spans are dropped.
- Loki retention defaults to 30 days; bump `loki/loki-config.yml` for prod.
- `alertmanager.yml` ships with an empty receiver — add Slack/email destinations before deploying.
