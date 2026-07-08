# Query, results & history

The generated query (or one you hand-edit) runs against a read-only session;
the result lands in a sortable table you can export, and the question is kept
in history for later.

## Safety

Every query is checked **twice** — once on the NL→Query output before it's
shown to you, and again on `execute` input, right before a DB session opens.
Defense in depth: even if one layer is bypassed, the other still blocks it.

### Relational SQL

- `SELECT *` is rejected — columns must be enumerated.
- DDL (`DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `RENAME`, `GRANT`, `REVOKE`,
  `SET`, `USE`, …) is **always** blocked.
- DML (`INSERT`, `UPDATE`, `DELETE`, `MERGE`) is blocked **by default**
  (`allowDml` is not exposed through the UI).
- Multiple statements in one query are rejected.
- Tables/columns not present in the introspected schema are rejected — with a
  deterministic **alias auto-correction** when a column exists on exactly one
  other table in the same query, so a typo'd alias doesn't need a round-trip.
- A missing `LIMIT` is injected automatically (default 5000 rows).

### Graph (Cypher)

- A statement must start with `MATCH`/`OPTIONAL`/`WITH`/`CALL`/`UNWIND`/`RETURN`.
- Write keywords (`CREATE`, `DELETE`, `MERGE`, `SET`, `DROP`, …) and dangerous
  procedure prefixes (`apoc.create.*`, `db.drop.*`, `dbms.*`, …) are rejected.
- Labels/properties not in the introspected schema trigger retry feedback.

### SOQL (Salesforce)

- Only `SELECT` is allowed; `SELECT *` and multi-statement input are rejected.
- Unknown sObjects are rejected; unknown single-identifier fields are
  rejected (dotted relationship paths pass through to Salesforce's own
  server-side validation).

### Other engines

MongoDB exposes only `find`/`aggregate`/`count`/`distinct`; Redis exposes only
read commands; Elasticsearch exposes only `_search`/`_count`; Qdrant exposes
only search/scroll. No write path is surfaced through the executor for any of
them.

### Read-only at the database level

Even if a validator ever missed something, the DB session itself refuses
writes: Postgres opens `BEGIN READ ONLY` with a 5-second `statement_timeout`;
SQLite opens `readonly: true` with `PRAGMA query_only = ON`; every other
dialect uses its own read-only session/driver option (Neo4j's driver, for
instance, is opened with `defaultAccessMode: READ`).

## Results

The result table is sortable and exports to CSV. Long result sets can be
condensed into a short natural-language summary (see
[Ask → Explain & summarize](nl2query.md#explain--summarize)).

## History

Every asked question is recorded with its generated query, so you can revisit
it later, mark it a **favorite**, or delete it. History is scoped per
connection and per tenant — see [Multi-tenancy](../reference/tenancy.md).

## Next

- Understand the identity and tenancy behind what you see →
  **[Security & RBAC](../reference/security.md)**,
  **[Multi-tenancy](../reference/tenancy.md)**.
