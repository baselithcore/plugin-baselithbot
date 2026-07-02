# NL2SQL pipeline

Translates a natural-language question into a validated, executable query in the target dialect. Same code path for SQL, Cypher, MongoDB ops, Redis commands, Elasticsearch DSL, Qdrant ops, and Salesforce SOQL — only the prompt notes and safety validator vary.

## Provider strategy

Three providers, all interchangeable. Default is local Ollama so nothing leaves the host.

| Provider                      | Adapter                | API                          | Notes                                                           |
| ----------------------------- | ---------------------- | ---------------------------- | --------------------------------------------------------------- |
| `ollama` (default)            | `OllamaAdapter`        | chat                         | Any chat-tuned model. JSON output mode forced.                  |
| `ollama` + `sqlcoder:*` model | `SqlcoderAdapter`      | completion                   | sqlcoder uses a custom prompt template; chat API not supported. |
| `openai`                      | `GenericRemoteAdapter` | Vercel AI SDK `generateText` | Default model `gpt-4o-mini`.                                    |
| `anthropic`                   | `GenericRemoteAdapter` | Vercel AI SDK `generateText` | Default model `claude-sonnet-4-6`.                              |

Selection happens in [apps/api/src/nl2sql/llm/factory.ts](../apps/api/src/nl2sql/llm/factory.ts). Temperature is hardcoded to `0`. The client picks `provider`, `model`, and (for Ollama) `ollamaBaseUrl` per request.

## Pipeline

```
POST /api/nl2sql { connectionId, prompt, provider, model? }
        │
        ▼
1. Load connection → decrypt connection string in-memory
2. Introspect schema → UnifiedSchema (cached unless ?refresh=1)
3. compactSchema(schema)     ── dialect-specific minimal representation
4. buildSystemPrompt(...)    ── dialect notes + schema + JSON-only rule
5. buildUserPrompt(prompt)   ── NL question + retry feedback (if any)
6. llm.complete()            ── ollama / openai / anthropic
7. parseJson(output)         ── ModelOutputError on bad JSON
8. sanitize(query)           ── placeholder fix, ellipsis strip, prefix cleanup
9. validateAndAnnotate(...)  ── safety validator + alias auto-correction
   ├── on safety / unknown error → build suggestions, retry (≤ MAX_RETRIES)
   └── on success → emit dbview_llm_calls_total + latency + tokens
        │
        ▼
{ query, language, explanation, warnings, involvedEntities }
```

Implementation lives under [apps/api/src/nl2sql/](../apps/api/src/nl2sql/).

## Prompt construction

System prompt sections:

1. **Dialect notes** — syntax differences. Postgres uses `ILIKE`, MSSQL uses `TOP n` instead of `LIMIT`, Oracle uses `FETCH NEXT n ROWS ONLY`, etc. SOQL: no `JOIN`, no `*`. Cypher: no `WRITE` keywords.
2. **Schema digest** — compact form of tables/columns/FKs (relational), labels/relationships (graph), collections (Mongo/Qdrant), sObjects/fields (Salesforce), etc.
3. **Output contract** — strict JSON with `query` and optional `explanation` and `involvedEntities`. No markdown fences, no trailing prose.

User prompt is the raw natural-language question, optionally prefixed with retry feedback (see below).

## Retry loop

The pipeline burns up to `MAX_RETRIES + 1` LLM calls.

- Configured via `DBVIEW_NL2SQL_MAX_RETRIES`, clamped to `0..4`, default `2`.
- Triggered on:
    - JSON parse failure (`ModelOutputError`).
    - Safety validator failure (`UnsafeSqlError`).
    - Unknown table / column / label / sObject / field.

On retry, the user prompt includes a feedback block listing each unknown identifier and up to three nearest candidates from the schema, ranked by Levenshtein distance with a `<= 40%` distance-to-length ratio. See [apps/api/src/nl2sql/grounding/suggest.ts](../apps/api/src/nl2sql/grounding/suggest.ts).

Example retry feedback:

```
Your previous query referenced unknown identifiers:
  - table `customers` — did you mean `customer`?
  - column `revenue_total` — did you mean `total_revenue`, `revenue`?
```

## Sanitizer

Deterministic post-processing before validation, in [apps/api/src/nl2sql/grounding/sanitize.ts](../apps/api/src/nl2sql/grounding/sanitize.ts). No LLM in the loop.

- Replace literal placeholders (`LIMIT ?`, `LIMIT {rowLimit}`, `TOP ?`, `FETCH NEXT ? ROWS ONLY`) with the actual numeric `rowLimit`.
- Strip trailing ellipses and stray alphabetic noise (`SELECT id, name FROM customer LIMIT 5 ...`).
- Remove bogus schema prefixes for SQLite (where `database.schema` doesn't apply).

## Alias auto-correction

Deterministic fixup that runs _during_ validation, not after. Avoids a retry round-trip.

When a column reference like `il.InvoiceDate` doesn't resolve on `InvoiceLine` aliased `il`, the validator checks every other aliased table in the same statement. If `InvoiceDate` exists on **exactly one** other table (say `Invoice` aliased `i`), the validator rewrites `il.InvoiceDate` to `i.InvoiceDate` and emits a warning `auto_corrected_column_alias`.

If the column exists on zero or more than one other table, no auto-correct; the validator emits an unknown-column warning and the retry loop picks it up.

See [packages/sql-core/src/safety/validator.ts](../packages/sql-core/src/safety/validator.ts).

## Conversation mode

`POST /api/nl2sql/ask` accepts an array of prior turns (`ChatTurn[]`). The system prompt is unchanged; the user prompt is built from the cumulative conversation, with the latest question last. Useful for follow-ups like _"Now group those by month"_.

## Explanation & summarization

`apps/api/src/nl2sql/explainer.ts` and `summarizer.ts` provide secondary LLM calls:

- **Explain** — given a generated query, returns plain-English commentary. Uses `*_MODEL_EXPLAIN` envs to allow a cheaper model. Default Anthropic: `claude-haiku-4-5-20251001`.
- **Summarize** — condenses a long result set into a short natural-language paragraph.

Both are emitted as `dbview_llm_calls_total{mode="explain"|"summarize"}` for cost tracking.

## Metrics emitted

Every LLM call increments:

- `dbview_llm_calls_total{provider, model, mode, status}`
- `dbview_llm_call_latency_seconds{provider, model, mode}`
- `dbview_llm_tokens_total{provider, model, type=input|output}` (when the provider returns token counts)

`status="error"` covers provider exceptions; safety-validator rejections after exhausting retries are bubbled as `UnsafeSqlError` (HTTP 400) and don't count as LLM errors.

## Failure modes

| Failure                             | HTTP | Code                                 |
| ----------------------------------- | ---- | ------------------------------------ |
| Provider unreachable / timeout      | 502  | `llm_provider_error`                 |
| JSON parse failed after retries     | 422  | `model_output_error`                 |
| Safety rule violation after retries | 400  | `unsafe_sql` (or dialect equivalent) |
| Unknown identifiers after retries   | 400  | `unknown_identifiers`                |
| Rate limit exceeded                 | 429  | `rate_limit_exceeded`                |
