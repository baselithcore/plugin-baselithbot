# Red Agent — Design Principles

The Red Agent is built around a small set of architectural tenets that
keep it useful in production without becoming dangerous. Every change
to this plugin is reviewed against these principles.

---

## 1. Adaptive reasoning, not static payload lists

The orchestrator drives scans through an `AttackPlanner` Protocol —
not a hard-coded sequence. The default implementation is deterministic
(`DeterministicPlanner`); the production-grade path uses
`ChainingPlanner` to feed each scanner's findings back into the
planning loop. The same loop accepts an `LLMReasoningPlanner` (Protocol
implementer) that decides the next move from the partial attack-surface
graph and the new findings. The orchestrator never embeds scan logic —
strategy is fully pluggable.

> **Knob:** `RED_AGENT_MULTI_STEP_CHAINS=true`,
> `RED_AGENT_CHAIN_MAX_ITERATIONS=3`.

## 2. Context-aware attack surface

Findings alone are not impact. The graph layer (`VulnerabilityGraph`)
exposes an extension schema for cloud and identity context:

- `CloudResource` (kind, region, owner_account)
- `Identity` (principal, type)
- `DataStore` (kind, sensitivity)
- `ApiSpec` (format, location)
- `(:Vulnerability)-[:LATERAL_TO]->(:CloudResource | :Identity | :DataStore)`

These nodes are populated by the operator's CSPM / cloud-context
plugin (or imported from a CMDB) — the Red Agent itself never queries
cloud APIs. The `lateral_paths(vuln_id)` query traverses both the scan
subgraph and the context layer to surface true blast radius.

## 3. Validated impact only

Noise erodes trust faster than missed findings. When
`RED_AGENT_VALIDATED_IMPACT_ONLY=true`, the orchestrator drops any
finding that is not (a) `severity ≥ HIGH`, (b) `cvss_score ≥
RED_AGENT_VALIDATED_IMPACT_MIN_CVSS`, or (c) carries an explicit
confirmation flag in `evidence` (set by adapters that perform real
exploitation, e.g. `sqlmap`). Default is off for backwards
compatibility, but every production deployment should turn it on.

## 4. Sandbox-first execution

Every scanner binary runs through `SandboxRunner` — a hardened
`docker run` wrapper with read-only rootfs, dropped capabilities,
no-new-privileges, memory and PID limits, and `argv`-list invocation
(no shell). Direct `subprocess` calls inside scanner adapters are
forbidden by review.

## 5. Guardrails before action

`GuardrailPipeline` rejects unsafe schemes, SSRF-prone hosts,
out-of-scope targets, and demotes any `active` or `intrusive`
intensity into a HITL approval cycle (`ApprovalRegistry` +
`/red-agent/scans/{id}/approve|reject`). Approvals are durable
(`red_agent_approvals` table) and survive restart.

## 6. Multi-step attack chains

Real exposures emerge from chained moves. `ChainingPlanner` runs recon
first, then DAST scanners against newly-discovered endpoints, up to
`chain_max_iterations`. Each planner step is recorded in the audit
log (`scan.planner_step`) with rationale and the findings that drove
it, so reviewers can replay the agent's decision tree.

## 7. Findings linked to the wider graph

Every vulnerability is upserted as a node and joined to its
`Endpoint`, `Service`, `Scanner`, `Scan`, `Target`, `CWE`, and `CVE`
peers. Operators with a cloud-context plugin add `LATERAL_TO` edges
to `CloudResource`, `Identity`, and `DataStore` nodes — making blast
radius queryable in Cypher.

## 8. RBAC + auditable trail

Mutating endpoints (`POST /red-agent/scans`, `quick`, `approve`,
`reject`) require the `security_operator` role provided by the local
`auth` plugin. Read endpoints require `viewer`. Every state
transition lands in `red_agent_audit` (append-only). When the auth
plugin is absent, every endpoint fails closed with **503**.

## 9. Bounded blast radius for the platform itself

A misbehaving scanner cannot DoS the host:

- Per-scanner timeouts (`RED_AGENT_SCANNER_TIMEOUTS`).
- `scanner_output_max_bytes` (default 64 KB) clips persisted
  evidence/raw payloads — full output stays in audit log.
- `max_concurrent_scans` semaphore bounds parallelism.
- `audit_retention_days` retention sweep deletes old audit rows.

## 10. Observable from minute zero

`/red-agent/health` is a Kubernetes-style readiness probe; the audit
log is structured; scan progress streams over WebSocket
(`/red-agent/ws/scans/{id}`); SARIF export is one HTTP call away
(`/red-agent/reports/{id}/sarif`); `baselith red-agent doctor` runs a
preflight from the operator's terminal.

---

## What the Red Agent does NOT do

- It does **not** fetch cloud configuration or runtime data on its
  own. Cloud context is populated by an external plugin and ingested
  via the graph helpers. This keeps the Red Agent free of cloud
  credentials.
- It does **not** sign findings as "exploitable" without active
  confirmation when `validated_impact_only=true`. Severity-based
  surrogates exist as a baseline for high/critical signals from
  template scanners.
- It does **not** invoke external networks outside the sandbox. The
  host process never opens sockets to scan targets.
- It does **not** execute LLM reasoning by default. The
  `LLMReasoningPlanner` is opt-in via DI, isolating the existing
  pipeline from prompt-injection risk against the planner itself.

---

## Operational maturity self-check

| Tenet | Default | Production-grade |
| --- | --- | --- |
| Scope policy | empty | `scope_allowlist` populated **or** `bug_bounty_mode` |
| HITL on active | enabled | enabled |
| Internal targets | blocked | blocked |
| Multi-step chains | off | on (`max_iterations=3`) |
| Validated-impact filter | off | on (`min_cvss=4.0`) |
| Auth plugin | optional | required (fail-closed) |
| Sandbox | docker | docker (read-only rootfs) |
| Audit retention | 365 days | per compliance (≥ 365 days) |

`baselith red-agent doctor` walks this list automatically.
