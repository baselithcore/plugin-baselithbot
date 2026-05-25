# HTTP API

All routes prefixed `/api`. Request and response bodies are JSON, validated via Zod (`ZodPipe`).

## Auth contract

- **Unauthenticated** (marked `@Public()`): health probes, login, register (if enabled), refresh, logout, `/auth/config`.
- **Authenticated**: any user with a valid `Authorization: Bearer <accessToken>` JWT.
- **Admin-only** (`@Roles('admin')`): connections CRUD, user management, history clear, `/api/metrics`.
- **Service-to-service**: pass `X-API-Key: <DBVIEW_API_KEY>` to bypass JWT. The `ApiKeyGuard` attaches a synthetic admin principal. Use for CI, Prometheus scrapes, or cron jobs only.

Error responses share the shape `{ code: string, message: string, issues?: unknown }`.

## Rate limits

| Endpoint                  | Limit         |
| ------------------------- | ------------- |
| `POST /api/auth/login`    | 5 / 60s / IP  |
| `POST /api/auth/register` | 5 / 60s / IP  |
| `POST /api/auth/refresh`  | 30 / 60s / IP |
| `POST /api/nl2sql`        | 20 / 60s / IP |
| `POST /api/nl2sql/ask`    | 20 / 60s / IP |

## Endpoint reference

### Health — public

| Method | Path                | Description                                                                                                                                                             |
| ------ | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/health`       | Legacy liveness, returns `{ status, uptime, version }`.                                                                                                                 |
| `GET`  | `/api/health/live`  | Kubernetes liveness. Always 200 if the process is up.                                                                                                                   |
| `GET`  | `/api/health/ready` | Kubernetes readiness. Checks data dir writability, JWT secret ≥32 chars, `DBVIEW_SECRET` ≥16 chars. Returns 503 if degraded with a `dependencies` map of probe results. |

### Auth

| Method | Path                 | Auth                                               | Description                                                                                                     |
| ------ | -------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `POST` | `/api/auth/login`    | public                                             | Body: `{ email, password }`. Returns `{ accessToken, expiresIn, user }`. Sets `dbview_refresh` httpOnly cookie. |
| `POST` | `/api/auth/register` | public (gated on `DBVIEW_ALLOW_REGISTRATION=true`) | Self-signup. Same response as login.                                                                            |
| `GET`  | `/api/auth/config`   | public                                             | Returns `{ registrationEnabled: boolean }` for the login UI.                                                    |
| `POST` | `/api/auth/refresh`  | public (reads cookie)                              | Rotates the refresh-token family, returns a new `accessToken`. Family revoked if replayed.                      |
| `POST` | `/api/auth/logout`   | public                                             | Revokes the family, clears the cookie.                                                                          |
| `GET`  | `/api/auth/me`       | JWT                                                | Current user profile.                                                                                           |

### Users — admin only

| Method   | Path                  | Description                                                         |
| -------- | --------------------- | ------------------------------------------------------------------- |
| `GET`    | `/api/auth/users`     | List users (no password hashes).                                    |
| `POST`   | `/api/auth/users`     | Body: `{ email, password, role, displayName? }`. Creates user.      |
| `PATCH`  | `/api/auth/users/:id` | Update `displayName` / `role` / `isActive` / `password`.            |
| `DELETE` | `/api/auth/users/:id` | Remove user. Cannot delete the synthetic service principal or self. |

### Connections — admin only

Connection strings are never returned in plaintext. The API stores `connectionStringCipher` (AES-256-GCM with key derived from `DBVIEW_SECRET` via scrypt).

| Method   | Path                           | Description                                                                |
| -------- | ------------------------------ | -------------------------------------------------------------------------- |
| `GET`    | `/api/connections`             | List connection summaries.                                                 |
| `GET`    | `/api/connections/:id`         | Single summary.                                                            |
| `POST`   | `/api/connections`             | Body: `CreateConnectionSchema`. Tests reachability before saving.          |
| `POST`   | `/api/connections/test`        | Test without persisting.                                                   |
| `POST`   | `/api/connections/upload-dump` | Multipart-style base64 body to import a SQLite dump (SQL or binary `.db`). |
| `DELETE` | `/api/connections/:id`         | Remove connection.                                                         |

### Schema

| Method | Path                                  | Description                                                         |
| ------ | ------------------------------------- | ------------------------------------------------------------------- |
| `GET`  | `/api/schema/:connectionId?refresh=1` | Returns `UnifiedSchema`. `?refresh=1` bypasses the in-memory cache. |

### Query

| Method | Path                 | Description                                                                                                                                                                                 |
| ------ | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST` | `/api/query/execute` | Body: `{ connectionId, query, rowLimit }`. Revalidates the query against safety rules, opens a read-only session, returns `{ columns, rows, rowCount, durationMs, truncated }`.             |
| `POST` | `/api/query/sample`  | Body: `{ connectionId, entityName, rowLimit }`. Generates and runs a `SELECT … LIMIT` (or dialect equivalent) over the named entity. Identifier checked against `^[A-Za-z_][A-Za-z0-9_]*$`. |

### NL2SQL

| Method | Path              | Description                                                                                                                                                                               |
| ------ | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST` | `/api/nl2sql`     | Body: `Nl2SqlRequestSchema` (`{ connectionId, prompt, provider, model?, allowDml?, rowLimit?, ollamaBaseUrl? }`). Returns `{ query, language, explanation, warnings, involvedEntities }`. |
| `POST` | `/api/nl2sql/ask` | Multi-turn conversation. Same provider/model knobs plus prior turns.                                                                                                                      |

`provider` is one of `ollama` (default), `openai`, `anthropic`. See [NL2SQL pipeline](./nl2sql.md) for retry behavior.

### History

| Method   | Path                                                               | Auth  | Description                              |
| -------- | ------------------------------------------------------------------ | ----- | ---------------------------------------- |
| `GET`    | `/api/history?connectionId=…&limit=50&offset=0&favoritesOnly=true` | JWT   | Returns `{ entries, total }`.            |
| `PATCH`  | `/api/history/:id/favorite`                                        | JWT   | Toggle favorite flag.                    |
| `DELETE` | `/api/history/:id`                                                 | JWT   | Remove one entry.                        |
| `DELETE` | `/api/history?connectionId=…`                                      | admin | Bulk clear. Preserves favorited entries. |

### LLM utility

| Method | Path                               | Description                                              |
| ------ | ---------------------------------- | -------------------------------------------------------- |
| `GET`  | `/api/llm/ollama/models?baseUrl=…` | Proxies `GET {baseUrl}/tags` and returns the model list. |

### Metrics

| Method | Path           | Auth                   | Description                                                                                                                           |
| ------ | -------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/metrics` | admin (or `X-API-Key`) | Prometheus exposition format. Default Node + process metrics plus `dbview_*` custom metrics. See [Observability](./observability.md). |

## Curl examples

```bash
# Login
curl -s -c cookies.txt -X POST http://localhost:3001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@dbview.local","password":"<password>"}'

# Save token from response.accessToken, then call protected endpoints
TOKEN=...

# Create a connection
curl -s -X POST http://localhost:3001/api/connections \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"shop","dialect":"postgres",
       "connectionString":"postgres://dbview_ro:dbview_ro_password@postgres:5432/shopdb"}'

# NL → SQL
curl -s -X POST http://localhost:3001/api/nl2sql \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"connectionId":"...","prompt":"Top 5 customers by revenue","provider":"ollama"}'

# Execute
curl -s -X POST http://localhost:3001/api/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"connectionId":"...","query":"SELECT id, name FROM customer LIMIT 5","rowLimit":1000}'
```
