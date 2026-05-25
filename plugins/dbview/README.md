# dbview plugin

Hosts the upstream [dbview](https://github.com/giovanni-ippolito/dbview)
TypeScript/NestJS application — database visualisation + NL→Query
across 17 engines — as a BaselithCore plugin.

The full dbview monorepo lives byte-for-byte under [dbview/](dbview/);
the Python wrapper supervises the Node child process and proxies
traffic through a FastAPI reverse-proxy router.

## Architecture

```text
Browser
   │ /api/dbview/*                 /dbview/*
   ▼                                ▼
┌───────────────────────────┐  ┌────────────────────┐
│ FastAPI proxy router      │  │ Static SPA mount   │
│ (proxy_router.py)         │  │ (apps/web/dist/)   │
└─────────────┬─────────────┘  └────────────────────┘
              │ http://127.0.0.1:<port>/api/*
              ▼
┌───────────────────────────┐
│ NestJS + Fastify          │   ← supervised by supervisor.py
│ (apps/api/dist/main.js)   │
└───────────────────────────┘
```

* `plugin.py` — `DbviewPlugin(RouterPlugin)` entrypoint.
* `supervisor.py` — async Node child-process lifecycle (spawn / health
  gate / restart / SIGTERM→SIGKILL).
* `proxy_router.py` — streaming reverse proxy with hop-by-hop header
  stripping and `Set-Cookie Path=` rewriting for JWT refresh rotation.

## Build

The wheel ships the dbview source tree but does **not** bundle Node
dependencies (hundreds of MB) nor pre-built bundles. After install:

```bash
cd plugins/dbview/dbview
pnpm install
pnpm --filter @dbview/shared \
     --filter @dbview/sql-core \
     --filter @dbview/cypher-core \
     --filter @dbview/document-core \
     --filter @dbview/vector-core \
     --filter @dbview/keyvalue-core \
     --filter @dbview/search-core \
     build
pnpm --filter @dbview/api build
VITE_API_BASE_URL=/api/dbview VITE_BASE_PATH=/dbview/ \
  pnpm --filter @dbview/web build
```

In dev mode (`DBVIEW_PLUGIN_MODE=dev`) `pnpm dev` is invoked directly
and incremental builds run on file change — no separate build step
required, but pnpm and Node ≥ 20 must be on `PATH`.

## Environment

Mandatory:

* `DBVIEW_JWT_SECRET` — JWT signing key, ≥ 32 chars.
* `DBVIEW_SECRET` — AES-256-GCM key for stored connection strings,
  ≥ 16 chars.

Plugin-specific knobs:

* `DBVIEW_PLUGIN_MODE` — `prod` (default) or `dev`.
* `DBVIEW_INTERNAL_HOST` — bind host for the embedded API. Default
  `127.0.0.1`.
* `DBVIEW_INTERNAL_PORT` — bind port. Default: ephemeral allocation.
* `DBVIEW_STARTUP_TIMEOUT_S` — startup gate max wait. Default `90`.
* `DBVIEW_RESTART_MAX_ATTEMPTS` — `0` = unlimited.

Every other `DBVIEW_*`, `OLLAMA_*`, `OPENAI_*`, `ANTHROPIC_*`,
`OTEL_*`, `LOG_*`, `NODE_*`, `APP_VERSION` environment variable is
forwarded transparently to the child process — see
[dbview/.env.example](dbview/.env.example) for the full reference.

## Source-tree patches

Three host-aware patches were applied to the upstream UI. Each is
guarded by an environment variable whose default reproduces standalone
behaviour exactly — `cd plugins/dbview/dbview && pnpm build` without
the plugin envs produces a bundle byte-identical to upstream:

| File                                  | Patch                                                                  |
| ------------------------------------- | ---------------------------------------------------------------------- |
| `apps/web/src/lib/api.ts`             | `baseURL` reads `VITE_API_BASE_URL` (default `/api`).                  |
| `apps/web/src/lib/auth.ts`            | `fetch('/api/auth/…')` calls use the same env-driven base.             |
| `apps/web/vite.config.ts`             | `base` reads `VITE_BASE_PATH` (default `/`).                           |

The NestJS backend is **untouched**. The proxy router rewrites
`Set-Cookie Path=/api/auth → /api/dbview/api/auth` on the wire so the
refresh-cookie rotation flow keeps working behind the new prefix.

## Tests

```bash
python -m pytest plugins/dbview/tests/ --no-cov -v
```

19 unit tests cover the proxy router (header filtering, cookie path
rewriting, upstream-down 503, connect-failure 502, URL prefix
forwarding) and the supervisor configuration layer (env composition,
runtime-prerequisite detection, prod/dev command selection).

The Node child is not spawned in unit tests; the integration smoke
that actually boots NestJS lives separately and requires `node` +
the built bundles to be present.
