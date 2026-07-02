# CLAUDE.md — dbview

Project context for AI assistants. Read fully before edits.

## What this is

Database visualization + NL2SQL MVP. Monorepo (pnpm + Turbo).

- `apps/web` — Vite + React 19 + Tailwind + React Flow (dagre) + TanStack Query + Zustand
- `apps/api` — NestJS + Fastify
- `packages/shared` — Zod schemas + types (single source of truth, end-to-end)
- `packages/sql-core` — DB introspector + safety validator (AST) + read-only executor
- `infra/seed` — Postgres demo schema (`shop`)

## Hard rules

### Code

- **Max 500 LOC per file**. Split before exceeding. Extract cohesive units (one component / one service / one concern per file). No dump files.
- **TypeScript strict everywhere**. No `any`. No `@ts-ignore` without inline reason. Prefer `unknown` + narrow.
- **Zod at boundaries**: HTTP body, env config, parsed LLM output. Internal modules trust types.
- **Single source of truth for types**: `@dbview/shared` Zod schemas → infer types. Never duplicate type defs across api/web.
- **No `console.log` in production paths**. Use Nest `Logger`. UI: structured client-side error surfacing.
- **No raw HTML injection in React** (the dangerous `__html` prop). Tokenize/render via React or use sanitizer.
- **ESM only**: `"type": "module"` everywhere. CJS deps → default import + destructure (`import pg from 'pg'; const { Pool } = pg`). Tsx in dev hides this; Node ESM exposes it.
- **Workspace deps via dist**: `@dbview/shared` and `@dbview/sql-core` ship from `dist/`. Build them before consumers in CI/Docker.
- **No `publishConfig.directory`** in workspace pkgs — breaks pnpm symlink resolution.

### SQL safety (non-negotiable)

These rules live in `packages/sql-core/src/safety/validator.ts`. Tests in `validator.test.ts`. Don't loosen without updating both + getting explicit approval.

1. **Never `SELECT *`** — enumerate columns.
2. **Block DDL**: DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, SET, USE, RENAME.
3. **Block DML by default**: INSERT/UPDATE/DELETE/MERGE require `allowDml: true` from caller.
4. **Single statement only** — no `;` inside.
5. **Tables must exist in schema** — reject unknown table refs (CTE names auto-allowed).
6. **Auto-inject `LIMIT`** for SELECT when missing.
7. **Preserve original SQL identifier case** — never re-`sqlify` (PG-quotes break case-sensitive lookups).
8. **DB-level read-only enforcement**:
   - Postgres: `BEGIN READ ONLY; ...; COMMIT` + `statement_timeout: 5_000`
   - SQLite: open `readonly: true` + `PRAGMA query_only = ON`

### NL2SQL pipeline

- Provider strategy: Ollama default (local), OpenAI/Anthropic optional (env). Adapter in `apps/api/src/nl2sql/llm/`.
- Prompt: schema serialized compact + few-shot rules. JSON-only output. Temperature 0.
- Pipeline: `compactSchema → buildPrompt → llm.complete → parseJson → validateAndAnnotate → return`. One retry with validator feedback on parse/safety failure.
- Rate limit: 20 req/60s per IP via `RateLimitGuard`.

### Connections

- Connection string encrypted at rest (AES-256-GCM). Key from `DBVIEW_SECRET` (≥16 chars) via scrypt.
- Plaintext only in-memory at connect time. Never returned via HTTP. Never logged.
- Test reachability before save (`assertReachable` introspect).
- Persist to `${DBVIEW_DATA_DIR:-./data}/connections.json`, atomic write (tmp+rename), mode 0600.

## UI/UX best practices (frontend)

### Visual

- **Dark mode default**, light optional. Use semantic CSS vars (`--surface-0/1/2`, `--accent`, `--accent-fg`) — never raw hex inline.
- **Tailwind + composable utilities**. Component classes in `globals.css` for repeated patterns (`.btn`, `.btn-primary`, `.input`, `.panel`).
- **Type scale**: 10/11/12px (meta), 13/14px (body), 16/18px (headings). Never below 10px.
- **Spacing scale**: stick to Tailwind 1/2/3/4/6/8 — no arbitrary `[7px]`.
- **Iconography**: `lucide-react`. Size by context: 3.5/4/5/6 (12/16/20/24px). Stroke-width consistent.
- **Color hierarchy**: surface (bg) → text (fg) → accent (interactive) → semantic (rose/amber/emerald). Avoid 5+ chromatic accents in one view.
- **Schema graph header gradient**: deterministic hash → palette index. Same schema → same color, always.

