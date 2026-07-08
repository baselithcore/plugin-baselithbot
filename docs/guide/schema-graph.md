# Schema graph

Once a connection is selected, dbview introspects it and renders the result as
an interactive graph — the same canvas whatever the engine kind, so switching
between a Postgres database and a Neo4j graph feels like the same tool, not two.

## What gets introspected

| Engine kind | Unified shape | Node type |
|---|---|---|
| Relational (SQL) | Tables + columns + foreign keys | `TableNode` |
| Graph (Neo4j/FalkorDB/Ultipa) | Labels + relationship types | `LabelNode` |
| Document (MongoDB) | Sampled collections + inferred fields | `CollectionNode` |
| Vector (Qdrant) | Collections + vector dimension + payload sample | `CollectionNode` |
| Key-value (Redis) | Keyspaces + key-pattern/type histogram | `KeyspaceNode` |
| Search (Elasticsearch) | Indices + mappings tree | `IndexNode` |
| SaaS (Salesforce) | sObjects + fields + reference arrows | `SObjectNode` |

Document/vector/key-value/search schemas are **sampled, not strict** — field
types are inferred from sample documents/keys/mappings rather than a rigid
catalog, since those engines don't enforce one.

## Layout

The graph is auto-laid-out (dagre) and memoized on `(schema, highlights)`, so
hovering an entity — e.g. one referenced by a generated query — highlights it
without recomputing the whole layout. Each schema gets a deterministic header
color derived from its name, so the same schema always renders identically
across sessions.

## Refreshing

Schema is cached after first introspection for the session. Re-fetch it (for
example after a migration on the source) with a manual refresh — the same
introspection endpoint accepts a `refresh` flag so you're never looking at a
stale shape without asking to be.

## Details

Click any table, label, collection or field to open the **detail drawer** —
column types, nullability, primary/foreign keys for relational sources; label
properties and relationship types for graph sources, and so on per kind.

## Next

- Turn what you see into a query without writing one →
  **[Ask (NL → Query)](nl2query.md)**.
