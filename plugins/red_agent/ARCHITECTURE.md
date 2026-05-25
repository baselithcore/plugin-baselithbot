# Red Agent — Architecture

> **Status (2026-04-26):** server-side orchestrator + UI production-ready;
> endpoint daemon Phase 1 / MVP shipped as `v0.1.0` (full mTLS, ed25519
> enrollment, signed-policy bundle verifier, sandboxed local executor).
> Phase 2 (eBPF / ESF / NATS / self-update) on the roadmap.

## 1. Mission

The Red Agent is an enterprise-grade, autonomous Red Team plugin that
runs reconnaissance, DAST and SCA scans against authorized URLs, APIs
and code repositories, then materializes the discovered attack surface
as a queryable property graph in FalkorDB. It is delivered as a
first-class BaselithCore plugin (`plugins/red_agent/`), respecting the
*Sacred Core rule*: no domain logic leaks into `core/`.

## 2. Architectural pillars

The design is anchored on three framework invariants:

1. **Plugin isolation** — every byte of red-team logic lives under
   `plugins/red_agent/`. Core only contributes generic infrastructure
   (`core.config.sandbox`, `core.di.container`, `core.plugins`).
2. **Sandbox-first execution** — every scanner binary executes through
   `SandboxRunner`, an asyncio wrapper over `docker run` with a
   read-only rootfs, dropped capabilities, no-new-privileges,
   memory/PID limits and an argv list (no shell). Direct `subprocess`
   calls in adapters are forbidden.
3. **Guardrails before action** — `GuardrailPipeline` rejects unsafe
   schemes, SSRF-prone hosts, out-of-scope targets, and demotes any
   active/intrusive intensity into a HITL approval cycle delegated to
   `core.human`.

## 3. Component map

```text
plugins/red_agent/
├── manifest.yaml             plugin metadata + integrity hash slot
├── plugin.py                 RedAgentPlugin (AgentPlugin), DI wiring
├── agent.py                  RedAgent orchestrator (scan lifecycle)
├── planner.py                Deterministic / Chaining attack planners
├── llm_planner.py            LLMReasoningPlanner + redaction
├── critic.py                 RoE / redundancy critics (vet every step)
├── config.py                 RedAgentConfig (Pydantic + SecretStr)
├── models.py                 Target / Finding / ScanRequest / ScanResult
├── guardrails.py             SSRF + scope + intensity gating
├── sandbox_runner.py         Hardened docker runner
├── scanners/                 Scanner adapters (nmap, nuclei, zap, etc.)
├── daemon/                   Rust endpoint agent workspace
├── proto/                    gRPC service definitions (agent.proto)
├── grpc/                     Python gRPC server implementation
├── graph.py                  VulnerabilityGraph (FalkorDB Cypher)
├── persistence/              Postgres DAOs (scans, agents, tokens)
├── audit.py                  Append-only audit logger
├── dependencies.py           FastAPI deps + auth-plugin RBAC bridge
├── routers/                  /red-agent/scans, /findings, /graph, /agents
├── migrations/               SQL migration files
└── ui/                       React frontend source
```

## 4. Data flow

```text
ScanRequest
   │
   ├── persistence.insert_scan      (status=QUEUED)
   ├── audit.record(scan.submitted)
   │
   ├── GuardrailPipeline.check ─── violation? → status=FAILED, raise
   │
   ├── if active/intrusive ──► core.human approval (HITL)
   │                              denied? → status=CANCELLED
   │
   └── _run_scan (asyncio.Task, semaphore-limited)
         ├── graph.upsert_target / upsert_scan
         ├── for s in selected_scanners:
         │     SandboxRunner.execute(image, argv, network, timeout)
         │         → stdout/stderr/artifacts
         │     Scanner._parse(output)  →  list[Finding]
         ├── persistence.insert_findings
         ├── graph.upsert_finding (Vulnerability + Endpoint + Service nodes)
         └── audit.record(scan.finished)
```

