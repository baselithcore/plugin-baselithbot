# Observability — llm-wiki

Stack: **Prometheus + Grafana + Loki + Promtail + Tempo + OTel Collector + Alertmanager**.
Pattern porting da `agent-jira/deploy/observability/` (Sprint 10).

## Componenti

| Servizio | Porta | Ruolo |
|----------|-------|-------|
| Prometheus | 9090 | TSDB, scrape `/metrics` con auth header `X-API-Key=$WIKI_METRICS_TOKEN` |
| Grafana | 3000 | Dashboard + alerting UI |
| Loki | 3100 | Log aggregation (JSON labels: tenant_id, request_id, level) |
| Promtail | — | Docker JSON-log shipper, autodiscovery via `observability.scrape=true` |
| Tempo | 3200, 4317, 4318 | Trace storage, OTLP gRPC/HTTP |
| OTel Collector | 4319 (HTTP), 4320 (gRPC), 8889 (Prom) | Tail-sampling + resource attrs + Tempo export |
| Alertmanager | 9093 | Routing critical/SLO/quota |
| node-exporter | — | Host metrics |

Network condivisa: `llm-wiki-obs-net`.

## Quickstart

```bash
cd deploy/observability
cp .env.example .env
# imposta almeno WIKI_METRICS_TOKEN (uguale al backend) e LLM_WIKI_TARGET

./bootstrap.sh up
```

Configura il backend llm-wiki perché esporti tracce:

```bash
# .env (root del repo)
WIKI_METRICS_TOKEN=<stesso valore di deploy/observability/.env>
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4319
OTEL_SERVICE_NAME=llm-wiki
LOG_FORMAT=json
```

Riavvia l'app. Dopo qualche minuto:

- Grafana → <http://localhost:3000> (`admin` / `$GRAFANA_ADMIN_PASSWORD`)
- Datasources Prometheus / Loki / Tempo già provisioned
- Dashboard `llm-wiki — Overview` precaricata

## Frontend RUM (opzionale)

Installa Faro nel frontend:

```bash
cd frontend
npm install @grafana/faro-web-sdk @grafana/faro-web-tracing
```

`.env`:

```bash
VITE_OTLP_ENDPOINT=http://localhost:4319
VITE_APP_VERSION=0.1.0
VITE_APP_ENV=dev
```

Senza i package o senza endpoint il front skip-pa init in modo silenzioso.

## Comandi bootstrap

```bash
./bootstrap.sh up        # avvia tutto
./bootstrap.sh down      # ferma e libera porte
./bootstrap.sh status    # ps + scrape target health
./bootstrap.sh reload    # ricarica config Prom + Alertmanager senza restart
./bootstrap.sh logs prometheus
./bootstrap.sh render    # solo envsubst dei .tpl
```

## Cardinalità + retention

- `wiki_tenant_*{tenant_id=...}`: cresce linearmente coi tenant attivi.
  Sotto 10k è gestibile in Prometheus single-binary.
- Loki retention: 30 giorni (filesystem). Migrare a S3/GCS per >10 GB/giorno.
- Tempo retention: 14 giorni.

## Tail sampling

OTel Collector tiene 100% degli errori, 100% degli span >1500ms, 10% baseline.
Config: `otel-collector/otel-collector-config.yaml`.

## Hardening

- `/metrics` non è pubblico: gating bearer admin / X-API-Key / loopback (vedi
  `llm_wiki/api/routers/metrics_router.py`).
- Tutti i servizi obs bind-ano `127.0.0.1` (eccetto Grafana 3000 e
  OTel HTTP 4319 per accettare frontend RUM).
- `WIKI_METRICS_TOKEN` deve essere un secret randomico ≥32 chars.
