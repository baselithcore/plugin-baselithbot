# dbview — Database Visualisation + NL→Query Workbench

BaselithCore plugin hosting the upstream **dbview** TypeScript stack (NestJS +
Fastify API, React 19 + Vite SPA, 7 workspace packages) as a supervised Node
child process behind an authenticated FastAPI reverse proxy.

Supports **18 engines**: PostgreSQL, MySQL, MariaDB, MSSQL, SQLite, Oracle,
ClickHouse, DuckDB, CockroachDB, Neo4j, FalkorDB, Ultipa, MongoDB, Redis,
Elasticsearch, Qdrant, Salesforce (SOQL), Salesforce Data Cloud — with schema
graph visualisation, AST-level query safety, NL→SQL/Cypher/SOQL translation
(Ollama/OpenAI/Anthropic), history/favorites and per-user encrypted
connection storage.

## Architecture

```
browser ── /dbview            (built SPA, static mount)
        └─ /api/dbview/…      (FastAPI reverse proxy, streaming)
                │  central auth: get_current_user → require-tab policy
                │  identity → x-dbview-gateway-user + per-boot secret
                ▼
        127.0.0.1:<ephemeral>  (supervised `node dist/main.js`)
                └─ NestJS GatewayAuthGuard → JIT user mirror → engines
```

* **Wrapper** ([plugin.py](plugin.py)) — lifecycle, env composition, tabs.
* **Supervisor** ([supervisor/](supervisor/)) — spawn, health gate, restart
  backoff, SIGTERM→SIGKILL. Loopback bind only.
* **Proxy** ([proxy_router.py](proxy_router.py)) — prefix re-rooting
  (`/api/dbview/X` → `/api/X`), hop-by-hop stripping, `Set-Cookie` path
  rewriting, upstream-down 503 / connect-fail 502.
* **Identity bridge** ([identity.py](identity.py)) — central `AuthUser` →
  gateway header; **effective-admin** (wildcard-aware, degrades closed) →
  dbview `admin` role; identity-derived **tenancy scope key** via
  `resolve_plugin_tenant_key("dbview", "shared")`.

## Central auth & RBAC (platform conventions)

* All identity lives in the platform **auth** plugin. dbview's local
  login/registration/password endpoints return 403 in plugin (gateway) mode;
  users are JIT-mirrored (id = central user id, unusable password sentinel).
* The proxy enforces the central per-tab policy for `(dbview, dbview)` —
  manage access from the auth console's Access Control matrix.
* The SPA reads the shared central token (`localStorage['auth_access_token']`)
  and re-resolves the session on cross-tab `storage` events; without a session
  it shows a bilingual (en/it) "sign in from the console" screen.
* Admin decisions use the **effective permission set** (wildcard custom roles
  count as admin), never the literal role alone.

## Tenancy

Declared `tenancy: shared` (admin can flip to `personal` at runtime from the
auth console). The proxy forwards the resolved scope key per request:

* every mirrored user carries a `tenantKey`;
* connection **sharing** (`all` / `admins` / explicit users) never crosses a
  tenant scope; explicit share targets are validated same-tenant;
* history and LLM credentials are strictly per-owner (per central user id)
  under both modes.

## Operator setup

```bash
# 1) Build once (Node ≥ 20, pnpm ≥ 11)
cd plugins/dbview/dbview
pnpm install && pnpm -r build            # packages + api
VITE_API_BASE_URL=/api/dbview VITE_BASE_PATH=/dbview/ VITE_AUTH_MODE=gateway \
  pnpm --filter @dbview/web build        # plugin-mode SPA

# 2) Mandatory env (stable across restarts — encrypts stored connections)
export DBVIEW_SECRET="<random ≥16 chars>"

# 3) Enable in configs/plugins.yaml (already registered)
# dbview: { enabled: true, mode: prod }
```

Runtime data lives in `plugins/dbview/var/data` (override with
`DBVIEW_DATA_DIR`). See [manifest.yaml](manifest.yaml) for the full env
contract. A standalone build (no `VITE_*`/gateway env) reproduces upstream
behaviour byte-for-byte — local JWT login, refresh-cookie rotation and the
Vite root base all stay intact.

## Tests

```bash
python -m pytest plugins/dbview/tests -q         # wrapper: proxy/supervisor/identity
cd plugins/dbview/dbview && pnpm -r test         # upstream + gateway guard suites
```
