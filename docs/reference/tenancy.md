# Multi-tenancy

dbview's tenant boundary is **identity-derived** and confines connection
sharing — never a client-supplied header, and never trusted by the upstream
without the host proxy having resolved it first.

## How the tenant key is resolved

- The host proxy resolves the scope key through the framework seam,
  `core.context.resolve_plugin_tenant_key("dbview", "shared")`
  ([`identity.py`](../reference/architecture.md)), which honours the
  plugin's declared tenancy mode **and** any runtime admin override — it never
  reads a request header.
- That key is embedded as `tenantKey` inside the signed
  `x-dbview-gateway-user` header on every authenticated, tab-permitted
  request (see [Security & RBAC](security.md)).
- On the upstream side, the tenant key is persisted on the JIT-mirrored user
  row and compared for every non-owner visibility check.

## Declared mode

The manifest declares `tenancy: shared` — a team collaborates on the same
connections. Because the scope key is resolved through the seam, an
administrator can flip the mode to `personal` at runtime (one tenant per
user) with no code change; every subsequent gateway header picks up the new
key.

| Mode | Effect |
|---|---|
| `shared` (default) | Connections scoped by the deployment-derived tenant (a team collaborates). |
| `personal` | 1 user = 1 tenant, regardless of how the deployment resolves tenancy elsewhere. |

## What the tenant key confines

**Connection sharing.** Every connection has an owner and a sharing mode
(`private`/`admins`/`all`/`users` — see
[Connections & sharing](../guide/connections.md)). The upstream's visibility
check (`ConnectionsService.canView`) always grants the owner access; for
anyone else it first requires the caller's `tenantKey` to match the
connection owner's mirrored `tenantKey` — only *then* does the sharing mode
apply. A connection shared as `all` on one tenant is still invisible to a
caller resolving to a different tenant.

!!! note "Standalone (non-gateway) dbview has no tenant boundary"
    The upstream's same-tenant check is a no-op (`sameTenant` returns `true`
    unconditionally) whenever gateway mode is off — i.e. for a bare,
    non-plugin deployment of dbview with local login. Under this plugin's
    intended integration, gateway mode is always on, so the check is always
    live.

## Background / unauthenticated callers

`resolve_plugin_tenant_key` degrades safely to the session/default tenant
(`get_tenant_or_default()`) when no user is bound to the request context —
this only matters for the rare unauthenticated forward (an anonymous request
to a `@Public()` upstream endpoint), since dbview has no background
tasks of its own; the request/response proxy is the entire runtime surface.

## What is *not* tenant-scoped

- **The Node child process itself** — one leader-elected process serves the
  whole deployment, across every tenant. Tenancy is enforced at the
  application/data layer (connection ownership + sharing), not by process
  isolation.
- **Metrics and health** — `/metrics`, `/health*` are deployment-wide, not
  per-tenant.

!!! warning "A mode change does not migrate data"
    Switching `shared` ↔ `personal` at runtime changes which scope key new
    requests carry; it does not move previously mirrored users or reassign
    existing connections between tenant keys. Plan mode changes deliberately.
