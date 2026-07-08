# dbview — Database Visualisation & NL→Query

dbview connects to a database, graph, document, vector, key-value, search or
SaaS data source; renders its schema as an interactive graph; and turns a
plain-English question into a **safe, validated, read-only query** you can run
with one click.

!!! tip "In one sentence"
    Point dbview at a data source, see its shape, ask a question in English,
    get back a query that has already been checked against the real schema and
    **cannot write** — then run it, export the result, and revisit it later
    from history.

## What it is

dbview is a self-contained TypeScript stack — a NestJS API and a React/Vite
SPA — vendored **verbatim** under `plugins/dbview/dbview/` and hosted as a
managed Node child process behind a FastAPI reverse proxy. A Python rewrite of
its 18 engine adapters and AST-level query safety would inevitably regress the
upstream project, so the plugin's job is purely **hosting and identity**: spawn
the child, gate it on health, proxy authenticated traffic to it, and bridge the
platform's identity into it.

## Architecture sketch

```
Browser
   │  GET/POST /api/dbview/...            GET /dbview/  (built SPA)
   ▼
Host FastAPI  (plugins/dbview/proxy_router.py)
   │  1. get_current_user() — central auth chokepoint
   │  2. central per-tab policy: (dbview, dbview)
   │  3. mint x-dbview-gateway-user + x-dbview-gateway-secret
   │  4. strip any inbound x-dbview-gateway-* header (anti-spoof)
   ▼
Gateway bridge (plugins/dbview/identity.py)
   │  AuthUser → {id, email, displayName, role, tenantKey}
   ▼
Leader-elected Node child   (plugins/dbview/leader.py + supervisor/)
   │  exactly ONE child for the whole deployment, on a fixed loopback port
   │  every other worker's proxy forwards to it (follower mode)
   ▼
Vendored dbview NestJS API  (plugins/dbview/dbview/apps/api)
   │  GatewayAuthGuard → JIT-mirror user → per-dialect connector
   ▼
Target data source (Postgres, Neo4j, MongoDB, Elasticsearch, Salesforce, …)
```

## What each surface does

| Surface | What it's for |
|---|---|
| **Connections** | Register a data source (connection string, encrypted at rest) and choose who else can see it — private, admins, everyone, or a named list, always confined to the caller's tenant. |
| **Schema graph** | An auto-laid-out, interactive graph of the introspected schema — tables/FKs, labels/relationships, collections, sObjects — one React Flow node type per engine kind. |
| **Ask (NL → Query)** | A plain-English question becomes a dialect-native query (SQL/Cypher/Mongo ops/SOQL/…), validated against the real schema before it's ever shown to you, with conversational follow-ups. |
| **Query, results & history** | Run the generated (or hand-edited) query against a read-only session, browse a sortable result table, export CSV, and revisit past questions with favorites. |

## Who it's for

- **Developers** onboarding onto an unfamiliar schema — SQL or graph — without
  writing a single query by hand.
- **DBAs and data analysts** who need a fast, safe way to explore production or
  staging data without risking a write.
- **Teams standardizing on one workbench** across relational, graph, document,
  vector, search and Salesforce data instead of one tool per engine.

## Design principles

- **Safety by construction, not by trust.** Every generated query is validated
  against the introspected schema and re-validated at execution time; the
  underlying DB session itself is opened read-only. See
  [Query, results & history](guide/query-results-history.md).
- **Vendor, don't rewrite.** The NestJS/React stack ships as-is; the plugin
  contributes hosting, lifecycle and identity — not a reimplementation of 18
  engine adapters.
- **One authoritative process, always.** A Postgres advisory lock elects a
  single worker to own the Node child across a multi-worker deployment, so
  connections and sessions are never split across siblings. See
  [Architecture](reference/architecture.md).
- **Framework-native identity.** dbview never re-implements login — it
  consumes the platform's central `auth` plugin through a signed gateway
  bridge. See [Security & RBAC](reference/security.md).

## Next steps

- New here? Start with **[Getting started](getting-started.md)** — connect
  your first data source and ask your first question.
- Operating or deploying dbview? See **[Architecture](reference/architecture.md)**,
  **[Configuration](reference/configuration.md)** and the
  **[Runbook](operations/runbook.md)**.