### Interaction

- **Optimistic updates** for create/delete via TanStack mutate. Invalidate query keys narrowly.
- **Loading states**: skeleton > spinner. Show structure first.
- **Error states**: inline near triggering action, not toast. Quote error code (`code: 'unsafe_sql'`).
- **Empty states**: actionable copy + CTA, not "No data".
- **Destructive ops**: `confirm()` minimum; modal for irreversible.
- **Keyboard**: forms submit on Enter, Esc closes overlays. Tab order matches visual flow.
- **Latency**: actions <200ms feel instant; >500ms need progress feedback.

### Layout

- **Three-pane workspace** (sidebar / canvas / inspector) is the default for tools like this. Avoid modal-heavy flows.
- **No layout shift** during loads — reserve space.
- **`min-h-0` + `overflow-auto`** on flex children to scroll inside layouts, not body.
- **Responsive**: target 1280×720 baseline. Below, collapse panels. Don't over-engineer for mobile in MVP.

### Performance

- **React Flow**: memoize nodes/edges; layout in `useMemo` keyed on graph + highlights.
- **Bundle**: lazy-import heavy panels (graph, results) when web bundle >500KB.
- **`useState` for ephemeral, Zustand for cross-panel, TanStack Query for server state**. Don't mix.
- **No prop drilling >2 levels** — use store or context.

### Accessibility

- All interactive elements: focus ring (`focus:ring-2 focus:ring-accent`).
- All icons-as-buttons: `aria-label`.
- Color contrast: text on surface ≥ WCAG AA. Don't rely on color alone for state (add icon/label).

## Project conventions

### File organization

- One Nest module per feature (`connections/`, `schema/`, `nl2sql/`, `query/`, `health/`).
- Each module: `*.module.ts`, `*.controller.ts`, `*.service.ts`. Add subfolders only when >3 collaborators.
- React components: one component per file. Hooks in `lib/` or co-located if scoped.
- Tests next to source: `validator.ts` + `validator.test.ts`.

### Naming

- Files: `kebab-case.ts` for utilities, `PascalCase.tsx` for React components.
- Exports: named, not default (except React components).
- Schemas: `XxxSchema` (Zod), inferred type `Xxx`. Pattern: `export type Foo = z.infer<typeof FooSchema>`.

### Error handling

- API: throw typed `DbviewError` subclasses (`UnsafeSqlError`, `IntrospectionError`, `LlmProviderError`). Filter maps to HTTP status + `{code, message}`.
- Web: `axios` errors → surface message inline. Never swallow.
- Don't wrap library errors generically — preserve original message; prefix with context.

### Imports

- Absolute monorepo: `@dbview/shared`, `@dbview/sql-core`.
- Within package: `./relative` with `.js` extension (NodeNext rule).
- Side-effect imports first (`reflect-metadata`), framework, internal, types.

## Workflow

### Local dev

```bash
pnpm install
pnpm --filter @dbview/shared --filter @dbview/sql-core build  # one-time
pnpm dev   # turbo: api on :3001, web on :5173
```

### Docker

```bash
docker compose up -d postgres api web
docker compose --profile llm up -d ollama  # optional
```

### Pre-commit checks

- `pnpm -r typecheck` — must pass
- `pnpm -r test` — must pass
- Don't commit if either fails.

### When adding a feature

1. Define Zod schema in `packages/shared` first.
2. Implement service in api / package, with unit test.
3. Wire controller + DTO via `ZodPipe`.
4. Add UI component consuming via `lib/api.ts`.
5. Validate end-to-end with curl or browser before claiming done.

## Things to NOT do

