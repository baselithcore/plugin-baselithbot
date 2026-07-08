# API

The host mounts one router at **`/api/dbview`** — but it is a deliberate
**catch-all reverse proxy** (`""` and `/{full_path:path}`, both
`include_in_schema=False`), not a set of individually declared FastAPI routes.
Every request under that prefix is forwarded to the vendored NestJS API,
re-rooted from its native `/api` namespace:

```
browser  →  /api/dbview/schema/<id>
                       │ strip "/api/dbview", prepend "/api"
                       ▼
upstream →  /api/schema/<id>
```

!!! note "Backstage API entity: definition falls back to the full spec"
    The core exporter normally inlines an OpenAPI definition scoped to a
    plugin's own routes. Because dbview's proxy routes are intentionally
    excluded from the host's OpenAPI document (a catch-all forwarder has no
    per-endpoint schema to declare), there is nothing to slice — the
    Component's API entity still exists (`dbview-api`), but its
    **Definition** card falls back to `{$text: <host>/openapi.json}`, the
    framework's **full, unscoped** spec. The route map below — sourced from
    the upstream project's own reference — is the authoritative contract for
    this plugin.

## Route map

All paths below are relative to `/api/dbview`. Health and auth-config are
public; everything else requires the caller to be authenticated through the
host proxy (which forwards trusted identity) or, for direct upstream/service
access, `X-API-Key: <DBVIEW_API_KEY>`.

| Group | Paths | Auth | Notes |
|---|---|---|---|
| Health | `/health`, `/health/live`, `/health/ready` | public | `ready` is a deep probe (data dir, secrets). |
| Auth | `/auth/config`, `/auth/login`, `/auth/refresh`, `/auth/logout` | public | Under gateway mode, local login/refresh are routable but functionally inert — JIT-mirrored users carry an unverifiable password sentinel. |
| Auth | `/auth/me` | authenticated | Current (gateway-forwarded) identity. |
| Users | `/auth/users`, `/auth/users/:id` | admin | Invite-only CRUD — irrelevant under gateway mode (users are JIT-mirrored, never invited locally). |
| Connections | `/connections/*` | authenticated | CRUD, reachability test, dump upload. Visibility/ownership enforced per [Connections & sharing](../guide/connections.md). |
| Schema | `/schema/:connectionId?refresh=1` | authenticated | Returns the `UnifiedSchema` for the connection. |
| NL2SQL | `/nl2sql`, `/nl2sql/ask` | authenticated | Rate-limited 20/60s/IP upstream. |
| Query | `/query/execute`, `/query/sample` | authenticated | Safety validator runs again on input. |
| History | `/history`, `/history/:id`, `/history/:id/favorite` | authenticated | Bulk clear is admin. |
| LLM | `/llm/ollama/models` | authenticated | Proxies `GET {ollamaBaseUrl}/tags`. |
| Metrics | `/metrics` | admin / API key | Prometheus exposition (`dbview_*`). |

## Identity forwarding

For an authenticated caller, the proxy attaches the identity as trusted
gateway headers before forwarding — never the raw bearer token. See
[Security & RBAC](security.md) for the exact header contract.

## Response shape

Errors from the upstream propagate through unchanged: `{ code, message }` with
an appropriate HTTP status. When the upstream is unreachable or unhealthy the
proxy itself returns a structured `502`/`503` (`dbview_upstream_error` /
`dbview_upstream_down`) rather than a raw connection failure.

## Streaming

The proxy is streaming end-to-end in both directions (`httpx.AsyncClient.stream` and
`StreamingResponse`), so large schema-introspection payloads are never buffered
twice.