The graph projection is rebuilt incrementally per scan; Postgres is the
source of truth, FalkorDB is a derived view optimized for traversal
queries powering the UI's Attack Surface canvas.

## 5. Security posture

- **SSRF** — `TargetGuardrails._reject_private` resolves the host and
  rejects any address that is loopback, private, link-local,
  multicast, reserved or unspecified, mirroring the existing
  `BrowserAgent` rule. Override only via
  `RED_AGENT_ALLOW_INTERNAL_TARGETS=true`.
- **Scope** — `scope_allowlist` (CIDRs + domains, suffix-aware) is
  enforced unless `bug_bounty_mode=true`, in which case authorization
  is delegated to the upstream bug-bounty program metadata.
- **Intensity** — `INTRUSIVE` always requires HITL; `ACTIVE` requires
  HITL when `require_hitl_for_active=true` (default). `sqlmap` is
  bound to `INTRUSIVE` intensity — refused otherwise.
- **Secrets** — every credential (graph password, bug-bounty token) is
  `pydantic.SecretStr`, never serialised through logs or `repr()`.
- **Sandbox** — read-only root, dropped caps, no-new-privileges,
  argv-list invocation, per-scan workspace mounted rw and removed in
  `finally`. Network is bound to `none` unless the scanner declares
  `requires_network`.
- **Audit** — append-only `red_agent_audit` table, recording submit /
  guardrail-violation / hitl / start / finish events with actor and
  scan id, retained for `audit_retention_days` (365 default).

## 6. Auth-plugin integration

`plugins/red_agent/dependencies.py` consumes the local `auth` plugin's
public deps when present:

```python
from core.auth import AuthRole
from plugins.auth.dependencies import require_auth, require_roles
```

Mutating endpoints (`POST /red-agent/scans`, `quick_scan`) are gated by
`require_security_operator()` (currently mapped to `AuthRole.ADMIN`,
with a follow-up plan to introduce a dedicated `SECURITY_OPERATOR`
role). Read endpoints use `require_viewer()` (any authenticated user).
When the auth plugin is absent, every Red Agent endpoint returns 503 —
fail-closed by design.

## 7. Storage tiers

| Tier        | Backend       | Role                                          |
| ----------- | ------------- | --------------------------------------------- |
| Relational  | Postgres      | Source of truth for scans, findings, audit   |
| Graph (L2)  | FalkorDB      | Attack-surface projection, traversal queries |
| Cache       | Redis         | Idempotency keys, scan-status pubsub         |
| Object*     | (optional)    | Future: SARIF / PCAP / report artifacts      |

All three are first-class storage tiers of the framework.

## 8. UI

A standalone React + Vite SPA (`plugins/red_agent/ui/`) following the
`baselithbot` packaging pattern (`npm run build` → `ui/dist/`). Theme:
*Cyber-Modern Dark Mode* with neon-on-graphite tokens, monospace
display font, glow reserved for critical state, severity encoded with
shape and label (not color alone). Cytoscape.js renders the live
attack-surface graph with `fcose` layout. WebSocket streams scan
progress and findings into the dashboard with sub-second latency.

## 9. Operational definition of done (MVP)

The Red Agent is considered operational when:

1. The plugin loads via `core.plugins.loader` and registers its routers.
2. `POST /red-agent/scans/quick { target_value }` (admin auth) accepts
   a public URL, passes guardrails, runs `nmap` + `nuclei` in a
   sandbox container, and returns a `scan_id`.
3. The scan transitions through `running → completed`, with findings
   persisted in `red_agent_findings` and reflected in FalkorDB as
   `Target → Endpoint → Vulnerability` nodes.
4. The UI Attack Surface view renders the resulting graph in real time.

## 9.bis Planner pipeline

The orchestrator loop is:

```text
plan_next_step → critic.review → execute scanners → ingest findings
        ▲                                                  │
        └──────────────────────────────────────────────────┘
```

