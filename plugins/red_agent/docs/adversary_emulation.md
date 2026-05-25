# Adversary emulation

Adversary emulation runs ATT&CK-mapped techniques against authorized
endpoints to test defensive coverage. It is *not* vulnerability
scanning — the goal is to confirm whether the SOC's controls fire on
known-bad actions, not to find new bugs.

Two execution backends ship:

| Backend | Where the technique runs | When to use |
| --- | --- | --- |
| Atomic Red Team (`atomic_loader.py`) | Endpoint daemon's local executor (sandbox-exec / landlock). | Hosts already enrolled with the Red Agent daemon; minimum new infra. |
| Caldera (`caldera_client.py`) | Caldera server pushes plans to its own agents. | Customers already running Caldera, or scenarios that need server-driven planning. |

Either backend produces :class:`EmulationResult` records that
:func:`result_to_findings.to_finding` lifts onto the standard
`Finding` shape, so emulation outcomes flow through the same triage,
audit, and ATT&CK-mapping pipeline as scan findings.

## Plan model

`EmulationPlan` captures the operator's intent before any code
executes:

- `target_agent_ids` — endpoint daemon UUIDs the plan is authorized
  against. The daemon executor refuses unbound plans by construction.
- `engagement_id` — inherits autonomy + intrusive gate from the
  parent engagement.
- `steps[]` — ordered :class:`EmulationStep`; each carries an
  ATT&CK technique id, an :class:`AtomicTest` payload, and an
  operator-supplied `input_overrides` dict.
- `authored_by` / `reviewed_by` — operator dual-control gate.

`EmulationPlan.is_dual_controlled()` returns true only when the
reviewer is a *different* operator from the author.

## Safety gates

Five toggles must all pass before any technique runs:

| Setting | Default | Effect |
| --- | --- | --- |
| `RED_AGENT_ADVERSARY_EMULATION_ENABLED` | false | Master toggle. |
| `RED_AGENT_ADVERSARY_REQUIRE_SIGNED_PLAN` | true | Plan must be signed via the existing policy-bundle pipeline. |
| `RED_AGENT_ADVERSARY_REQUIRE_DUAL_CONTROL` | true | Reject plans where author == reviewer. |
| `RED_AGENT_ADVERSARY_ALWAYS_RUN_CLEANUP` | true | Force every step's cleanup_command regardless of plan-author preference. |
| Engagement intensity | — | Must be `INTRUSIVE`. |

`RED_AGENT_ADVERSARY_MAX_STEPS_PER_PLAN` (default 50) caps plan
size; large plans must be split.

## Atomic Red Team loader

`atomic_loader.load_technique(atomics_root, technique_id)` reads
`<atomics_root>/<technique>/<technique>.yaml` and returns the
:class:`AtomicTest` records it defines. The loader is offline by
design — CI keeps the local `atomic-red-team` mirror current, the
loader never pulls.

`select_test(tests, *, platform, guid)` picks the first test that
runs on the requested platform, or the GUID-pinned one when the
operator wants to stick to a specific test version across upstream
re-orderings.

## Caldera client

`CalderaClient` speaks the Caldera v2 REST API. Authentication is
the upstream `KEY` header. Three operations are modelled:

- `submit_operation` — POST `/api/v2/operations`.
- `get_operation` — GET `/api/v2/operations/{id}`.
- `list_links` — GET `/api/v2/operations/{id}/links` for per-step
  results.

Errors are wrapped in :class:`CalderaClientError` with the upstream
status + body trimmed to 1 KiB so HTML error pages don't pollute
the audit log.

## Result → finding mapping

The mapping is opinionated: from the SOC's perspective, the
*executed* outcome is the bad one because it represents a missing
detection. The defaults:

| `EmulationOutcome` | `Severity` |
| --- | --- |
| `EXECUTED` (no defender block) | High |
| `BLOCKED` | Info (positive evidence) |
| `ERROR` / `TIMEOUT` | Low |
| `PRECONDITION_FAILED` / `SKIPPED` | (no finding) |

Findings carry the plan_id, step_index, agent_id, and bounded
stdout/stderr excerpts (512 chars each). Larger artefacts go to the
audit object store and are referenced by URL in
`EmulationResult.artifacts`.

## Wiring residues

The plumbing here is complete; the orchestrator wiring still needs:

- A `/red-agent/emulation/plans` REST surface.
- An approval workflow that flips `EmulationPlan.reviewed_by` and
  signs the plan via the policy-bundle pipeline.
- A daemon-side `RunEmulationStep` gRPC command + executor branch.
- Per-step audit events (`emulation.step.executed`,
  `emulation.step.blocked`).
- A "Detection coverage" UI panel correlating
  `techniques_unblocked()` with the SIEM detections (purple-team
  reporting).

## Roadmap

- Detection coverage report: correlate per-technique outcomes with
  SIEM-side detection logs (Splunk / Elastic / Sentinel).
- Atomic Red Team mirror auto-update CI job.
- Caldera planner selection per-engagement.
- Forensic-capture flag (one-shot opt-out of `always_run_cleanup`)
  with a separate audit event.
