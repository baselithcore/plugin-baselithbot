# Architecture

## Monorepo layout

pnpm workspaces + Turbo. Two deployable apps, seven shared packages.

```
apps/
  api/                NestJS + Fastify, port 3001
  web/                Vite + React 19 + Tailwind, port 5173 dev / 8088 docker
packages/
  shared/             Zod schemas, error classes, dialect enum, env validation
  sql-core/           Postgres/MySQL/MSSQL/SQLite/etc. introspector + AST safety
  cypher-core/        Neo4j/FalkorDB introspector + Cypher safety
  document-core/      MongoDB connector
  vector-core/        Qdrant connector
  keyvalue-core/      Redis connector
  search-core/        Elasticsearch connector
infra/                Seed scripts (Postgres SQL, Neo4j Cypher, FalkorDB)
deploy/observability/ Prometheus + Grafana + Loki + Tempo + OTel collector
```

## Type pipeline — single source of truth

`packages/shared` exports Zod schemas. Inferred TypeScript types flow end-to-end:

```
Zod schema (packages/shared)
   ├── API DTO via ZodPipe (validates HTTP body)
   ├── API service signature (typed)
   ├── HTTP response (Zod-shaped)
   ├── Frontend axios call (lib/api.ts)
   └── TanStack Query cache + Zustand store
```

No duplicate type definitions across api/web. If a contract changes, edit `packages/shared` once.

## Request flow — NL question to result

```
User types in NL2QueryPanel
        │
        ▼
POST /api/nl2sql                            ◄── JWT or API-key + rate limit 20/60s/IP
        │
        ▼
NL2SqlService.translate()
   ├─ load connection (encrypted at rest)
   ├─ introspect schema (cached UnifiedSchema)
   ├─ compactSchema + buildPrompt (dialect-specific notes)
   ├─ llm.complete (provider strategy: ollama | openai | anthropic)
   ├─ sanitize output (placeholder fix, strip ellipsis)
   ├─ validate against safety rules → warnings + unknowns
   ├─ on unknowns: build Levenshtein suggestions, retry up to MAX_RETRIES
   └─ alias auto-correction (deterministic, no retry)
        │
        ▼
Response: { query, language, explanation, warnings, involvedEntities }
        │
        ▼
Frontend stores response, optionally auto-runs via POST /api/query/execute
        │
        ▼
QueryService.execute()
   ├─ revalidate query (defense in depth — input may be edited)
   ├─ open read-only session (PG: BEGIN READ ONLY + statement_timeout 5s;
   │   SQLite: readonly + query_only; Neo4j: defaultAccessMode READ)
   ├─ execute, cap at rowLimit
   └─ emit dbview_query_executions_total + latency histogram
        │
        ▼
ResultTable renders rows; HistoryService records the entry
```

## Engine union

The query engine is a discriminated union over dialect:

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

type UnifiedSchema =
  | { kind: 'relational'; tables; relationships }
  | { kind: 'graph'; labels; relationshipTypes }
  | { kind: 'document'; collections }
  | { kind: 'vector'; collections }
  | { kind: 'keyvalue'; keyspaces }
  | { kind: 'search'; indices }
  | { kind: 'saas'; sObjects };
```

The API dispatches by `dialect`. The frontend chooses a node renderer per `kind` — `TableNode` for relational, `LabelNode` for graph, etc.

## API module map

Every Nest feature is one module. One controller + one service unless explicitly split.

| Module                            | Purpose                               | Route prefix       |
| --------------------------------- | ------------------------------------- | ------------------ |
| `AuthModule`                      | login, register, refresh, logout, /me | `/api/auth`        |
| `UsersController` (in AuthModule) | admin user CRUD                       | `/api/auth/users`  |
| `ConnectionsModule`               | CRUD + test + dump upload, encryption | `/api/connections` |
| `SchemaModule`                    | introspection + cache                 | `/api/schema`      |
| `QueryModule`                     | execute, sample                       | `/api/query`       |
| `Nl2SqlModule`                    | NL→query, ask                         | `/api/nl2sql`      |
| `HistoryModule`                   | query history + favorites             | `/api/history`     |
| `LlmModule`                       | list available Ollama models          | `/api/llm/ollama`  |
| `HealthModule`                    | live/ready/legacy probes              | `/api/health`      |
| `ObservabilityModule`             | Prometheus scrape                     | `/api/metrics`     |

Global guard chain (order matters): `ApiKeyGuard` → `JwtAuthGuard` → `RolesGuard`. `@Public()` short-circuits the JWT guard. `@Roles('admin')` enforces role on top of JWT.

## Persistence

All app state lives in JSON files under `${DBVIEW_DATA_DIR:-./data}`, mode `0600`, atomic write (`.tmp` + rename).

| File               | Contents                                                            |
| ------------------ | ------------------------------------------------------------------- |
| `users.json`       | argon2id-hashed users, role flags, `mustChangePassword`             |
| `connections.json` | metadata + AES-256-GCM `connectionStringCipher`                     |
| `sessions.json`    | refresh-token families (SHA-256 hashed tokens)                      |
| `history.json`     | recent NL→query attempts, favorites, capped at `DBVIEW_HISTORY_MAX` |

No database for app state by design. Switch only when JSON files become a measured bottleneck.

## Frontend layout

Three-pane resizable workspace:

```
┌──────────────┬──────────────────────────────┬────────────────┐
│ Sidebar      │ Canvas                       │ Inspector      │
│ ─ Connections│ ─ Schema graph (React Flow)  │ ─ DetailDrawer │
│ ─ History    │ ─ Result table               │ ─ NL2QueryPanel│
│ ─ Settings   │ ─ Graph viewport 2D/3D       │                │
└──────────────┴──────────────────────────────┴────────────────┘
        TopBar (connection switch, theme, palette ⌘K)
        StatusBar (rows, duration, warnings)
```

State split:

- **Zustand** (`store/app.ts`) — cross-panel app state (selected connection, conversation, theme, panel collapse, etc).
- **TanStack Query** — server state (connections list, schema, query results).
- **`useState`** — purely local component state.

Don't mix. Don't prop-drill more than two levels.
