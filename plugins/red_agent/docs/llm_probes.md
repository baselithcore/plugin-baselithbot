# LLM-attack probes (active scanners)

Active probes targeting AI / LLM-backed applications. Each scanner
walks a curated payload corpus, sends one request per payload to the
target chat endpoint via the sandboxed curl image, parses the
response, and emits a redacted `Finding` per detected outcome.

| Scanner                   | OWASP            | CWE (default) | Corpus                       |
| ------------------------- | ---------------- | ------------- | ---------------------------- |
| `llm_prompt_injection`    | LLM01            | CWE-1426      | `injection.yaml` (20+ items) |
| `llm_tool_abuse`          | LLM07 + LLM08    | CWE-1426      | `tool_abuse.yaml` (6 items)  |
| `llm_data_leakage`        | LLM06            | CWE-200       | `data_leakage.yaml` (5 items)|
| `llm_output_handling`     | LLM02            | per-payload   | `output_handling.yaml` (6)   |

`llm_recon` (passive fingerprinter) is the recon companion — run it
first to confirm the target really is LLM-backed before spending
budget on the active probes.

> **RAG poisoning (LLM03)** is deferred. It needs corpus access to
> the target retrieval store; we will not ship a generic probe.

## When the probes are allowed to run

* Engagement `autonomy_level` >= `execute_active` (the existing
  Rules-of-Engagement engine enforces this — we do not bypass it).
* Scan request `intensity` is `ACTIVE` or `INTRUSIVE`. Each scanner
  early-returns an empty finding list when called with `PASSIVE`.
* HITL approval was granted (or `require_human_approval=false` on
  the engagement, which is operator opt-out).
* Engagement metadata declares the target chat endpoint and (if
  applicable) a sentinel string the operator planted in the system
  prompt at engagement setup.

## Configuring the target

`Target.metadata` carries the LLM-app shape. Default values let an
unauthenticated OpenAI-compatible endpoint work out of the box.

```yaml
target:
  type: url
  value: "https://llm.example.com/v1/chat/completions"
  metadata:
    chat_endpoint: "https://llm.example.com/v1/chat/completions"
    request_template:
      model: "claude-haiku-4-5"
      messages:
        - { role: "user", content: "{prompt}" }
    response_path: "choices.0.message.content"
    auth_header_name: "Authorization"
    auth_token: "Bearer ${LLM_APP_TOKEN}"   # SecretStr in practice
    system_prompt_sentinel: "ENG-9001-SECRET"
    rate_limit_seconds: 1.0
    max_consecutive_5xx: 5
    max_consecutive_refusals: 10
```

The string `{prompt}` in `request_template` is replaced per-call;
the literal `{{SENTINEL}}` placeholder anywhere in a payload's
`prompt` or `detect.*` markers is replaced with `system_prompt_sentinel`.

## Detection model

Three outcomes per payload, evaluated in priority order:

1. **`leaked`** — response contains the sentinel or another marker
   indicating the system prompt / private context bled through.
2. **`tool_misfire`** — response contains a function/tool-call
   marker; the model tried to invoke a capability without
   authorization.
3. **`bypassed`** — response contains harmful content the model was
   supposed to refuse. **Suppressed when refusal markers fire** so a
   polite "I cannot help with that — DAN-OK is just a meme" does not
   trip a false positive.

`refusal_markers` per payload override the default set
(`I cannot`, `I won't`, `I'm sorry, but`, `as an AI`, etc.).

## Hard safety rules

| Rule                       | Enforcement                                                           |
| -------------------------- | --------------------------------------------------------------------- |
| Sandbox isolation          | Every request runs through `SandboxRunner` (sandboxed `curl`).        |
| Argv-only invocation       | No shell interpolation anywhere — `subprocess_exec` with arg list.    |
| Rate limit                 | `rate_limit_seconds` (default 1.0) between requests.                  |
| Consecutive-5xx halt       | `max_consecutive_5xx` (default 5) — protects production endpoints.    |
| Hardened-target halt       | `max_consecutive_refusals` (default 10) — model refuses every probe.  |
| No real PII in payloads    | Curated corpora use synthetic markers / sentinels only.               |
| Request + response redact  | `Finding.evidence` runs through the same secret-redaction filter as the planner before persistence. |

## Audit trail

Each detected outcome emits a standard `scan.finding_inserted` event
with the redacted evidence blob. The Sigma exporter ships the
redacted view (the raw response stays in scanner logs only).

## Adding new probes

1. Drop a new YAML into `plugins/red_agent/scanners/llm_payloads/`.
2. Either reuse an existing scanner module by extending its corpus,
   or create a thin scanner that calls
   `_llm_probe.run_probes(corpus_filename=...)`.
3. Write payload-corpus parser tests + at least one mocked-sandbox
   integration test. No live LLM in CI.
4. Update this document and `ARCHITECTURE.md` if the scanner introduces
   a new outcome category.

## Payload provenance + license

Every payload entry carries `source.name` and `source.license`. The
shipped corpora are SPDX-clean: `Apache-2.0` (internal + garak) and
`MIT` (promptmap). Do not add payloads under a license that prevents
redistribution.
