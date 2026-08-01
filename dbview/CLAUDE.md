# CLAUDE.md — dbview

Project context for AI assistants. Read fully before edits.

## What this is

Database visualization + NL2SQL MVP. Monorepo (pnpm + Turbo) — see the workspace layout and each package's `package.json` for the stack.

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

The rules live in `packages/sql-core/src/safety/validator.ts` (read them there); tests in `validator.test.ts`. Don't loosen without updating both + getting explicit approval. Gotcha: **preserve original SQL identifier case — never re-`sqlify`** (PG-quotes break case-sensitive lookups).

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

Design decisions to preserve (implementation details are in the code):

- **Default protected**: every endpoint requires JWT unless decorated `@Public()`; admin-only via `@Roles('admin')`.
- **Password hashing**: argon2id only (OWASP 2024 params). No bcrypt, no PBKDF2.
- **Access token stored in memory only on the frontend** (XSS-hardened) — never localStorage.
- **Registration is invite-only** (admin creates users). No public sign-up.
- **No default admin password**: bootstrap seeds admin only from `DBVIEW_ADMIN_EMAIL` + `DBVIEW_ADMIN_PASSWORD`; otherwise logins are rejected.
- **`DBVIEW_API_KEY`** attaches a synthetic admin principal (`ApiKeyGuard`) — CI/automation only.

## Observability

Same stack as `agent-jira`, ported to NestJS/TypeScript. Configs under `deploy/observability/`.

In-process: structured pino JSON logs (redacted secrets), request IDs, opt-in OTel tracing, `prom-client` metrics at `GET /api/metrics`, health probes, frontend Faro telemetry — the inventory (metric names, env vars) lives in the code (`apps/web/src/lib/observability.ts`, the metrics module) and in `deploy/observability/README.md`, which also covers bringing up the stack.

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