- Don't add an ORM. `pg` + `better-sqlite3` directly is intentional — we read foreign DBs we don't own.
- Don't add a database for app state until JSON file persistence becomes a real bottleneck.
- Don't introduce `clsx` patterns inside Tailwind utility strings — use `cn()` from `lib/cn.ts` for conditionals.
- Don't use `any` to silence TS — fix the type.
- Don't disable safety validator rules; add new tests if you find a false positive.
- Don't mix `tsx` runtime with built dist — pick one per environment.
- Don't add new top-level dirs without updating this file.

## Auth / RBAC

Implemented in `apps/api/src/auth/`. Mirrors the design of `agent-jira` (FastAPI) ported to NestJS/TS.

- **Roles**: `admin` / `user`. Default protected: every endpoint requires JWT unless decorated `@Public()`. Admin-only endpoints use `@Roles('admin')`.
- **Password hashing**: argon2id (OWASP 2024: m=19456 KiB, t=2, p=1). No bcrypt, no PBKDF2.
- **Access token**: JWT HS256, 15-minute TTL, issuer `dbview-api`. Sent as `Authorization: Bearer`. Stored in memory only on the frontend (XSS-hardened, no localStorage).
- **Refresh token**: opaque 48-byte random, SHA-256-hashed at rest. httpOnly + Secure (prod) + SameSite=Strict cookie `dbview_refresh`, path `/api/auth`, 30-day TTL. Rotated on every `/auth/refresh` call.
- **Replay detection**: family_id tracks rotation chain. Presenting a revoked token revokes the entire family (forced re-login).
- **Persistence**: `users.json` and `sessions.json` in `${DBVIEW_DATA_DIR:-./data}`, atomic write + mode 0600 (same pattern as `connections.json`).
- **Bootstrap**: on first boot, if no users exist and `DBVIEW_ADMIN_EMAIL` + `DBVIEW_ADMIN_PASSWORD` (≥12 chars) are set, seed admin. Otherwise logs a warning and rejects logins (no default password).
- **Registration**: invite-only. Admin creates users via `POST /api/auth/users`. No public sign-up.
- **Rate limits**: login 5/min/IP, refresh 30/min/IP. Existing nl2sql 20/min retained.
- **Service-to-service**: `DBVIEW_API_KEY` still works. The `ApiKeyGuard` attaches a synthetic admin principal so JWT guard short-circuits. Use for CI/automation only.
- **Env vars**: `DBVIEW_JWT_SECRET` (≥32 chars, **required**), `DBVIEW_JWT_ACCESS_TTL` (seconds, default 900), `DBVIEW_JWT_REFRESH_TTL` (seconds, default 2592000), `DBVIEW_ADMIN_EMAIL`, `DBVIEW_ADMIN_PASSWORD`.

### Auth endpoints

- `POST /api/auth/login` — `{email, password}` → `{accessToken, expiresIn, user}` + sets refresh cookie. Public.
- `POST /api/auth/refresh` — reads cookie, rotates, returns new access token. Public.
- `POST /api/auth/logout` — revokes family, clears cookie. Public.
- `GET  /api/auth/me` — returns current user. Authenticated.
- `GET  /api/auth/users` — list users. Admin.
- `POST /api/auth/users` — invite user. Admin.
- `PATCH /api/auth/users/:id` — update role / displayName / isActive / password. Admin.
- `DELETE /api/auth/users/:id` — remove user. Admin.

## Observability

Same stack as `agent-jira`, ported to NestJS/TypeScript. Configs under `deploy/observability/`.

### What ships in-process

- **Structured JSON logs**: `nestjs-pino` + `LOG_FORMAT=json` → JSON with `request_id`, `level`, `name`, `msg`. Redact list covers `authorization`, `x-api-key`, `cookie`, `set-cookie`, `connectionString`, `connectionStringCipher`, `password`, `passwordHash`, `accessToken`, `refreshToken`. Set `LOG_FORMAT=json` in prod.
- **Request IDs**: Fastify `onRequest` hook reads `X-Request-Id` (or generates UUIDv4), stores it in an `AsyncLocalStorage` context, echoes back via response header, and pino bindings emit it on every log line.
- **OpenTelemetry tracing**: opt-in via `OTEL_EXPORTER_OTLP_ENDPOINT`. Auto-instruments `http`, `fastify`, `pg`, `redis`, etc. Batch span processor → OTLP HTTP exporter. Health and `/api/metrics` excluded.
- **Prometheus metrics**: `prom-client` registry exposed at `GET /api/metrics`, admin-only. Default Node + process metrics + custom `dbview_*` counters/histograms:
    - `dbview_http_request_latency_seconds{method, route, status_bucket}`
    - `dbview_http_request_errors_total{method, route, status_bucket, reason}`
    - `dbview_llm_calls_total{provider, model, mode, status}` + latency histogram + tokens counter
    - `dbview_query_executions_total{dialect, status}` + latency histogram
    - `dbview_schema_introspection_failures_total{dialect, reason}`
    - `dbview_auth_events_total{event}` — login_success, login_fail, token_replay, token_rotate
    - `dbview_connections_up{connection_id, dialect}` (gauge, reserved for future periodic probe)
