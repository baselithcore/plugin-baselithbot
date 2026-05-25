# dbview — Documentation

Index of technical documentation for the dbview monorepo.

dbview is a read-only database visualization and natural-language-to-query tool. It ingests connection strings, introspects schema, renders it as an interactive graph, and translates plain-English questions into validated queries via local or remote LLMs. It supports SQL, Cypher, MongoDB queries, Redis commands, Elasticsearch DSL, Qdrant vector ops, and Salesforce SOQL behind a single unified API.

## Read in order

1. [Architecture](./architecture.md) — monorepo layout, request flow, type pipeline.
2. [Dialects & engines](./dialects.md) — supported databases, dialect metadata, query language per engine.
3. [HTTP API](./api.md) — endpoints, request/response shapes, rate limits, auth requirements.
4. [Auth & RBAC](./auth.md) — JWT, refresh-token rotation, argon2id, service-to-service API key, bootstrap admin.
5. [NL2SQL pipeline](./nl2sql.md) — prompt building, retry loop, sanitizer, grounding, alias auto-correction.
6. [Safety validators](./safety.md) — SQL, Cypher, SOQL, and other dialect-specific rules. Non-negotiable.
7. [Configuration](./configuration.md) — full environment-variable reference.
8. [Observability](./observability.md) — Prometheus metrics, OpenTelemetry traces, structured logs, health probes.
9. [Frontend](./frontend.md) — UI panels, state stores, API client, telemetry.
10. [Deployment](./deployment.md) — Docker Compose, profiles, persistence, healthchecks.

## Where things live

| Path                                                  | Contents                                                          |
| ----------------------------------------------------- | ----------------------------------------------------------------- |
| [apps/api/](../apps/api/)                             | NestJS + Fastify backend                                          |
| [apps/web/](../apps/web/)                             | Vite + React 19 + Tailwind frontend                               |
| [packages/shared/](../packages/shared/)               | Zod schemas, error classes, dialect enum — single source of truth |
| [packages/sql-core/](../packages/sql-core/)           | SQL introspector, AST safety validator, read-only executor        |
| [packages/cypher-core/](../packages/cypher-core/)     | Neo4j / FalkorDB introspector + Cypher safety                     |
| [packages/document-core/](../packages/document-core/) | MongoDB driver wrapper                                            |
| [packages/vector-core/](../packages/vector-core/)     | Qdrant client                                                     |
| [packages/keyvalue-core/](../packages/keyvalue-core/) | Redis client                                                      |
| [packages/search-core/](../packages/search-core/)     | Elasticsearch client                                              |
| [infra/](../infra/)                                   | Postgres seed schema, Neo4j seed cypher, FalkorDB seed            |
| [deploy/observability/](../deploy/observability/)     | Prometheus + Grafana + Loki + Tempo + OTel collector stack        |
| [CLAUDE.md](../CLAUDE.md)                             | Project conventions, hard rules, AI-assistant guidance            |

## Conventions cheat sheet

- ESM only. Workspace packages ship from `dist/`.
- TypeScript strict. No `any`. Zod at HTTP / env / LLM-output boundaries.
- 500 LOC max per file.
- Types flow `packages/shared` → API DTOs → React Query → UI. Never duplicated.
- Tests next to source: `validator.ts` + `validator.test.ts`.
