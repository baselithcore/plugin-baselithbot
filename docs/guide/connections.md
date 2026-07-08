# Connections & sharing

A **connection** is a saved, encrypted credential to one data source, plus who
else is allowed to see and use it. It's the unit dbview scopes everything
else — schema, queries, history — around.

## Registering a connection

From **Connections → New connection**, supply a name, a dialect, and a
connection string (or upload a SQLite file / SQL dump). dbview tests
reachability by introspecting the source before saving — a bad credential or
an unreachable host is caught immediately, not on first use.

The connection string is stored **AES-256-GCM encrypted at rest**, keyed from
`DBVIEW_SECRET`. It is only ever decrypted in-memory at connect time, never
returned by any endpoint and never logged.

## Sharing modes

Every connection has an **owner** (the creator) and a sharing mode:

| Mode | Who else can see and use it |
|---|---|
| `private` (default) | Nobody but the owner. |
| `admins` | Every admin in the same tenant — the operational co-op default. |
| `all` | Every authenticated user in the same tenant. |
| `users` | An explicit list of user ids, in the same tenant. |

The owner can always see and use their own connection regardless of mode.
Visibility and the ability to resolve/run against a connection are the same
check — a visible-but-unusable connection would only confuse users.

!!! note "Sharing never crosses a tenant"
    Non-owner visibility is confined to identities that resolve to the **same
    tenant key**. This is enforced upstream, not by the proxy — see
    [Multi-tenancy](../reference/tenancy.md) for how the tenant key is derived
    and forwarded.

## Uploading a file-based source

SQLite connections can be created from an uploaded `.db` file or a `.sql`
dump — the dump is applied to a fresh local SQLite file before the connection
is saved.

## Deleting or changing sharing

Owners manage their own connections freely. An admin can delete or change the
sharing mode of a connection they don't own (operational recovery for
deactivated owners or orphaned connections) — every such cross-admin mutation
is logged to the audit trail with the connection id, owner and actor.

## Engines

18 dialects across seven kinds — every one goes through the same introspect →
visualize → ask → validate → execute pipeline:

| Kind | Dialects |
|---|---|
| SQL | PostgreSQL, MySQL, MariaDB, MSSQL, SQLite, CockroachDB, Oracle, ClickHouse, DuckDB |
| Graph | Neo4j, FalkorDB, Ultipa |
| Document | MongoDB |
| Vector | Qdrant |
| Key-value | Redis |
| Search | Elasticsearch |
| SaaS | Salesforce, Salesforce Data Cloud |

## Next

- See what dbview shows you once a connection is picked →
  **[Schema graph](schema-graph.md)**.