- **Health probes**: `GET /api/health` (legacy), `GET /api/health/live`, `GET /api/health/ready` (deep — checks data dir writability, `DBVIEW_JWT_SECRET`, `DBVIEW_SECRET`). Ready returns HTTP 503 when degraded.
- **Frontend telemetry**: `@grafana/faro-web-sdk` + `@grafana/faro-web-tracing`. Init in `apps/web/src/lib/observability.ts`. No-op unless `VITE_OTLP_ENDPOINT` set at build/dev time. Captures web vitals, navigation, fetch, errors, console.

### What ships in `deploy/observability/`

Identical layout to agent-jira (Prometheus 2.55, Grafana 11.3, Loki 3.2, Promtail 3.2, Tempo 2.6, OTel Collector contrib 0.113, Alertmanager 0.27, node-exporter 1.8):

```text
deploy/observability/
├── docker-compose.yml
├── .env.example
├── README.md
├── prometheus/
│   ├── prometheus.yml.tpl   # envsubst → prometheus.yml
│   └── alerts.yml           # dbview_* SLO + infra rules
├── grafana/
│   ├── provisioning/{datasources,dashboards}/*.yml
│   └── dashboards/          # add JSON dashboards here
├── loki/loki-config.yml
├── promtail/promtail-config.yml
├── tempo/tempo-config.yml
├── otel-collector/otel-collector-config.yaml   # tail-sampling + filter/noise
└── alertmanager/alertmanager.yml
```

Bring up: `cd deploy/observability && cp .env.example .env && envsubst < prometheus/prometheus.yml.tpl > prometheus/prometheus.yml && docker compose up -d`. See `deploy/observability/README.md` for wiring details.

### Observability env vars

- `LOG_FORMAT` — `json` for prod (Promtail parses it), default pretty in dev.
- `LOG_LEVEL` — pino level, default `info` prod / `debug` dev.
- `OTEL_EXPORTER_OTLP_ENDPOINT` — collector base URL (e.g. `http://dbview-otelcol:4318`). Tracing is no-op when unset.
- `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` — override `/v1/traces` suffix.
- `OTEL_SERVICE_NAME` — defaults to `dbview-api`.
- `APP_VERSION` — surfaced as `service.version` resource attr and in `/health` payload.
- `VITE_OTLP_ENDPOINT`, `VITE_APP_NAME`, `VITE_APP_VERSION`, `VITE_DEPLOY_ENV` — frontend Faro config.
- `DBVIEW_API_KEY` — also used by Prometheus to scrape `/api/metrics` (same key, service-to-service path).

### Operational notes

- `/api/metrics` is _not_ public — Prometheus must pass `X-API-Key`. Same key authorizes the synthetic admin principal so service-to-service scrapes don't need a JWT.
- Health endpoints are public; both `/api/health` and `/api/health/live`/`ready` are exempt from auth and from request logging.
- OTel collector tail-sampling: 100% errors, 100% slow (>1.5s), 10% baseline. Health/metrics spans filtered out.
- Multi-tenant labels intentionally absent — single-tenant deployment.

## Open extensions (not yet implemented)

- GraphDB / Cypher (Neo4j) — separate `packages/cypher-core`, `QueryEngine` discriminated union, force-directed layout for property graphs.
- E2E tests (Playwright).
- Multi-tenant isolation (single-tenant for MVP).
- Audit log persistence (currently only Nest `Logger`).
