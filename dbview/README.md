# dbview

Database visualization + Natural Language to Query for **PostgreSQL**, **MySQL**, **MariaDB**, **MSSQL**, **SQLite**, **CockroachDB**, **Oracle**, **ClickHouse**, **DuckDB**, **Neo4j**, **FalkorDB**, **MongoDB**, **Qdrant**, **Redis**, **Elasticsearch**, and **Salesforce (SOQL)**.

Connect a read-only data source, see its schema as an interactive graph, ask in plain English, and get a safe, validated query — generated locally via Ollama (default) or by OpenAI / Anthropic.

📚 **Full documentation lives under [`docs/`](./docs/README.md)** — start there.

---

## Highlights

- **17 engines** across SQL, graph, document, vector, key-value, search, and SaaS.
- **Unified schema graph** — tables/columns + FKs, labels + relationships, collections, sObjects, etc. Auto-laid out with dagre.
- **NL → Query** — Ollama (default, local) with `codellama:7b`; pluggable OpenAI / Anthropic. Per-dialect prompt notes and validators.
- **Safety-first** — AST validator blocks `SELECT *`, DDL, DML by default, multiple statements, unknown tables/labels. Auto-injects `LIMIT`. Read-only DB sessions enforced. Deterministic alias auto-correction avoids round-trips.
- **Column validation** — LLM-generated SQL and SOQL are checked against the introspected schema before being returned; unknowns trigger a retry with Levenshtein suggestions.
- **Auth & RBAC** — JWT (HS256) + argon2id passwords + httpOnly refresh-cookie rotation with replay detection. Admin / user roles. Service-to-service API key.
- **Observability** — Prometheus metrics (`dbview_*`), OpenTelemetry traces, structured Pino JSON logs with secret redaction, deep readiness probe. Grafana Faro web telemetry on the frontend. Bundled `docker-compose` stack under [`deploy/observability/`](./deploy/observability/).
- **Modern UI** — three-pane resizable workspace, command palette (`⌘K`), dark/light theme, keyboard shortcuts (`⌘↵` to generate), CSV export, sortable result table, conversation mode, query history with favorites.
- **Production-grade scaffolding** — NestJS + Fastify, AES-256-GCM encrypted connection strings at rest, non-root Docker images with healthchecks.

---

## Architecture

```text
apps/
  api/                NestJS + Fastify backend (port 3001)
  web/                Vite + React 19 + Tailwind frontend
packages/
  shared/             Zod schemas, errors, dialect enum (single source of truth)
  sql-core/           SQL introspector + AST safety + read-only executor
  cypher-core/        Cypher introspector + safety (Neo4j, FalkorDB, Ultipa)
  document-core/      MongoDB connector
  vector-core/        Qdrant connector
  keyvalue-core/      Redis connector
  search-core/        Elasticsearch connector
infra/
  seed/               Postgres demo schema + data
  neo4j-seed.cypher   Neo4j demo property graph
  falkordb-seed.cypher
deploy/
  observability/      Prometheus + Grafana + Loki + Tempo + OTel collector stack
```

End-to-end types flow from `packages/shared` Zod schemas → API DTOs → React Query → UI. No duplicated types.

### Engine union

```ts
type QueryEngine =
  | {
      kind: 'sql';
      dialect:
        | 'postgres'
        | 'mysql'
        | 'mariadb'
        | 'mssql'
        | 'sqlite'
        | 'cockroach'
        | 'oracle'
        | 'clickhouse'
        | 'duckdb';
    }
  | { kind: 'graph'; dialect: 'neo4j' | 'falkordb' | 'ultipa' }
  | { kind: 'document'; dialect: 'mongodb' }
  | { kind: 'vector'; dialect: 'qdrant' }
  | { kind: 'keyvalue'; dialect: 'redis' }
  | { kind: 'search'; dialect: 'elasticsearch' }
  | { kind: 'saas'; dialect: 'salesforce' };
```

The API dispatches by `dialect`. The frontend renders a different React Flow node type per `kind` (`TableNode`, `LabelNode`, `CollectionNode`, `KeyspaceNode`, `IndexNode`, `SObjectNode`).

See [`docs/architecture.md`](./docs/architecture.md) for the full module map and request flow.

---

## Quick start (Docker — recommended)

Requires Docker 24+ and Docker Compose v2.

```bash
# 1. Core stack: Postgres (with seed) + API + Web
docker compose up -d postgres api web

# 2. (optional) Local LLM
docker compose --profile llm up -d ollama
docker compose exec ollama ollama pull codellama:7b     # SQL + Cypher (chat-tuned)

# 3. (optional) Neo4j with APOC
docker compose --profile graph up -d neo4j
# Wait until ready, then seed:
docker compose exec -T neo4j cypher-shell -u neo4j -p neo4j_password \
  < infra/neo4j-seed.cypher

# 4. (optional) FalkorDB
docker compose --profile graph up -d falkordb
# Seed (host port 56379, graph name "shop"):
docker exec dbview-falkordb-1 redis-cli GRAPH.QUERY shop "$(tr '\n' ' ' < infra/falkordb-seed.cypher)"
```

