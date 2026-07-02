# baselithcontrol

> Centralized control-plane dashboard for BaselithCore — discover, monitor, and
> govern every loaded plugin from one place.

`baselithcontrol` is the framework's command bridge. It dynamically discovers
every other plugin through the core registry (zero per-plugin hardcoding),
streams their health in real time over SSE, aggregates each plugin's own UI, and
exposes governed lifecycle control (enable / disable / reload) behind RBAC, an
optional autonomy gate, and an append-only audit trail. Around that core it
bundles a System Console (CLI bridge), a live log viewer, per-plugin LLM cost
accounting with a durable ledger, resource observability, and a news ticker.

The manifest declares `system: true`: the plugin is platform infrastructure, so
its tabs are admin-only in the central Access Control matrix and hidden from
ordinary users' navigation.

Full design rationale: [docs/architecture/baselithcontrol.md](../../docs/architecture/baselithcontrol.md).

## Highlights

- **Dynamic discovery** — reads the live `PluginRegistry`; new plugins appear
  automatically, grouped and searchable. No configuration per plugin.
- **Normalized status** — one `healthy | degraded | down | disabled | unknown`
  vocabulary with colorblind-safe shapes, latency, and "last healthy" time.
- **Zero-code widgets** — a plugin opts into a rich status tile by adding a
  `control.widget` block to its manifest (no frontend code). See below.
- **Live stream** — `GET /stream` (SSE) bridges the core `EventBus`
  (`plugin.*` / `system.*`) to the dashboard. Under enforced auth, SSE
  authenticates via the `?token=` query credential (EventSource cannot set
  headers) or the same-origin session cookie.
- **Governed control** — enable/disable/reload behind the `admin` role, an
  optional autonomy approval gate, and an audit log.
- **System Console** — the `baselith` CLI surfaced in the dashboard:
  diagnostics (`doctor` / `verify` / `info` / `config`), infra status +
  destructive ops (cache clear, db reset), and streamed dev-tool jobs
  (test / lint / docs). Admin-only, reads included (topology disclosure).
- **Live log viewer** — an in-memory ring capture of all application logs with
  level/plugin/text filters (admin-only tab).
- **LLM cost accounting** — real per-plugin token usage attributed at the
  request boundary, priced from the core pricing table, persisted per-tenant to
  Postgres (multi-worker-safe additive ledger; degrades to in-memory and
  re-probes the DB periodically).
- **Resource observability** — psutil gauges (CPU/RAM/net/uptime) plus a
  pure-ASGI per-plugin request meter (count/latency/errors).
- **News ticker** — merged RSS/Atom headlines on the home view. Every fetch is
  SSRF-guarded with per-hop redirect re-validation and connection pinning, and
  bodies are streamed under a hard size cap.
- **Sandboxed UI embed** — each plugin's SPA renders in an origin-locked iframe;
  A2UI status blueprints render through a whitelist-safe renderer.
- **i18n** — English + Italian, complete, frontend **and** backend (API
  messages localize via `Accept-Language`).

## API (prefix `/api/baselithcontrol`)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/inventory` | authenticated | Plugin catalog (active + discovered) |
| GET | `/ui-registry` | authenticated | Embeddable UI surfaces |
| GET | `/status` | authenticated | Aggregated health + system metrics |
| GET | `/overview` | authenticated | Head-band summary counts |
| GET | `/status/{plugin}` | authenticated | Normalized per-plugin status |
| GET | `/widgets` | authenticated | Declarative status widgets |
| GET | `/stream` | authenticated | SSE live events (`?token=` under enforced auth) |
| GET | `/me` | session | Caller identity + capabilities |
| GET | `/resources` | authenticated | System gauges (CPU/RAM/net/uptime) |
| GET | `/resources/plugins` | authenticated | Per-plugin request meter |
| GET | `/resources/history` | authenticated | Retained gauge series |
| GET | `/timeline` | authenticated | Request-volume trend + lifecycle feed |
| GET | `/news` | authenticated | Merged news-ticker snapshot |
| GET | `/cost/usage` | authenticated | Per-plugin LLM spend (own tenant; admins: global) |
| GET | `/pricing` | authenticated | LLM list-price reference table |
| POST | `/actions/{plugin}/{op}` | **admin** | enable / disable / reload (audited) |
| POST | `/config/{plugin}` | **admin** | Persist `enabled` in plugins.yaml (audited) |
| GET | `/audit` | **admin** | Recent governed-action records |
| GET | `/logs` | **admin** | Filtered tail of captured application logs |
| GET | `/cli/doctor` · `/cli/verify` · `/cli/info` · `/cli/config` | **admin** | Diagnostics (CLI bridge) |
| GET | `/cli/infra/db` · `/cli/infra/cache` · `/cli/infra/queue` | **admin** | Infra status |
| POST | `/cli/infra/cache/clear` · `/cli/infra/db/reset` | **admin** | Destructive infra ops (audited) |
| POST | `/cli/devtools/{test\|lint\|docs}` | **admin** | Start a streamed dev-tool job (audited) |
| GET | `/cli/devtools/jobs[/{id}]` | **admin** | List / poll dev-tool jobs |

