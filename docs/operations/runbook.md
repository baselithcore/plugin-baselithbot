# Runbook & troubleshooting

Operational notes for running dbview in production, especially with more than
one backend worker.

## Install / upgrade

```bash
cd plugins/dbview/dbview
pnpm install && pnpm -r build
VITE_API_BASE_URL=/api/dbview VITE_BASE_PATH=/dbview/ VITE_AUTH_MODE=gateway \
  pnpm --filter @dbview/web build

# Restart the backend — the proxy router and the SPA mount during
# create_app() (NOT hot-reloadable)
```

!!! danger "Restart after any install / rebuild"
    The proxy router and the SPA mount happen once at app startup. A running
    server will not pick up a rebuilt web bundle, nor a first-time build,
    until it is restarted. "Done" means `GET /dbview/` returns **200**.

## Health checks

```bash
curl -s -o /dev/null -w '%{http_code}' http://<host>:8000/dbview/          # → 200
curl -s -o /dev/null -w '%{http_code}' http://<host>:8000/api/dbview/health  # → 200
```

Prometheus metrics from the upstream (`dbview_*` — request latency/errors,
LLM calls, query executions, introspection failures, auth events) are exposed
at `/api/dbview/metrics`, gated admin/API-key.

## Connection Not Found Bug

**Symptom**: a connection created successfully immediately shows *"Could not
load schema — Connection `<id>` not found"* on the very next request.

**Root cause**: the embedded dbview app is single-instance — its state
(connections, mirrored users, sessions, engine pools) lives in per-process
in-memory maps. Under `WEB_CONCURRENCY>1`, every uvicorn worker used to spawn
its **own** Node child on its **own** ephemeral port. Requests round-robin
across workers, so a connection created via the child spawned by worker A was
invisible to the child spawned by worker B.

**Fix**: exactly one worker is elected leader (Postgres advisory lock —
`pg_try_advisory_lock`) and owns the single Node child, spawned on a **fixed**
loopback port (`DBVIEW_INTERNAL_PORT`, default `43117`). Every other worker's
proxy runs in *follower* mode and forwards to that same port instead of
spawning its own child. See [Architecture → Multi-worker leadership](../reference/architecture.md#multi-worker-leadership).

**If you still see this symptom**, check:

| Check | How |
|---|---|
| Is Postgres enabled? | Leadership degrades to *one child per worker* (the old, broken behaviour) whenever Postgres is disabled or unreachable — this is by design for single-worker/dev, but wrong for a multi-worker prod deployment. Confirm `POSTGRES_ENABLED=true` and the connection string is reachable from every worker. |
| Did every worker resolve the same port? | Confirm no per-worker `DBVIEW_INTERNAL_PORT` override diverges; the default is pinned automatically once leadership is coordinated. |
| Did every worker derive the same gateway secret? | If `DBVIEW_GATEWAY_SECRET` is set, it must be **identical** across every worker process (it should be — it's inherited from the shared environment). If unset, it's derived from `DBVIEW_SECRET`, which must equally be identical everywhere. A mismatch here doesn't cause "not found" — it causes 401s from followers, a related but distinct symptom (see below). |

## "401 on every follower-forwarded request"

Distinct from the symptom above: if leadership elects correctly but
`DBVIEW_SECRET` (or an explicit `DBVIEW_GATEWAY_SECRET`) differs between
workers — for example, one worker's environment was loaded from a stale
`.env` — the leader-owned child's `timingSafeEqual` check rejects
follower-signed identity headers. Fix: ensure `DBVIEW_SECRET` (and, if set,
`DBVIEW_GATEWAY_SECRET`) is byte-identical across every worker's environment.

## Multi-worker deployment checklist

- [ ] `POSTGRES_ENABLED=true` and reachable from every worker — required for
      coordinated leadership; without it you get one Node child **per**
      worker again (dev-only behaviour).
- [ ] `DBVIEW_SECRET` identical across every worker process.
- [ ] `DBVIEW_GATEWAY_SECRET` unset (let it derive) **or** identical across
      every worker if set explicitly.
- [ ] No per-worker `DBVIEW_INTERNAL_PORT` override that diverges from the
      others.
- [ ] Node ≥ 20 and the prod bundle (`apps/api/dist/main.js`) present on
      **every** host that might win leadership — not just the one that
      happened to win it in dev.

## Common issues

| Symptom | Fix |
|---|---|
| `/dbview/` → 404 or opaque error | Backend started before the plugin/`ui/dist` existed → restart. If `ui/dist` is missing, the framework mounts a self-diagnosing placeholder → build it, then restart. |
| Plugin fails to activate: `DBVIEW_SECRET ... required` | Set `DBVIEW_SECRET` (≥ 16 chars) in the host environment before boot. |
| `NodeNotAvailableError` at startup | `node` (or, in dev mode, `pnpm`) is missing from `PATH` on the host that's trying to become leader. |
| `StartupTimeoutError` | The Node child never answered `/api/health` within `DBVIEW_STARTUP_TIMEOUT_S`. Check supervisor logs (`[dbview-node] ...` lines) for the underlying failure — commonly a missing prod bundle (`pnpm -r build` not run) or a port collision. |
| Connection created on one request, "not found" on the next | See [Connection Not Found Bug](#connection-not-found-bug) above. |
| `403 dbview_tab_denied` | The caller's central RBAC policy for `(dbview, dbview)` denies the tab — check the Access Control matrix, not this plugin. |
| Local login doesn't work | Expected under gateway mode — identities are owned by the central `auth` plugin; local login is intentionally inert. |

## Restart / recovery behaviour

- The supervisor restarts a crashed leader-owned child automatically, with
  capped exponential backoff, up to `DBVIEW_RESTART_MAX_ATTEMPTS` (0 =
  unlimited).
- A follower never restarts anything — it only tracks the leader-owned
  child's health and 503s while it's down.
- If the **leader worker itself** exits, its held advisory lock is released
  (the connection closes), and another worker wins leadership on its next
  `acquire_dbview_leadership()` call — but that only happens at that worker's
  own `initialize()`, i.e. on its own restart. A full backend restart is the
  reliable way to re-elect after losing the leader worker.

## Backstage / TechDocs

This documentation is published to the developer portal automatically: the
core exporter emits a `backstage.io/techdocs-ref` on dbview's Component
because this plugin ships an `mkdocs.yml`. The portal's TechDocs generator
builds these pages on demand; no static site is committed. See
[API](../reference/api.md) for a caveat specific to this plugin's Backstage
**API** entity (its Definition card falls back to the full framework spec).
