# Dialects & engines

dbview is engine-agnostic. The same NL2SQL → validate → execute pipeline serves SQL, Cypher, MongoDB, Elasticsearch, Qdrant, Redis, and Salesforce, with per-dialect prompts and validators.

## Catalog

Source of truth: `packages/shared/src/dialect.ts`.

| Kind     | Dialect         | Query language            | Status | Default port |
| -------- | --------------- | ------------------------- | ------ | ------------ |
| sql      | `postgres`      | SQL                       | stable | 5432         |
| sql      | `mysql`         | SQL                       | stable | 3306         |
| sql      | `mariadb`       | SQL                       | stable | 3306         |
| sql      | `mssql`         | SQL                       | stable | 1433         |
| sql      | `sqlite`        | SQL                       | stable | — (file)     |
| sql      | `cockroach`     | SQL                       | stable | 26257        |
| sql      | `oracle`        | SQL                       | stable | 1521         |
| sql      | `clickhouse`    | SQL                       | stable | 8123         |
| sql      | `duckdb`        | SQL                       | stable | — (file)     |
| graph    | `neo4j`         | Cypher                    | stable | 7687         |
| graph    | `falkordb`      | Cypher                    | stable | 6379         |
| graph    | `ultipa`        | Cypher                    | beta   | —            |
| document | `mongodb`       | Mongo query / aggregation | stable | 27017        |
| vector   | `qdrant`        | JSON envelope ops         | stable | 6333         |
| keyvalue | `redis`         | Redis commands            | stable | 6379         |
| search   | `elasticsearch` | Elasticsearch DSL         | stable | 9200         |
| saas     | `salesforce`    | SOQL                      | beta   | — (OAuth)    |

Each dialect has metadata: `kind`, `defaultPort`, `brandColor`, `beta`, `available`. The frontend uses `brandColor` for the schema-graph headers (deterministic — same dialect always gets the same color).

## Connection string formats

The shared package exposes `parse<Dialect>Connection()` helpers, all returning a normalized object.

### SQL — standard URI

```
postgres://user:password@host:5432/database
mysql://user:password@host:3306/database
mssql://user:password@host:1433/database?trustServerCertificate=true
sqlite:///absolute/path/to/file.db
cockroachdb://user:password@host:26257/database?sslmode=verify-full
oracle://user:password@host:1521/SERVICE
clickhouse://user:password@host:8123/database
duckdb:///absolute/path/to/file.duckdb
```

### Graph

```
neo4j://user:password@host:7687
neo4j+s://user:password@host:7687     # TLS
falkor://host:6379/<graph-name>
```

### Document / Vector / KV / Search

```
mongodb://user:password@host:27017/database
qdrant://host:6333?apiKey=...
redis://[:password@]host:6379/[db]
elasticsearch://user:password@host:9200
```

### Salesforce (OAuth Client Credentials only)

```
salesforce://<instanceUrl>?clientId=<id>&clientSecret=<secret>&apiVersion=v60.0&sandbox=false
```

The REST client at [apps/api/src/engine/salesforce/client.ts](../apps/api/src/engine/salesforce/client.ts) hits `POST {instanceUrl}/services/oauth2/token` and caches the bearer token in memory, refreshing ~25 minutes before expiry.

## Unified schema

Every introspector returns a `UnifiedSchema` whose shape depends on `kind`.

### Relational (`kind: 'relational'`)

```ts
{
  kind: 'relational',
  dialect: 'postgres' | ...,
  tables: [{
    name, schema?, columns: [{ name, dataType, nullable, primaryKey, ... }],
    rowCountEstimate?
  }],
  relationships: [{
    from: { table, column },
    to:   { table, column },
    name?
  }]
}
```

### Graph (`kind: 'graph'`)

```ts
{
  kind: 'graph',
  dialect: 'neo4j' | 'falkordb' | ...,
  labels: [{ name, properties: [{ name, type, nullable }] }],
  relationshipTypes: [{ name, from, to, properties }]
}
```

### Document / Vector / KV / Search

Sampled, not strict. Mongo collections, Qdrant collections, Redis keyspaces, Elasticsearch indices. Field types are inferred from sample documents.

### SaaS (Salesforce)

```ts
{
  kind: 'saas',
  dialect: 'salesforce',
  sObjects: [{ name, label, fields: [{ name, type, referenceTo? }] }]
}
```

The introspector calls `/services/data/<apiVersion>/sobjects` then `describe` for each, with concurrency limited to avoid Salesforce API quotas.

## Frontend rendering

The frontend dispatches on `schema.kind`:

| Kind         | React Flow node type                                            |
| ------------ | --------------------------------------------------------------- |
| `relational` | `TableNode` — header gradient, list of columns, PK/FK badges    |
| `graph`      | `LabelNode` — circular, property list, relationship edges typed |
| `document`   | `CollectionNode` — sampled field schema                         |
| `vector`     | `CollectionNode` — vector dimension + payload sample            |
| `keyvalue`   | `KeyspaceNode` — key patterns + type histogram                  |
| `search`     | `IndexNode` — mappings tree                                     |
| `saas`       | `SObjectNode` — fields + reference arrows                       |

Auto-layout uses `dagre`. Layout is memoized in `useMemo` keyed on `(graph, highlightedTables)` to avoid recomputation on hover.

## Sample data

`infra/` ships seed scripts for the demo dialects:

- `infra/seed/` — Postgres `shop` schema: customer, invoice, invoice_line, product, etc.
- `infra/neo4j-seed.cypher` — Customer/Order property graph.
- `infra/falkordb-seed.cypher` — Same content for FalkorDB.

See [Deployment](./deployment.md) for compose profiles and seed commands.