Open <http://localhost:8088>. Log in with the `DBVIEW_ADMIN_*` credentials from your `.env` (see [`docs/auth.md`](./docs/auth.md) for bootstrap behavior).

### Demo connection strings (inside the docker network)

| Dialect       | Connection string                                                       |
| ------------- | ----------------------------------------------------------------------- |
| Postgres      | `postgres://dbview_ro:dbview_ro_password@postgres:5432/shopdb`          |
| Neo4j         | `neo4j://neo4j:neo4j_password@neo4j:7687`                               |
| FalkorDB      | `falkor://falkordb:6379/shop`                                           |
| MongoDB       | `mongodb://root:example@mongo:27017/admin`                              |
| Redis         | `redis://redis:6379/0`                                                  |
| Elasticsearch | `http://elastic:changeme@elasticsearch:9200`                            |
| Qdrant        | `http://qdrant:6333`                                                    |
| Salesforce    | `salesforce://<instanceUrl>?clientId=…&clientSecret=…&apiVersion=v60.0` |
| SQLite        | Upload a `.db` or SQL dump via the UI                                   |

### Demo query

In the **Ask** panel:

> Top 5 customers by total revenue

→ generated SQL with explicit columns, JOINs annotated as comments, `LIMIT` injected, validated by AST. Hit **Run** to execute against the read-only role.

For Neo4j, switch to the `shop-graph` connection:

> Customers with the most orders

→ generated Cypher.

---

## Local development

Requires Node 22+ and pnpm 11+.

```bash
pnpm install

# One-time build of internal libs (they ship from dist/)
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
# → Web:  http://localhost:5173 (proxies /api → :3001)
```

Pre-commit gates:

```bash
pnpm -r typecheck   # every package and app
pnpm -r test        # safety validators + service unit tests
pnpm lint
```

---

## Configuration

### Required

- `DBVIEW_JWT_SECRET` — JWT signing key, ≥ 32 chars (`openssl rand -hex 32`).
- `DBVIEW_SECRET` — connection-string AES-256-GCM master key, ≥ 16 chars.

### Common knobs

- `PORT` (default `3001`), `NODE_ENV`, `LOG_LEVEL`, `LOG_FORMAT`.
- `DBVIEW_DATA_DIR` (default `./data`) — host for `users.json`, `connections.json`, `sessions.json`, `history.json` (mode `0600`).
- `DBVIEW_ADMIN_EMAIL` / `DBVIEW_ADMIN_PASSWORD` — bootstrap admin on first boot.
- `DBVIEW_API_KEY` — service-to-service key. Pass as `X-API-Key` to bypass JWT; the guard attaches a synthetic admin principal.
- `DBVIEW_NL2SQL_MAX_RETRIES` (default `2`, clamped 0..4).
- `OLLAMA_BASE_URL` + `OLLAMA_MODEL_{SQL,GRAPH,DOCUMENT,KEYVALUE,SEARCH,VECTOR,SAAS,EXPLAIN}` — per-kind model overrides; defaults to `codellama:7b`.
- `OPENAI_API_KEY` / `OPENAI_MODEL` (default `gpt-4o-mini`).
- `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` (default `claude-sonnet-4-6`).
- `OTEL_EXPORTER_OTLP_ENDPOINT` — collector base URL. Tracing is a no-op if unset.
- `VITE_OTLP_ENDPOINT` — frontend Faro endpoint (build-time).

Full reference: [`docs/configuration.md`](./docs/configuration.md).

---

## API (HTTP)

All paths prefixed `/api`. Health and auth endpoints are public; everything else requires `Authorization: Bearer <accessToken>` JWT or `X-API-Key: <DBVIEW_API_KEY>`. Admin role gates connections CRUD, user management, and `/api/metrics`.

