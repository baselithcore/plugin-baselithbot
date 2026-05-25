# ADR-0009: Policy CRUD with YAML Import/Export

**Status:** Accepted
**Date:** 2026-05-03

## Context

The Policies tab originally exposed read-only listing. Production use requires:

- Compliance officers must author and version policies without DB access.
- Admins must seed shipped catalogues (GDPR, ISO, NIS2) reproducibly.
- Each rule keeps verbatim policy excerpts (Glass Box pillar) — a portable,
  human-reviewable format is mandatory.

## Decision

1. Full CRUD endpoints under `/api/v1/policies` for both policies and their rules.
2. YAML as the canonical portable format (`POST /policies/import`,
   `GET /policies/{id}/{version}/export.yaml`). PyYAML is bundled.
3. `(policy_id, version)` is the composite primary key; **versions are
   immutable** once any signed Report references them — `DELETE` is blocked
   by `409 Conflict` if `policies_applied` cites the policy. Use clone +
   deactivate workflow for revisions.
4. Rule IDs are global PKs: import always regenerates rule IDs to avoid
   cross-policy collisions.
5. RBAC actions: `policy:read` (list/inspect/export), `policy:write` (create,
   update metadata, activate/deactivate, clone, manage rules, import),
   `policy:admin` (delete). Seeded by migration `0005`.
6. Every mutation appends an immutable audit-log entry
   (`policy.{create,update,activate,deactivate,clone,delete,import,rule.*}`).

## Consequences

- Positive: deterministic policy lifecycle, signed-report integrity preserved,
  human-readable artefacts for review boards and CI.
- Negative: deleting a policy version requires manual cleanup workflow when
  reports already cite it (intentional tradeoff).
- Service layer split (`services/policies.py` + thin `api/policies.py`) keeps
  files under the 500-LOC budget set by CLAUDE.md.

## Alternatives considered

- JSON-only import: rejected — YAML is friendlier for verbatim multi-line
  excerpts.
- Allowing destructive edits (mutating rules in place after sign-off): rejected
  for audit reproducibility.
- Soft-delete via `active=0`: kept as the user-facing default (Deactivate
  button); hard delete is restricted to `policy:admin`.
