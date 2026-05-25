# ADR-0004: Helm Chart per Path Multi-Tenant

**Status:** Accepted (skeleton MVP, attivazione F5+)
**Date:** 2026-05-03

## Context

MVP target = workstation Electron + DGX Spark dedicato. Path roadmap richiede multi-tenant cluster K8s post-MVP. Cliente enterprise potenzialmente vuole deploy on-prem in cluster isolato già MVP.

## Decision

Pubblicare **Helm chart** [docker/helm/docheck/](../../docker/helm/docheck/) skeleton con feature flag `multiTenant.enabled` per attivazione differita.

**Componenti chart:**
- `engine` StatefulSet (persistent volume per DB + traces).
- `vllm` Deployment (GPU node selector).
- `ui` Deployment (statico Next.js export).
- `NetworkPolicy` egress lockdown by default.
- `Secret` signing key esterno (mai in container image).

**Multi-tenant gating:**
- `multiTenant.postgres` → swap SQLite → Postgres con tenant id row-level.
- `multiTenant.qdrant` → swap Chroma → Qdrant cluster con namespace per tenant.
- `multiTenant.oidc` → attiva OIDC issuer (Keycloak), disabilita login locale.

## Consequences

**Positive**
- Deploy enterprise customer-ready dal D1 (workstation Electron resta opzione primaria).
- NetworkPolicy egress lockdown enforce by default → conformità "zero cloud leak".
- Path multi-tenant è swap di config, non rewrite.

**Negative**
- Mantenere parity SQLite ↔ Postgres → migration script aggiuntivo.
- ChromaDB ↔ Qdrant: API simili ma semantic differences (filter syntax) → wrapper layer richiesto.

## Alternatives Considered

- **Docker Compose only**: insufficiente per multi-tenant scale; no service mesh, no NetworkPolicy primitives.
- **Kustomize**: meno friendly per opzioni feature-flag complesse.
- **Operator Kubernetes custom**: overkill MVP, posticipato a F6+ se richiesto da deploy fleet.

## Activation Plan (F5)

1. Implementare `db/backend.py` astrazione SQLite/Postgres.
2. Wrapper `services/embedding.py` per Chroma↔Qdrant.
3. Attivare OIDC stub [`core/oidc.py`](../../docheck-engine/src/docheck/core/oidc.py).
4. Tenant context middleware: estrae `tenant_id` da JWT claim.
5. Row-level security policies (Postgres `CREATE POLICY`).
6. Helm values di esempio per cliente enterprise.
