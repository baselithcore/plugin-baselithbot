# Deployment

Two paths: local dev with `pnpm dev` (turbo runs API + web in parallel) or Docker Compose for a production-shaped stack with optional engines and a local LLM.

## Local development

Requires Node 22+ and pnpm 11+.

```bash
pnpm install

# One-time build of internal workspace packages (they ship from dist/)
pnpm --filter @dbview/shared \
     --filter @dbview/sql-core \
     --filter @dbview/cypher-core \
     --filter @dbview/document-core \
     --filter @dbview/vector-core \
     --filter @dbview/keyvalue-core \
     --filter @dbview/search-core \
     build

# Dev (turbo runs api + web in parallel)
pnpm dev
# → API:  http://localhost:3001
# → Web:  http://localhost:5173  (proxies /api → :3001)
```

Pre-commit gates (must pass):

```bash
pnpm -r typecheck
pnpm -r test
pnpm lint
```

A minimal `.env` for local dev:

```bash
DBVIEW_JWT_SECRET=$(openssl rand -hex 32)
DBVIEW_SECRET=$(openssl rand -hex 32)
DBVIEW_ADMIN_EMAIL=you@example.com
DBVIEW_ADMIN_PASSWORD=changeme-please-12chars
```

## Docker Compose

Requires Docker 24+ and Compose v2. The root `docker-compose.yml` wires everything with named profiles so you only spin up what you need.

### Core stack

```bash
docker compose up -d postgres api web
```

Brings up:

- `postgres:16-alpine` — seeded from `infra/seed/` on first boot. Creates the read-only `dbview_ro` user used in demos.
- `api` — built from [apps/api/Dockerfile](../apps/api/Dockerfile). Node 22 slim, multi-stage, non-root `dbview` user, `tini` init, `/data` volume. Healthcheck via `/api/health`.
- `web` — built from [apps/web/Dockerfile](../apps/web/Dockerfile). Vite production build served by nginx-unprivileged on `:8080` (mapped to `:8088` on the host).

Open **http://localhost:8088**. Log in with the `DBVIEW_ADMIN_*` credentials from your `.env`.

### Optional profiles

| Profile    | Service(s)          | Use                                                                                  |
| ---------- | ------------------- | ------------------------------------------------------------------------------------ |
| `llm`      | `ollama`            | Local LLM provider. After up: `docker compose exec ollama ollama pull codellama:7b`. |
| `graph`    | `neo4j`, `falkordb` | Cypher engines. Seed below.                                                          |
| `document` | `mongo`             | MongoDB.                                                                             |
| `keyvalue` | `redis`             | Redis.                                                                               |
| `search`   | `elasticsearch`     | Elasticsearch.                                                                       |
| `vector`   | `qdrant`            | Qdrant.                                                                              |

Bring them up explicitly:

```bash
docker compose --profile llm up -d ollama
docker compose --profile graph up -d neo4j falkordb
```

### Seed scripts

Postgres seeds automatically. Graph engines need manual seeding:

```bash
# Neo4j
docker compose exec -T neo4j cypher-shell -u neo4j -p neo4j_password \
  < infra/neo4j-seed.cypher

# FalkorDB
docker exec dbview-falkordb-1 redis-cli GRAPH.QUERY shop \
  "$(tr '\n' ' ' < infra/falkordb-seed.cypher)"
```

### Demo connection strings (inside the compose network)

| Dialect       | Connection string                                              |
| ------------- | -------------------------------------------------------------- |
| Postgres      | `postgres://dbview_ro:dbview_ro_password@postgres:5432/shopdb` |
| Neo4j         | `neo4j://neo4j:neo4j_password@neo4j:7687`                      |
| FalkorDB      | `falkor://falkordb:6379/shop`                                  |
| MongoDB       | `mongodb://root:example@mongo:27017/admin`                     |
| Redis         | `redis://redis:6379/0`                                         |
| Elasticsearch | `http://elastic:changeme@elasticsearch:9200`                   |
| Qdrant        | `http://qdrant:6333`                                           |
| SQLite        | Upload a `.db` or SQL dump via the UI                          |

## Volumes & persistence

| Volume                                                                                | Mount            | Contents                                                                        |
| ------------------------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------- |
| `apidata`                                                                             | `/data` in `api` | `users.json`, `connections.json`, `sessions.json`, `history.json`. Mode `0600`. |
| `pgdata`                                                                              | postgres data    | persistent DB state                                                             |
| `neo4jdata`, `falkordata`, `mongodata`, `redisdata`, `esdata`, `qdrantdata`, `ollama` | engine data      | persistent per profile                                                          |

`/data` is the only volume the API requires. Back it up to back up auth + connections.

## Healthchecks

- `api` — `curl http://localhost:3001/api/health` every 10 s, 3 s timeout, 5 retries.
- `web` — `wget -q --spider http://localhost:8080/` every 10 s.
- `postgres` — `pg_isready`.
- Engine services use their stock healthchecks.

Compose dependencies wait on `service_healthy` where it matters: `api` waits on `postgres` healthy; `web` waits on `api`.

## Observability stack

Separate `docker-compose.yml` under [deploy/observability/](../deploy/observability/). Run independently:

```bash
cd deploy/observability
cp .env.example .env
# fill in DBVIEW_API_KEY (must match the API's)
envsubst < prometheus/prometheus.yml.tpl > prometheus/prometheus.yml
docker compose up -d
```

The collector reaches into the app network via the shared external network name; see `deploy/observability/README.md`.

## Production checklist

Before exposing to anything beyond localhost:

- [ ] Set `DBVIEW_JWT_SECRET` (≥ 32 chars) and `DBVIEW_SECRET` (≥ 16 chars) to fresh random values.
- [ ] Set `DBVIEW_ADMIN_EMAIL` + `DBVIEW_ADMIN_PASSWORD` (or rotate the auto-generated password on first login).
- [ ] Set `NODE_ENV=production`, `LOG_FORMAT=json`, `LOG_LEVEL=info`.
- [ ] Set `DBVIEW_API_KEY` for Prometheus scrape and lock down `/api/metrics`.
- [ ] Terminate TLS upstream (nginx / Cloudflare / ALB). The web container ships plain HTTP on `:8080`.
- [ ] Mount `/data` on persistent storage; back it up.
- [ ] Set `OTEL_EXPORTER_OTLP_ENDPOINT` if you want traces; otherwise tracing is a no-op.
- [ ] Set `VITE_OTLP_ENDPOINT` at build time for Faro frontend telemetry.
- [ ] Pin model versions: `OLLAMA_MODEL_SQL`, `OPENAI_MODEL`, `ANTHROPIC_MODEL`. Don't ship `latest` tags.
- [ ] Remove default engine credentials (Postgres seed creds, Neo4j `neo4j:neo4j_password`, etc.).

## Rebuild & deploy

```bash
docker compose build api web
docker compose up -d api web
```

API has zero-downtime constraints only on auth (in-flight refresh-token rotation). For a brief moment, a refresh in flight might 401 — clients retry once on 401.