Reads pass through when the `auth` plugin runs with `auth_required=false`; they
require a validated session once auth is enforced (bearer, `?token=`, API key,
or refresh cookie — same semantics as the central guard). Error messages and
action results localize via `Accept-Language` (`en` default, `it`).

### Multi-worker note

Lifecycle actions (`/actions/{plugin}/{op}`) and dev-tool jobs mutate **the
worker that serves the request**; with `WEB_CONCURRENCY>1` other workers
converge on restart, or durably via `POST /config/{plugin}` (which persists to
`plugins.yaml`). The LLM cost ledger is multi-worker-safe by design (additive
Postgres UPSERT).

## Configuration

Set in `configs/plugins.yaml` under `baselithcontrol:` or via env
(`BASELITHCONTROL_*`). The yaml block is published at plugin initialize and
governs request-time behaviour; env vars override.

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | Load the plugin |
| `require_admin` | `true` | Require the `admin` role for mutations. Set `false` to allow any authenticated user (trusted single-operator setups) |
| `gate_level` | `open` | Autonomy gate on destructive actions: `open` (RBAC only) / `semi` / `strict` |
| `approval_timeout_seconds` | `60` | Human-approval wait before failing closed (`semi`/`strict`) |
| `sse_heartbeat_seconds` | `20` | SSE idle keepalive interval |
| `audit_max_events` | `500` | In-memory audit ring-buffer capacity |
| `volume_interval_seconds` | `5` | Request-volume sampling cadence |
| `volume_capacity` | `720` | Volume ring capacity (≈1 h at 5 s) |
| `lifecycle_capacity` | `200` | Retained lifecycle-timeline capacity |
| `news_enabled` | `true` | Fetch + render the news ticker |
| `news_feeds` | curated set | Override feed list (`{url, source, category, lang}`) |
| `news_cache_ttl_seconds` | `600` | Snapshot cache TTL |
| `news_max_items` | `40` | Max merged headlines |
| `news_fetch_timeout_seconds` | `6` | Per-feed HTTP timeout |
| `news_allow_internal` | `false` | Skip SSRF checks (dev fixtures only) |
| `logs_enabled` | `true` | Capture application logs for the viewer |
| `log_buffer_capacity` | `2000` | Log ring capacity |
| `persist_costs` | `true` | Durable Postgres LLM cost ledger (degrades to memory) |
| `cost_flush_seconds` | `15` | Cost delta flush cadence |

## Opting a plugin into a status widget

Add an optional `control` block to that plugin's `manifest.yaml`. The endpoint
must be a **relative, same-origin path** (the dashboard never fetches external
URLs server-side; the browser fetches it directly with the session cookie):

```yaml
control:
  group: Operations          # dashboard grouping (falls back to category)
  icon: gauge                # optional lucide icon name
  instance: prod             # optional multi-env label
  widget:
    title: Twin queue
    endpoint: /api/baselithtwin/stats
    display: list            # list | block
    fields:
      - { path: queue.depth, label: Queue, format: number,
          highlight: { gte: 50, tone: warning } }
      - { path: replies.today, label: Replies, format: number }
```

`format` ∈ `number | percent | duration | bytes | text`;
`highlight` ∈ `{ gte | lte | eq, tone }` for threshold coloring.

## Development

```bash
# Backend tests (mock registry, no live infra)
python -m pytest tests/plugins/baselithcontrol/ -v

# Frontend (React 19 + Vite + Tailwind 4)
cd plugins/baselithcontrol/ui
npm install
npm run dev      # http://localhost:5181 (proxies /api/baselithcontrol and /api/auth to :8000)
npm run build    # → ui/dist/ (ships in the wheel; ui/src does not)
```

Only `ui/dist/**` is packaged; the TypeScript source and `node_modules` are
excluded. Rebuild after forking the UI.
