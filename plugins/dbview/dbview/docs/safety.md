# Safety validators

Non-negotiable rules. Each dialect family has a validator that runs **twice**: once on NL2SQL output before returning to the client, and again on `/api/query/execute` input before opening a DB session. Defense in depth.

If you ever need to loosen a rule, update the corresponding `*.test.ts` first and get explicit approval.

## SQL — `packages/sql-core/src/safety/validator.ts`

Parser: [`node-sql-parser`](https://github.com/taozhi8833998/node-sql-parser), with a per-dialect parser identifier mapped in `PARSER_DIALECT`. Identifier case is preserved by never re-`sqlify`-ing the parsed AST.

### Rules

| Rule                                                                                                        | Action                                                                |
| ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Empty after comment strip                                                                                   | reject (`unsafe_sql`)                                                 |
| Multiple statements (`;` inside)                                                                            | reject                                                                |
| Statement type not `select`                                                                                 | reject unless `allowDml` and type ∈ `{insert, update, delete, merge}` |
| Statement type ∈ `{drop, truncate, alter, create, rename, grant, revoke, set, use, replace, call, execute}` | reject — always blocked, even with `allowDml`                         |
| `SELECT *` (any star)                                                                                       | reject — must enumerate columns                                       |
| Tables not in introspected schema (excluding CTE names)                                                     | warning + retry feedback                                              |
| Columns not in schema                                                                                       | attempt alias auto-correction; otherwise warning + retry feedback     |
| Missing `LIMIT` on `SELECT`                                                                                 | inject `LIMIT <rowLimit>` (default 5000)                              |

### Read-only DB session (defense-in-depth)

Even if the validator misses something, the executor refuses writes at the DB level:

- **Postgres** — `BEGIN READ ONLY; <query>; COMMIT` with `SET LOCAL statement_timeout = 5000`.
- **SQLite** — file opened `readonly: true`, `PRAGMA query_only = ON` set after open.
- **MySQL / MariaDB / MSSQL / Oracle / ClickHouse / DuckDB / CockroachDB** — read-only session via dialect-specific connection options.

### Column resolution

The validator builds an alias map from the parsed AST:

```
FROM customer AS c
JOIN invoice AS i ON i.customer_id = c.id
JOIN invoice_line AS il ON il.invoice_id = i.id
```

→ `{ c: customer, i: invoice, il: invoice_line }`.

For each column reference:

- `*` and SELECT-alias references are skipped.
- CTE-qualified references are skipped (CTE schema is local).
- Otherwise the column must exist on the aliased table.
- If not, see [Alias auto-correction](./nl2sql.md#alias-auto-correction).

## Cypher — `packages/cypher-core/src/safety.ts`

Token-based check (no full Cypher parser). Robust enough for the surface area of read-only queries.

### Rules

| Rule                                                                                                                                                                                  | Action                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Statement does not start with `MATCH` / `OPTIONAL` / `WITH` / `CALL` / `UNWIND` / `RETURN`                                                                                            | reject                                                               |
| Contains write keyword: `CREATE`, `DELETE`, `DETACH`, `MERGE`, `SET`, `REMOVE`, `DROP`, `LOAD CSV`, `USING PERIODIC`, `FOREACH`                                                       | reject (unless `allowWrites=true`, which is not exposed via the API) |
| Calls dangerous procedure prefix: `apoc.create.*`, `apoc.merge.*`, `apoc.refactor.*`, `apoc.load.*`, `apoc.export.*`, `apoc.periodic.*`, `db.create.*`, `db.drop.*`, `dbms.*`, `tx.*` | reject                                                               |
| Multiple statements (`;` inside)                                                                                                                                                      | reject                                                               |
| Label not in introspected schema                                                                                                                                                      | warning + retry feedback                                             |
| Property not on label                                                                                                                                                                 | warning + retry feedback                                             |
| Missing `LIMIT`                                                                                                                                                                       | inject                                                               |

The Neo4j driver is opened with `defaultAccessMode: READ`, so even a slipped write fails at the server.

## SOQL (Salesforce) — `apps/api/src/engine/salesforce/safety.ts`

| Rule                                                           | Action                         |
| -------------------------------------------------------------- | ------------------------------ |
| Statement not `SELECT`                                         | reject                         |
| `SELECT *`                                                     | reject — must enumerate fields |
| Multiple statements                                            | reject                         |
| `FROM` references unknown sObject (case-insensitive)           | reject                         |
| Single-identifier field refs not in target sObject's field set | reject                         |
| Missing `LIMIT`                                                | inject                         |

Dotted-path field references (relationships, e.g. `Account.Owner.Name`) are not validated against the schema — the relationship graph is too large to introspect fully — they pass through to the Salesforce REST API which validates them server-side.

The Salesforce REST client only exposes `SELECT` paths; no DML helpers exist on the client surface.

## Other dialects

- **MongoDB** ([packages/document-core](../packages/document-core/)) — only `find`, `aggregate`, `count`, `distinct` operations exposed. Write commands (`insertOne`, `updateMany`, etc.) are not surfaced through the executor.
- **Redis** ([packages/keyvalue-core](../packages/keyvalue-core/)) — read commands only (`GET`, `KEYS`, `SCAN`, `HGETALL`, etc.). Write commands rejected.
- **Elasticsearch** ([packages/search-core](../packages/search-core/)) — `_search` and `_count` only; no `_bulk` or `_update`.
- **Qdrant** ([packages/vector-core](../packages/vector-core/)) — search and scroll only; no upsert/delete.

## Test suite

Each safety validator ships with a unit-test sibling:

- `packages/sql-core/src/safety/validator.test.ts` — 12 SQL cases.
- `packages/cypher-core/src/safety.test.ts` — 10 Cypher cases.
- Salesforce SOQL tests in `apps/api/src/engine/salesforce/safety.test.ts`.

Run with `pnpm -r test`. Pre-commit gate: all must pass.

## Reporting & error surface

All safety failures return HTTP 400 with `{ code, message }`:

| Dialect | Code            |
| ------- | --------------- |
| SQL     | `unsafe_sql`    |
| Cypher  | `unsafe_cypher` |
| SOQL    | `unsafe_soql`   |

`message` quotes the failing fragment when feasible (truncated to 200 chars).
