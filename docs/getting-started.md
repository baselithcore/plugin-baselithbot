# Getting started

This walkthrough connects a data source and asks a first question against it.

## Prerequisites

- The dbview plugin is installed and enabled, and the backend has been
  **restarted** after install — the SPA and the proxy router mount at app
  startup (they are not hot-reloadable).
- Node.js ≥ 20 is on the host `PATH`, and the vendored stack has been built
  once (see below).
- `DBVIEW_SECRET` (≥ 16 chars) is set — it encrypts stored connection strings
  and is mandatory; the plugin refuses to activate without it.
- You can reach the UI at **`/dbview/`** and are signed in through the central
  auth plugin (if auth is enforced).

!!! note "Access"
    Tab visibility for `dbview` is governed centrally by RBAC (default-allow).
    Ask an administrator if the tab is hidden. See
    [Security & RBAC](reference/security.md).

## Build the stack (operators only)

Both the Node API and the SPA ship as built artifacts.

```bash
cd plugins/dbview/dbview
pnpm install && pnpm -r build

VITE_API_BASE_URL=/api/dbview VITE_BASE_PATH=/dbview/ VITE_AUTH_MODE=gateway \
  pnpm --filter @dbview/web build

# then restart the backend — the proxy router and the SPA mount during
# create_app()
```

`DBVIEW_PLUGIN_MODE=dev` runs `pnpm dev` (turbo) instead, for local iteration
against the vendored stack.

## 1. Sign in

Open **`/dbview/`**. Under central-auth (gateway) mode dbview's own login
screen is inert — your identity is forwarded automatically by the host proxy,
and the corresponding dbview user is created/updated just-in-time on your
first authenticated request.

## 2. Connect a data source

Open **Connections → New connection**, pick a dialect and paste a connection
string:

| Dialect family | Example |
|---|---|
| Postgres / MySQL / MSSQL / … | `postgres://user:password@host:5432/database` |
| Neo4j | `neo4j://user:password@host:7687` |
| MongoDB | `mongodb://user:password@host:27017/database` |
| Elasticsearch | `elasticsearch://user:password@host:9200` |
| Qdrant | `http://host:6333` |
| Salesforce | `salesforce://<instanceUrl>?clientId=…&clientSecret=…&apiVersion=v60.0` |
| SQLite | upload a `.db` file or a SQL dump |

dbview tests reachability before saving. Choose a **sharing mode** — private
(default), admins, everyone, or a named list of users — see
[Connections & sharing](guide/connections.md) for what each one means.

!!! tip "Use a read-only credential"
    dbview enforces read-only at the query-validator level *and* at the DB
    session level (`BEGIN READ ONLY`, `PRAGMA query_only`, driver read mode,
    …), but a genuinely read-only DB role is defense in depth worth having.

## 3. Explore the schema

Select the connection and open the **Schema graph**. Tables/labels/collections
lay out automatically; click a node to open its details in the side drawer.

## 4. Ask a question

Open **Ask**, type a question in plain English — e.g. *"Top 5 customers by
total revenue"* — and generate. dbview returns a validated, dialect-native
query with an explanation and the entities it touched (highlighted on the
graph). Hit **Run** to execute it against the read-only session.

!!! warning "Nothing you ask can write"
    `SELECT *`, DDL, and (by default) DML are rejected before you ever see a
    query — see [Query, results & history](guide/query-results-history.md#safety).

## 5. Keep exploring

Ask a follow-up (*"Now group those by month"*) — dbview keeps the conversation
in context. Revisit past questions from **History**, star the useful ones, and
export any result set as CSV.

## Where to go next

- Understand who can see a connection and why → **[Connections & sharing](guide/connections.md)**.
- How the NL→Query pipeline validates itself → **[Query, results & history](guide/query-results-history.md)**.
- Deploying with more than one backend worker → **[Runbook](operations/runbook.md)**.
