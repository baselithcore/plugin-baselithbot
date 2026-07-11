# Ask (NL → Query)

Type a question in plain English; dbview returns a validated, dialect-native
query. The same pipeline serves SQL, Cypher, MongoDB operations, Redis
commands, Elasticsearch DSL, Qdrant operations and SOQL — only the prompt
notes and the safety validator vary by dialect.

## Providers

Three interchangeable providers, selected per request:

| Provider | Notes |
|---|---|
| **Ollama** (default) | Local, chat-tuned model (`codellama:7b` by default) — nothing leaves the host. |
| **OpenAI** | Optional, needs `OPENAI_API_KEY`. |
| **Anthropic** | Optional, needs `ANTHROPIC_API_KEY`. |

Temperature is fixed at `0` for determinism. Pick provider/model from the Ask
panel's selector.

Deployment **defaults** (provider credentials/endpoint and default models) can
be centrally pinned by an operator from the auth console — per pipeline, via
the `nl2sql` and `explain` LLM scopes; your explicit per-request choice in the
Ask panel always wins. See
[Configuration → Central LLM governance](../reference/configuration.md#central-llm-governance-auth-console).

## What happens on generate

1. The connection's schema is introspected (cached unless refreshed) and
   compacted into a dialect-specific digest.
2. A system prompt combines dialect notes, the schema digest, and a
   strict "JSON only, no prose" output contract.
3. The model returns `{ query, explanation, involvedEntities }`.
4. A deterministic sanitizer fixes placeholder artifacts (`LIMIT ?` →
   `LIMIT 5000`, stray ellipses, bogus schema prefixes) — no LLM involved.
5. The **safety validator** checks the query against the real, introspected
   schema (see [Query, results & history](query-results-history.md#safety)).
   Unknown tables/columns/labels/fields trigger **one retry** (configurable,
   `DBVIEW_NL2SQL_MAX_RETRIES`, default 2) with feedback naming the nearest
   valid identifiers by edit distance.
6. On success you get the query, an explanation, warnings (if any), and the
   entities involved — which are also highlighted on the
   [schema graph](schema-graph.md).

## Conversation mode

Follow-up questions ("now group those by month") reuse the prior turns as
context — the system prompt is unchanged, only the user prompt accumulates the
conversation. Useful for iterative exploration without restating the whole
question each time.

## Explain & summarize

Two secondary, cheaper LLM calls are available: **Explain** turns a query back
into plain English commentary, and **Summarize** condenses a long result set
into a short paragraph. Both can use a distinct, cheaper model via the
provider's `*_MODEL_EXPLAIN` setting.

## When it can't produce a safe query

After exhausting retries, dbview returns a structured error rather than a
query it can't stand behind:

| Situation | What you see |
|---|---|
| Provider unreachable/timeout | Provider error |
| Model output isn't valid JSON | Output-parsing error |
| Safety rule violated even after retries | Rejected query, with the rule that failed |
| Identifiers still unknown after retries | Rejected query, with suggestions |

## Next

- Run what was generated and read the result →
  **[Query, results & history](query-results-history.md)**.