Three planner backends slot into the same `AttackPlanner.plan()`
async protocol:

| Backend                | When it runs                                              |
| ---------------------- | --------------------------------------------------------- |
| `DeterministicPlanner` | default; runs the requested scanner set once              |
| `ChainingPlanner`      | `multi_step_chains=true`; chains DAST on new endpoints    |
| `LLMReasoningPlanner`  | `llm_planner_enabled=true`; falls back to `ChainingPlanner` on any provider/parse/budget failure |

Whatever the planner returns flows through `CompositeCritic`
(`RoECritic` then `RedundancyCritic`) before the orchestrator
executes it. The critic is the second wall: out-of-scope or
above-cap proposals from an LLM are vetoed regardless of how
plausible the rationale looks. See
[docs/llm_planner.md](docs/llm_planner.md).

## 9.ter LLM-attack scanner suite (OWASP LLM Top 10)

Active probes that target AI-backed applications. Each scanner walks
a SPDX-clean YAML payload corpus shipped under
`scanners/llm_payloads/`, sends one curl-sandboxed request per
payload, and applies rule-based detection to the response:

| Scanner                | OWASP         | Default CWE  |
| ---------------------- | ------------- | ------------ |
| `llm_recon`            | discovery     | CWE-200      |
| `llm_prompt_injection` | LLM01         | CWE-1426     |
| `llm_tool_abuse`       | LLM07 + LLM08 | CWE-1426     |
| `llm_data_leakage`     | LLM06         | CWE-200      |
| `llm_output_handling`  | LLM02         | per-payload  |

All probes refuse to run below `ScanIntensity.ACTIVE` and require the
engagement to grant `autonomy_level >= execute_active`. See
[docs/llm_probes.md](docs/llm_probes.md).

## 10. Endpoint daemon integration (Phase 1)

The orchestrator's reach extends to customer hosts via the standalone
Rust daemon under [daemon/](daemon/). End-to-end shape:

```text
host ─ baselith-redagent-daemon (single static binary, no listeners)
         │
         │  outbound TLS 1.3 only, ed25519 client cert,
         │  root-CA SPKI fingerprint pinned at install
         ▼
    Envoy LB ──► gRPC AgentServicer (plugins/red_agent/grpc)
                       │
                       ├── persistence/agents.py        (enrolled fleet)
                       ├── persistence/agent_telemetry.py (partitioned events)
                       ├── persistence/agent_certs.py   (active / revoked)
                       ├── persistence/enrollment_tokens.py
                       └── audit.py                     (all lifecycle events)
```

Server-side surface added by Phase 1:

- `routers/agents.py` — fleet listing, enrollment-token CRUD,
  daemon-facing `/agents/enroll` redemption (only unauthenticated
  endpoint, gated by single-use token + tenant binding).
- `crypto/agent_ca.py` — ed25519 cert issuer; loaded only when
  `RED_AGENT_CA_CERT_PATH` and `RED_AGENT_CA_KEY_PATH` are set.
  Without them the plugin loads in degraded mode (logs
  `red_agent.ca.unconfigured`, every enroll returns 503).
- `policy.py` — signed policy bundles (ed25519); the daemon refuses
  bundles with non-monotonic versions, skewed timestamps, or invalid
  signatures. The verifier survives daemon reconnects so an attacker
  cannot replay an old bundle by forcing a session drop.
- `models.TargetKind.HOST` + UI Host wizard
  ([ui/src/routes/new_target/wizard_steps.tsx](ui/src/routes/new_target/wizard_steps.tsx))
  — bind a target to an enrolled daemon (`agent:<uuid>` value);
  scans flow through the daemon's local sandboxed executor instead
  of the backend Docker sandbox.

Daemon-side spec lives in [docs/agent_daemon.md](docs/agent_daemon.md).
Operational invariants: TLS 1.3 only, root CA SPKI pin, OS keystore
identity, no inbound listeners.