| Group       | Paths                                               | Auth   | Notes                                           |
| ----------- | --------------------------------------------------- | ------ | ----------------------------------------------- |
| Health      | `/health`, `/health/live`, `/health/ready`          | public | `ready` is deep (data dir, secrets).            |
| Auth        | `/auth/login`, `/auth/refresh`, `/auth/logout`      | public | Rate-limited. Refresh cookie rotation + replay. |
| Auth        | `/auth/me`                                          | JWT    | Current user.                                   |
| Users       | `/auth/users`, `/auth/users/:id`                    | admin  | Invite-only CRUD.                               |
| Connections | `/connections/*`                                    | admin  | CRUD, reachability test, dump upload.           |
| Schema      | `/schema/:connectionId?refresh=1`                   | JWT    | Returns `UnifiedSchema`.                        |
| NL2SQL      | `/nl2sql`, `/nl2sql/ask`                            | JWT    | Rate-limited 20/60s/IP.                         |
| Query       | `/query/execute`, `/query/sample`                   | JWT    | Validator runs again on input.                  |
| History     | `/history`, `/history/:id`, `/history/:id/favorite` | JWT    | Bulk clear is admin.                            |
| LLM         | `/llm/ollama/models`                                | JWT    | Proxy `GET {baseUrl}/tags`.                     |
| Metrics     | `/metrics`                                          | admin  | Prometheus exposition (`dbview_*`).             |

Full endpoint reference: [`docs/api.md`](./docs/api.md).

### Example

```bash
TOKEN=$(curl -s -X POST http://localhost:3001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@dbview.local","password":"<password>"}' \
  | jq -r .accessToken)

curl -s -X POST http://localhost:3001/api/connections \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"shop","dialect":"postgres",
       "connectionString":"postgres://dbview_ro:dbview_ro_password@postgres:5432/shopdb"}'
```

---

## Safety guarantees

Non-negotiable. Rules live in `packages/sql-core/src/safety/validator.ts`, `packages/cypher-core/src/safety.ts`, and `apps/api/src/engine/salesforce/safety.ts`, with unit tests next to each. Each validator runs **twice** — on NL2SQL output and again on `/api/query/execute` input.

### Relational SQL

- ❌ `SELECT *` — must enumerate columns.
- ❌ DDL: `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `RENAME`, `GRANT`, `REVOKE`, `SET`, `USE`, `REPLACE`, `CALL`, `EXECUTE`.
- ❌ DML by default: `INSERT`, `UPDATE`, `DELETE`, `MERGE` (toggle via `allowDml`).
- ❌ Multiple statements (no `;` inside).
- ❌ Tables not present in introspected schema (CTE names auto-allowed).
- ❌ Columns not present on the referenced table — with deterministic alias auto-correction when the column exists on exactly one other table in the same query.
- ✅ Auto-`LIMIT` if missing on `SELECT`.
- ✅ Original SQL identifier case preserved (no parser-induced quoting bugs).
- ✅ DB-level read-only enforced: PG `BEGIN READ ONLY` + `statement_timeout 5s`; SQLite `readonly:true` + `query_only`; equivalent per dialect.

### Cypher

- ❌ Writes: `CREATE`, `DELETE`, `DETACH`, `MERGE`, `SET`, `REMOVE`, `DROP`, `LOAD CSV`, `FOREACH`.
- ❌ Dangerous procs: `apoc.create.*`, `apoc.merge.*`, `apoc.refactor.*`, `apoc.load.*`, `apoc.export.*`, `apoc.periodic.*`, `db.create.*`, `db.drop.*`, `dbms.*`, `tx.*`.
- ❌ Multiple statements.
- ❌ Labels/properties not present in introspected schema.
- ✅ Auto-`LIMIT`.
- ✅ Driver `defaultAccessMode: READ` — server-level enforcement.

### SOQL (Salesforce)

- ❌ Non-`SELECT` statements, `SELECT *`, multiple statements.
- ❌ Unknown sObject in `FROM`.
- ❌ Single-identifier fields not on target sObject (dotted relationship paths pass through to Salesforce server-side validation).
- ✅ Auto-`LIMIT`.

Full details: [`docs/safety.md`](./docs/safety.md).

---

## Keyboard shortcuts

| Shortcut                          | Action                 |
| --------------------------------- | ---------------------- |
| `⌘K` / `Ctrl+K`                   | Open command palette   |
| `⌘↵` / `Ctrl+↵` (in Ask textarea) | Generate query         |
| `Esc`                             | Close palette / dialog |

---

## Project conventions

See [`CLAUDE.md`](./CLAUDE.md) for the full set. Highlights:

- **500 LOC max per file**.
- **TypeScript strict** end-to-end. No `any`. Zod at boundaries.
- **ESM only**. CJS deps imported as `import x from 'pkg'; const { Y } = x`.
- **Single source of truth for types**: `@dbview/shared`.

---

## Roadmap

- [x] Auth (JWT + argon2id + refresh rotation).
- [x] Query history + favorites.
- [x] Observability: Prometheus + OTel + structured logs.
- [x] Column validation + deterministic alias auto-correction.
- [x] Salesforce SOQL support.
- [ ] Playwright E2E suite.
- [ ] Multi-statement `WITH` analyzer for cross-CTE safety.
- [ ] More dialects: BigQuery, Snowflake.
- [ ] Audit log persistence (currently Nest `Logger` only).
- [ ] Multi-tenant isolation.

---

## License

Internal MVP — TBD.
