# Security & RBAC

dbview never hand-rolls authentication. It **consumes the central `auth`
plugin** through a trusted-gateway bridge: the host proxy authenticates the
caller once, then forwards a signed identity assertion to the vendored NestJS
API, which trusts it and disables its own local login.

## The chokepoint

Every proxied request resolves the caller through the shared
`plugins.auth.dependencies.get_current_user` dependency (Bearer token,
central API key, or refresh cookie — whatever the platform accepts). If the
`auth` plugin is not importable in a given deployment, the proxy falls back to
treating every caller as anonymous — the upstream's own `@Public()` guards
still apply, so this **degrades closed** (nothing but health/config becomes
reachable) rather than silently trusting an unauthenticated caller.

## Central per-tab policy

Authenticated requests are checked against the central Access Control matrix
for `(dbview, dbview)` — the plugin's single UI surface — before anything is
forwarded. This mirrors `require_tab` semantics: **default-allow**, and it
**fails open** on an RBAC-store outage (tab gating is visibility policy, not
privilege elevation, matching the platform's `PluginAccessMiddleware` stance).
A denial returns `403 dbview_tab_denied` without ever reaching the Node child.

## The gateway identity header

For an authenticated, tab-permitted caller, the proxy mints and attaches two
headers before forwarding:

| Header | Contents |
|---|---|
| `x-dbview-gateway-user` | base64url JSON: `{id, email, displayName, role, tenantKey}` |
| `x-dbview-gateway-secret` | the shared per-deployment secret (see below) |

`email` falls back to the central directory profile, then token hints, then a
deterministic placeholder (`<user_id>@users.central.local`) if none is
available — the upstream's schema requires a syntactically valid address.
`role` is `"admin"` only for an **effective** admin (see below); everyone else
is `"user"`.

**Inbound `x-dbview-gateway-*` headers are always stripped** from the
client-facing request before it is inspected or forwarded — a caller can never
smuggle a spoofed identity through the proxy; only the proxy itself can mint
these headers.

## The shared gateway secret

The upstream's `GatewayAuthGuard` accepts a request only if
`x-dbview-gateway-secret` matches its own `DBVIEW_GATEWAY_SECRET`, compared
with `crypto.timingSafeEqual`. Under a multi-worker deployment only the
leader worker spawns the Node child, but **every** worker's proxy must sign
with the *same* value — a per-worker random secret would make
follower-forwarded identity fail the child's check with 401. Resolution
order:

1. An operator-set `DBVIEW_GATEWAY_SECRET` (shared via the process
   environment across every forked worker) wins verbatim.
2. Otherwise it is derived deterministically via `HMAC-SHA256(DBVIEW_SECRET,
   "dbview-gateway-secret-v1")` — the same value on every worker without any
   extra configuration, and not derivable by another local process that
   doesn't already hold `DBVIEW_SECRET`.

## JIT identity mirroring

On the upstream side, a gateway-authenticated identity is mirrored into the
local users store on first sight (and re-synced on drift — email, role,
display name, tenant key) so ownership foreign keys (`connections.ownerId`,
`history.ownerId`) resolve. Mirrored rows carry an **unverifiable password
sentinel**, so they can never be used to log in locally — identity is owned
by the central IdP, never duplicated as a real credential.

## Admin is an effective privilege

The `role: "admin"` claim is derived from
`plugins.auth.rbac.service.is_effective_admin` — wildcard-aware, so a user
granted full access via a custom RBAC role (not the literal `AuthRole.ADMIN`)
is still recognized as admin inside dbview. The verdict is cached for 30
seconds (the proxy sits on the hot path of every request and the RBAC store is
a database round-trip) and **falls back to the literal role check** if the
RBAC service is unreachable — an outage can only ever *demote* a wildcard-only
admin for the cache window, never elevate a non-admin.

## Secrets

- **`DBVIEW_SECRET`** (≥ 16 chars) — AES-256-GCM key for connection strings at
  rest. Mandatory; must stay stable across restarts.
- **`DBVIEW_GATEWAY_SECRET`** — see above; never logged, never returned by any
  endpoint.
- Connection strings are decrypted **in-memory only** at connect time; no
  endpoint ever echoes one back, encrypted or not.

## Service-to-service access

`DBVIEW_API_KEY`, when set, lets an operator or automation call the upstream
directly (`X-API-Key`) bypassing the gateway/JWT path entirely — the guard
attaches a synthetic admin principal. Central platform API keys (`bsk_…`)
instead flow through the normal proxy path like any other bearer credential.
