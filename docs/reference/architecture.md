# Architecture

dbview is a **RouterPlugin** that hosts a vendored TypeScript stack rather than
reimplementing it. It exposes a REST reverse-proxy under `/api/dbview` and a
bundled React/Vite SPA mounted at `/dbview`. A Python rewrite of 18 engine
adapters and their AST-level query safety would inevitably regress the
upstream project, so the plugin's own code is entirely **hosting,
lifecycle and identity** glue.

## Component map

```
plugins/dbview/
├── plugin.py          DbviewPlugin (RouterPlugin): initialize/shutdown,
│                      router + UI-tab + SPA-mount contracts, secret
│                      resolution, port pinning
├── leader.py          Postgres advisory-lock leadership election for the
│                      single Node child across workers
├── identity.py        AuthUser → dbview gateway-identity bridge (headers,
│                      effective-admin, tenant key)
├── proxy_router.py    Authenticated, streaming reverse-proxy router
├── supervisor/
│   ├── config.py      SupervisorConfig (env + plugin-YAML overrides)
│   └── process.py     NodeSupervisor: spawn / health-gate / restart / stop
└── dbview/            Vendored upstream monorepo (verbatim)
    ├── apps/api/      NestJS + Fastify backend
    ├── apps/web/      Vite + React 19 SPA
    └── packages/      shared · sql-core · cypher-core · document-core ·
                        vector-core · keyvalue-core · search-core
```

## Request flow

```
Browser
   │  GET/POST /api/dbview/*
   ▼
proxy_router.py
   │  get_current_user() (central auth chokepoint)
   │  can_access_dbview_tab()  — central per-tab policy (dbview, dbview)
   │  strip inbound x-dbview-gateway-* headers (anti-spoof)
   │  mint x-dbview-gateway-user + x-dbview-gateway-secret (if authenticated)
   │  strip hop-by-hop headers, rewrite Set-Cookie Path
   ▼  httpx streaming forward, re-rooted /api/dbview/X → /api/X
Node child  (leader-owned, http://127.0.0.1:<port>)
   │  GatewayAuthGuard verifies the shared secret (timingSafeEqual)
   │  JIT-mirrors the gateway identity into the local users store
   ▼
Per-dialect connector (packages/sql-core, cypher-core, document-core, …)
   ▼
Target data source
```

The proxy is streaming end-to-end (`httpx` + `StreamingResponse`), so a
multi-megabyte schema introspection payload is never buffered twice.

## Multi-worker leadership

The embedded dbview app is **single-instance** by construction: its state
(connections, mirrored users, sessions, engine pools) lives in per-process
in-memory maps read once at startup. Under `WEB_CONCURRENCY>1`, every uvicorn
worker used to spawn its **own** Node child on its own ephemeral port — a
connection created via one worker was invisible to the next request that
round-robined to a sibling.

The fix, in [`leader.py`](../reference/architecture.md):

1. At `initialize()`, every worker calls `acquire_dbview_leadership()`, which
   tries `pg_try_advisory_lock(DBVIEW_LEADER_LOCK_KEY)` on a **dedicated**
   Postgres connection (a pooled connection would reset the session on return
   and drop the lock).
2. The winner (`is_leader=True`) spawns the single Node child, on a **fixed**
   loopback port (`DBVIEW_INTERNAL_PORT`, default `43117`) so followers can
   forward to it without any cross-worker port publication.
3. Every other worker runs its `NodeSupervisor` in **follower mode**
   (`start_follower()`): it never spawns or restarts the child, only tracks
   the shared child's health by polling the fixed port, so its own proxy
   503s cleanly until the leader's child answers.
4. All workers derive the **same** gateway secret (see
   [Security](security.md#the-shared-gateway-secret)), so follower-forwarded
   identity headers pass the single child's `timingSafeEqual` check.
5. On `shutdown()`, the leader releases the advisory lock by closing the held
   connection, letting another worker win it on the next boot.

The lock key is a distinct 64-bit constant (`0x4462764368696C64`, ASCII
`"DbvChild"`), namespaced away from the `auth` plugin's schema-init lock and
the `honeypot` plugin's listener-leadership lock — the same advisory-lock
primitive, three independent keys.

**Degrades open**: if Postgres is disabled or unreachable, the caller assumes
leadership unconditionally (`degraded=True`) — this preserves the
pre-existing one-child-per-worker behavior for single-worker/dev deployments
rather than failing to boot.

## Node child lifecycle (`supervisor/`)

`NodeSupervisor` owns the whole child lifecycle:

- Allocates a loopback port (or honours `DBVIEW_INTERNAL_PORT` / the pinned
  leadership default).
- Builds the child environment: prefix-passthrough (`DBVIEW_*`, `OLLAMA_*`,
  `OPENAI_*`, `ANTHROPIC_*`, `OTEL_*`, `LOG_*`, `NODE_*`, `APP_VERSION`) plus
  the plugin-owned gateway contract.
- Spawns `node dist/main.js` (prod) or `pnpm dev` (dev) via the **argv** form
  of `asyncio`'s subprocess API — no shell, no string interpolation.
- Drains stdout/stderr line by line into the host logger.
- Gates readiness on `GET /api/health` with a bounded timeout
  (`DBVIEW_STARTUP_TIMEOUT_S`), detecting a premature child exit instead of
  polling a dead process.
- Restarts on unexpected exit with capped exponential backoff, up to
  `DBVIEW_RESTART_MAX_ATTEMPTS` (0 = unlimited).
- Stops via SIGTERM with a grace period, escalating to a **process-group**
  SIGKILL (pnpm spawns turbo + Nest children that a bare parent SIGKILL would
  orphan).

## Core reuse

| Capability | Core seam |
|---|---|
| Identity chokepoint | `plugins.auth.dependencies.get_current_user` |
| Effective-admin / tab RBAC | `plugins.auth.rbac.service` |
| Identity-derived tenancy | `core.context.resolve_plugin_tenant_key` |
| Storage config (for leadership) | `core.config.get_storage_config` |
| Structured logging | `core.observability.logging.get_logger` |
| Plugin contract | `core.plugins.RouterPlugin` |

## Extension points

- **UI tab**: a single surface, `get_ui_tabs() → [{"id": "dbview", "label":
  "DBView"}]` — the literal id keys the central Access Control matrix as
  `(dbview, dbview)`.
- **SPA mount**: `get_static_assets_path()` serves `dbview/apps/web/dist`,
  mounted at `/dbview` (and `/plugins/dbview/static`) when built; when the
  bundle is absent it is not mounted (a self-diagnosing placeholder is applied
  centrally by the framework's app-setup middleware).
