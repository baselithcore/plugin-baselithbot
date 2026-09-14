# Configuration

The plugin composes the Node child's environment from three layers: the host
process environment (prefix-passthrough), plugin-level overrides passed to
`initialize()` (`mode`/`host`/`port` from `configs/plugins.yaml`), and a small
set of values the plugin computes itself (the gateway contract, a safe JWT
fallback, the data directory). Everything under the passthrough prefixes
(`DBVIEW_`, `OLLAMA_`, `OPENAI_`, `ANTHROPIC_`, `OTEL_`, `LOG_`, `NODE_`,
`APP_VERSION`) reaches the child verbatim; nothing else does — the child never
sees unrelated host secrets.

## Mandatory

| Env | Notes |
|---|---|
| `DBVIEW_SECRET` | AES-256-GCM key for stored connection strings, **≥ 16 chars**. Must stay stable across restarts — rotating it silently orphans every saved connection. The plugin refuses to activate without it. |

## Plugin / host-level

| Env | Default | Notes |
|---|---|---|
| `DBVIEW_JWT_SECRET` | auto-generated per boot | Local JWT signing key, ≥ 32 chars. Only consumed by the (disabled under gateway mode) local login flow — a per-boot value is safe. Set explicitly only for a standalone deployment. |
| `DBVIEW_GATEWAY_SECRET` | derived from `DBVIEW_SECRET` (HMAC-SHA256) | The secret **every** worker signs forwarded identity with, and the single Node child validates against. An explicit value (already shared across every forked worker via the environment) wins verbatim; otherwise it's derived deterministically so every worker agrees without extra config. See [Security](security.md). |
| `DBVIEW_DATA_DIR` | `plugins/dbview/var/data` | Runtime data directory (users/sessions/connections/history JSON stores). Kept out of the vendored source tree. |
| `DBVIEW_PLUGIN_MODE` | `prod` | `prod` runs `node dist/main.js`; `dev` runs `pnpm dev` (turbo). |
| `DBVIEW_INTERNAL_HOST` | `127.0.0.1`, or `0.0.0.0` in cross-pod mode | Bind host for the embedded Node API. Loopback by default; cross-pod rendezvous widens it so peer replicas can reach the single child. An explicit value always wins. |
| `DBVIEW_ADVERTISE_HOST` | `POD_IP`, else unset | The host a **peer replica** should dial to reach this pod's Node child. Set it to a routable address (or leave the chart's `POD_IP` to it). Unset — or loopback — keeps the plugin in single-pod mode. Needs Redis as well: see [Architecture → Cross-pod rendezvous](architecture.md#cross-pod-rendezvous). |
| `DBVIEW_INTERNAL_PORT` | `43117` under coordinated leadership; ephemeral otherwise | Fixed rendezvous port so followers know where the leader-owned child listens. An explicit value always wins in both modes. |
| `DBVIEW_STARTUP_TIMEOUT_S` | `90` | Max seconds the supervisor waits for `/api/health` before failing activation. |
| `DBVIEW_HEALTH_INTERVAL_S` | `0.5` | Delay between health probes, both during startup and the keep-alive loop. |
| `DBVIEW_SHUTDOWN_GRACE_S` | `10` | Seconds between SIGTERM and the process-group SIGKILL on stop. |
| `DBVIEW_RESTART_MAX_ATTEMPTS` | `0` (unlimited) | Cap on consecutive child restarts after an unexpected exit. |
| `DBVIEW_PORT_RELEASE_TIMEOUT_S` | `15` | How long a predecessor may still hold the upstream port when a child is about to be spawned. A leadership handover releases the advisory lock the instant the old leader worker dies, while its child needs a moment to answer the parent-death `SIGTERM`; past this window the port counts as held by a foreign process and the spawn is refused with a `PortUnavailableError` instead of an endless `EADDRINUSE` restart loop. |
| `DBVIEW_SIGTERM_SETTLE_S` | `5` | Grace window used to classify a child killed by `SIGTERM`: the supervisor waits this long for the host's own shutdown before treating the exit as a crash worth restarting. `0` disables the wait. |
| `DBVIEW_API_KEY` | — | Optional upstream service key for direct loopback access (Prometheus scrape, CI automation). Central platform API keys (`bsk_…`) work through the proxy regardless. |

## Passed through to the vendored app

These are consumed by the NestJS API itself (not by the plugin), forwarded
verbatim because they match a passthrough prefix. Most only matter for
provider selection or a **standalone** (non-gateway) deployment.

| Env | Default | Notes |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434/api` | Local NL→Query provider endpoint. |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | — / `gpt-4o-mini` | Optional remote provider. |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | — / `claude-sonnet-4-6` | Optional remote provider. |
| `DBVIEW_NL2SQL_MAX_RETRIES` | `2` (clamped 0–4) | Retry budget for the NL→Query safety/parse feedback loop. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP collector base URL. Tracing is a no-op when unset. |
| `DBVIEW_JWT_ACCESS_TTL` / `DBVIEW_JWT_REFRESH_TTL` | `900` / `2592000` (seconds) | Local JWT lifetimes — only relevant when gateway auth is off. |
| `DBVIEW_ADMIN_EMAIL` / `DBVIEW_ADMIN_PASSWORD` | `admin@dbview.local` / random | Bootstrap admin for **standalone** (non-gateway) deployments only; under gateway mode local admin bootstrap is skipped entirely (identities are owned by the central IdP). |
| `DBVIEW_ALLOW_REGISTRATION` | `false` | Self-signup on the local login screen — irrelevant under gateway mode, where local login is inert. |

## Central LLM governance (auth console)

LLM routing follows the platform's per-plugin LLM policy, like every other
plugin: an operator pin for `dbview` set from the **auth console** overrides
the provider env above. The plugin declares two `llm_scopes` so the two
pipelines can be pinned independently:

| Scope | Pipeline | Model env it governs |
|---|---|---|
| `nl2sql` | NL→Query translation | `OLLAMA_MODEL_SQL/GRAPH/DOCUMENT/VECTOR/KEYVALUE/SEARCH/SAAS`, `OPENAI_MODEL`, `ANTHROPIC_MODEL` |
| `explain` | Explain / summarize | `OLLAMA_MODEL_EXPLAIN`, `OPENAI_MODEL_EXPLAIN`, `ANTHROPIC_MODEL_EXPLAIN` |

A scope with no pin of its own inherits the plugin's default pin; unpinned,
the child keeps the env-driven configuration above — zero behaviour change.
The pinned provider's **central credential/endpoint** (`OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `OLLAMA_BASE_URL`) also comes from central config; a
pinned model replaces that scope's default-model vars. What a pin never
touches: the per-request provider/model chosen in the Ask UI and per-user
stored (BYOK) keys — explicit caller choices remain a product feature.
Supported pins: `openai`, `anthropic`, `ollama` (the child bundles exactly
those SDKs; a `huggingface` pin is ignored).

