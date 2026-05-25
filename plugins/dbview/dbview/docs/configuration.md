# Configuration reference

All API config is read from environment variables. The shared package defines a Zod env schema; startup fails if a required variable is missing or malformed.

## Required

| Variable            | Notes                                                                 |
| ------------------- | --------------------------------------------------------------------- |
| `DBVIEW_JWT_SECRET` | JWT signing secret, ≥ 32 chars. Generate with `openssl rand -hex 32`. |

The app refuses to start without this. `/api/health/ready` reports it as a dependency.

## Core

| Variable            | Default                       | Notes                                                                               |
| ------------------- | ----------------------------- | ----------------------------------------------------------------------------------- |
| `NODE_ENV`          | `development`                 | `production` switches Pino to JSON, disables pretty printing.                       |
| `PORT`              | `3001`                        | API HTTP port.                                                                      |
| `APP_VERSION`       | `0.1.0`                       | Surfaced in `/health` payload and as the OTel `service.version` resource attribute. |
| `LOG_LEVEL`         | `info` (prod) / `debug` (dev) | Pino level.                                                                         |
| `LOG_FORMAT`        | `json` (prod) / pretty (dev)  | Promtail expects JSON in prod.                                                      |
| `DBVIEW_BODY_LIMIT` | `419430400` (400 MB)          | HTTP body size, in bytes. Set high to allow SQLite dump uploads.                    |

## Storage & encryption

| Variable             | Default         | Notes                                                                                                             |
| -------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------- |
| `DBVIEW_SECRET`      | dev placeholder | Master key for connection-string AES-256-GCM. ≥16 chars. Must be set in any non-dev deployment.                   |
| `DBVIEW_DATA_DIR`    | `./data`        | Directory for `users.json`, `connections.json`, `sessions.json`, `history.json`. Created if missing, mode `0700`. |
| `DBVIEW_HISTORY_MAX` | `5000`          | Soft cap on history entries. Oldest non-favorites evicted first.                                                  |

## Auth

| Variable                    | Default                       | Notes                                                                         |
| --------------------------- | ----------------------------- | ----------------------------------------------------------------------------- |
| `DBVIEW_JWT_ACCESS_TTL`     | `900`                         | Access token lifetime in seconds.                                             |
| `DBVIEW_JWT_REFRESH_TTL`    | `2592000`                     | Refresh token lifetime (30 days).                                             |
| `DBVIEW_ADMIN_EMAIL`        | `admin@dbview.local`          | Bootstrap admin email (first boot only).                                      |
| `DBVIEW_ADMIN_PASSWORD`     | random + `mustChangePassword` | ≥12 chars if supplied.                                                        |
| `DBVIEW_ALLOW_REGISTRATION` | `false`                       | When `true`, enables `POST /api/auth/register`.                               |
| `DBVIEW_API_KEY`            | unset                         | Service-to-service shared key. Passes `ApiKeyGuard`, injects synthetic admin. |

## NL2SQL

| Variable                    | Default | Notes                                                    |
| --------------------------- | ------- | -------------------------------------------------------- |
| `DBVIEW_NL2SQL_MAX_RETRIES` | `2`     | Clamped 0..4. Number of retries after the first attempt. |

## LLM providers

### Ollama (default)

| Variable                | Default                      |
| ----------------------- | ---------------------------- |
| `OLLAMA_BASE_URL`       | `http://localhost:11434/api` |
| `OLLAMA_MODEL_SQL`      | `codellama:7b`               |
| `OLLAMA_MODEL_GRAPH`    | `codellama:7b`               |
| `OLLAMA_MODEL_DOCUMENT` | `codellama:7b`               |
| `OLLAMA_MODEL_KEYVALUE` | `codellama:7b`               |
| `OLLAMA_MODEL_SEARCH`   | `codellama:7b`               |
| `OLLAMA_MODEL_VECTOR`   | `codellama:7b`               |
| `OLLAMA_MODEL_SAAS`     | `codellama:7b`               |
| `OLLAMA_MODEL_EXPLAIN`  | `codellama:7b`               |

`sqlcoder:*` models use a different (completion) adapter automatically.

### OpenAI

| Variable               | Default                |
| ---------------------- | ---------------------- |
| `OPENAI_API_KEY`       | —                      |
| `OPENAI_MODEL`         | `gpt-4o-mini`          |
| `OPENAI_MODEL_EXPLAIN` | same as `OPENAI_MODEL` |

### Anthropic

| Variable                  | Default                     |
| ------------------------- | --------------------------- |
| `ANTHROPIC_API_KEY`       | —                           |
| `ANTHROPIC_MODEL`         | `claude-sonnet-4-6`         |
| `ANTHROPIC_MODEL_EXPLAIN` | `claude-haiku-4-5-20251001` |

## Observability

| Variable                             | Default                | Notes                                                                              |
| ------------------------------------ | ---------------------- | ---------------------------------------------------------------------------------- |
| `OTEL_SERVICE_NAME`                  | `dbview-api`           | Resource attribute.                                                                |
| `OTEL_EXPORTER_OTLP_ENDPOINT`        | unset                  | Collector base URL (e.g. `http://otel-collector:4318`). Tracing is no-op if unset. |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | `<endpoint>/v1/traces` | Override traces path only.                                                         |

## Frontend (Vite)

Build-time only. Set in `apps/web/.env` or as build args.

| Variable             | Default                      | Notes                                         |
| -------------------- | ---------------------------- | --------------------------------------------- |
| `VITE_OTLP_ENDPOINT` | unset                        | Grafana Faro / OTel endpoint. No-op if unset. |
| `VITE_APP_NAME`      | `dbview-web`                 |                                               |
| `VITE_APP_VERSION`   | `0.1.0`                      |                                               |
| `VITE_DEPLOY_ENV`    | `development` / `production` | Used as Faro env tag.                         |

## Database side-channels (non-app config)

The Postgres seed image (`infra/seed/`) is parameterized in `docker-compose.yml`:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — superuser to bootstrap.
- The seed script creates `dbview_ro` (read-only) for application use.

Neo4j and FalkorDB use their default credentials from compose. Change before exposing.

## Sample `.env`

```bash
# Required
DBVIEW_JWT_SECRET=$(openssl rand -hex 32)
DBVIEW_SECRET=$(openssl rand -hex 32)

# Auth bootstrap
DBVIEW_ADMIN_EMAIL=admin@example.com
DBVIEW_ADMIN_PASSWORD='strong-password-≥12-chars'

# Storage
DBVIEW_DATA_DIR=/data

# LLM (default: local Ollama)
OLLAMA_BASE_URL=http://ollama:11434/api
OLLAMA_MODEL_SQL=codellama:7b

# Observability (optional)
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
LOG_FORMAT=json
LOG_LEVEL=info

# Service principal (optional, for Prometheus scrape + CI)
DBVIEW_API_KEY=$(openssl rand -hex 32)
```
