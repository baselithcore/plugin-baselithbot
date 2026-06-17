# baselithcontrol

> Centralized control-plane dashboard for BaselithCore — discover, monitor, and
> govern every loaded plugin from one place.

`baselithcontrol` is the framework's command bridge. It dynamically discovers
every other plugin through the core registry (zero per-plugin hardcoding),
streams their health in real time over SSE, aggregates each plugin's own UI, and
exposes governed lifecycle control (enable / disable / reload) behind RBAC, an
optional autonomy gate, and an append-only audit trail.

Full design rationale: [docs/architecture/baselithcontrol.md](../../docs/architecture/baselithcontrol.md).

## Highlights

- **Dynamic discovery** — reads the live `PluginRegistry`; new plugins appear
  automatically, grouped and searchable. No configuration per plugin.
- **Normalized status** — one `healthy | degraded | down | disabled | unknown`
  vocabulary with colorblind-safe shapes, latency, and "last healthy" time.
- **Zero-code widgets** — a plugin opts into a rich status tile by adding a
  `control.widget` block to its manifest (no frontend code). See below.
- **Live stream** — `GET /stream` (SSE) bridges the core `EventBus`
  (`plugin.*` / `system.*`) to the dashboard.
- **Governed control** — enable/disable/reload behind the `admin` role, an
  optional autonomy approval gate, and an audit log.
- **Sandboxed UI embed** — each plugin's SPA renders in an origin-locked iframe;
  A2UI status blueprints render through a whitelist-safe renderer.
- **i18n** — English + Italian, complete, with a language switcher.

## API (prefix `/api/baselithcontrol`)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/inventory` | authenticated | Plugin catalog (active + discovered) |
| GET | `/ui-registry` | authenticated | Embeddable UI surfaces |
| GET | `/status` | authenticated | Aggregated health + system metrics |
| GET | `/overview` | authenticated | Head-band summary counts |
| GET | `/status/{plugin}` | authenticated | Normalized per-plugin status |
| GET | `/widgets` | authenticated | Declarative status widgets |
| GET | `/stream` | authenticated | SSE live events |
| GET | `/me` | session | Caller identity + capabilities |
| POST | `/actions/{plugin}/{op}` | **admin** | enable / disable / reload (audited) |
| GET | `/audit` | **admin** | Recent governed-action records |

Reads pass through when the `auth` plugin runs with `auth_required=false`; they
require a session once auth is enforced.

## Configuration

Set in `configs/plugins.yaml` under `baselithcontrol:` or via env
(`BASELITHCONTROL_*`):

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | Load the plugin |
| `require_admin` | `true` | Require the `admin` role for mutations. Set `false` to allow any authenticated user (trusted single-operator setups) |
| `gate_level` | `open` | Autonomy gate on destructive actions: `open` (RBAC only) / `semi` / `strict` |
| `sse_heartbeat_seconds` | `20` | SSE idle keepalive interval |
| `audit_max_events` | `500` | In-memory audit ring-buffer capacity |

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
python -m pytest tests/unit/plugins/baselithcontrol/ -v

# Frontend (React 19 + Vite + Tailwind 4)
cd plugins/baselithcontrol/ui
npm install
npm run dev      # http://localhost:5181 (proxies the API to :8000)
npm run build    # → ui/dist/ (ships in the wheel; ui/src does not)
```

Only `ui/dist/**` is packaged; the TypeScript source and `node_modules` are
excluded. Rebuild after forking the UI.