**Live propagation (no restart).** The pin reaches the running Node child two
ways, live-first: the proxy resolves the current pin **per request** and
forwards it as trusted `x-dbview-gov-*` headers (stripped inbound, so a client
can't spoof them), which the engine prefers over its spawn env — so a re-pin
takes effect within the policy-snapshot TTL with **no** respawn (hard-refresh
the SPA, or wait for its 60 s governance cache, to see the controls lock). The
spawn-time env injection remains as a fallback for requests that don't traverse
the proxy and so a crash-restart still picks up the current pin.

## Runtime prerequisites

- Node.js ≥ 20 on `PATH` (mandatory; ≥ 22.13 only if pnpm is upgraded to
  11.x).
- pnpm, auto-provisioned as `10.15.0` via the vendored `packageManager`
  field — needed for `DBVIEW_PLUGIN_MODE=dev` and for builds. Do not pin pnpm
  11.x while on Node 20 (pnpm 11 requires Node ≥ 22.13).
- `apps/api/dist/main.js` built once (`pnpm install && pnpm -r build` inside
  `plugins/dbview/dbview`) — prod mode refuses to start otherwise.
- `apps/web/dist/index.html` built once for the SPA (see
  [Getting started](../getting-started.md#build-the-stack-operators-only)).

## Example `plugins.yaml` block

```yaml
dbview:
  mode: prod
  host: 127.0.0.1
  # port: 43117   # only if the default rendezvous port collides on this host
```

`mode`/`host`/`port` are the only knobs read from the plugin-level YAML block;
everything else is environment-driven.
