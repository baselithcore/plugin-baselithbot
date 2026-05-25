# LLM reasoning planner

The Red Agent ships two attack-planner backends:

| Backend                 | When                                              |
| ----------------------- | ------------------------------------------------- |
| `DeterministicPlanner`  | default; runs the requested scanner set once      |
| `ChainingPlanner`       | `multi_step_chains=true`; chains DAST on new URLs |
| `LLMReasoningPlanner`   | `llm_planner_enabled=true`; Anthropic by default  |

The LLM planner is a **drop-in** replacement: the orchestrator loop
(`plan → critic.review → execute → ingest`) is unchanged. Only the
`.plan()` body differs. The critic still vets every step against scope,
exclusions, and intensity — the LLM is never trusted.

## Why two layers (planner + critic)

Keeping scope/exclusion/intensity enforcement inside the critic means
the LLM can propose an out-of-scope or above-cap step and the worst
case is a `scan.critic_veto` audit event — not an actual scan against
an unauthorized target. Defense in depth.

## Configuration

All knobs live in `RedAgentConfig` (env prefix `RED_AGENT_LLM_PLANNER_*`):

| Field                                     | Default          | Notes                                           |
| ----------------------------------------- | ---------------- | ----------------------------------------------- |
| `llm_planner_enabled`                     | `False`          | Master switch.                                  |
| `llm_planner_provider`                    | `anthropic`      | `anthropic` / `openai` / `ollama`.              |
| `llm_planner_model`                       | `claude-opus-4-7`| Reasoning-heavy default.                        |
| `llm_planner_max_tokens_per_scan`         | `50_000`         | Hard per-scan budget across all calls.          |
| `llm_planner_max_iterations`              | `8`              | Upper bound on iterations.                      |
| `llm_planner_max_tokens_per_call`         | `2048`           | Per-call generation cap.                        |
| `llm_planner_temperature`                 | `0.2`            | Low → deterministic chains.                     |
| `llm_planner_redact_secrets`              | `True`           | Strip credentials from findings before prompt.  |
| `llm_planner_fallback_to_deterministic`   | `True`           | Sticky fallback to `ChainingPlanner` on error.  |

Provider credentials are read from the standard core LLM configuration
(`BASELITH_ANTHROPIC_KEY` etc.) wrapped in `pydantic.SecretStr`. The
planner never touches the keys directly — it goes through
`core.services.llm.LLMService`, which already implements caching,
cost-control middleware integration, and circuit-breaker policy.

## Prompt contract

System prompt declares the role, the safety boundary (no tool use,
no scanner execution), and a JSON schema. Each turn the user payload
contains:

* `iteration`, `max_iterations`
* `initial_target` (`type` + `value`)
* `intensity_ceiling` (the engagement autonomy cap)
* `requested_scanners`, `enabled_scanners`
* `seen_endpoints`, `seen_services`
* `previous_findings` (last 20, **redacted**)
* `new_findings` (last 20, **redacted**)

The model returns:

```json
{
  "stop": false,
  "scanners": ["nuclei"],
  "target": { "type": "url", "value": "https://example.com" },
  "intensity": "active",
  "rationale": "Prior nmap finding exposed an HTTP service on :8080; rerun nuclei against it.",
  "derived_from": ["<finding-id>"]
}
```

`stop: true` (or any unparseable response) ends the chain. The planner
parses the JSON, hard-rejects intensities above the autonomy cap (audit
event `scan.planner_hypothesis` with `self_rejected: ...`), and hands
the step to the critic. From there, the existing pipeline takes over.

## Audit events

| Event                          | Emitted when                                                     |
| ------------------------------ | ---------------------------------------------------------------- |
| `scan.planner_llm_call`        | After every model call; carries provider, model, tokens.         |
| `scan.planner_hypothesis`      | After every parsed step (or self-rejection / stop).              |
| `scan.planner_llm_fallback`    | On parse error, provider error, or token-budget exhaustion.      |

The existing `scan.planner_step`, `scan.critic_veto`, and
`scan.critic_amended` events still fire downstream — nothing about the
critic flow changes.

## Fallback behavior

`LLMReasoningPlanner` wraps a deterministic fallback (default:
`ChainingPlanner` with the same `max_iterations`). Any of the following
flips a sticky fallback flag — every subsequent `plan()` call delegates
to the fallback for the rest of the scan:

1. Provider raises any exception (network, auth, rate limit).
2. Response is not valid JSON, or fails the schema check.
3. Cumulative token usage exceeds `llm_planner_max_tokens_per_scan`.

Setting `llm_planner_fallback_to_deterministic=false` makes those
failures end the chain immediately instead — the scan reaches
`COMPLETED` with whatever findings have already been ingested.

## What the LLM never sees

* Provider credentials of any kind.
* Raw scanner stdout (only normalized `Finding.evidence` fields).
* Sandbox internals (workdir paths, container IDs).
* Strings matching the redaction regex set: AWS access/STS keys,
  GitHub PATs/OAuth tokens, GitLab PATs, Slack tokens, Google API keys,
  generic `sk-…` keys, JWTs, PEM private-key headers.

## Disabling

Set `RED_AGENT_LLM_PLANNER_ENABLED=false` (the default) to revert. The
orchestrator picks `ChainingPlanner` when `multi_step_chains=true`,
otherwise `DeterministicPlanner`.
