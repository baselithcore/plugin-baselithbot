# ADR-0007: LangGraph Parallel Fan-Out per Legal/Tech/PII

**Status:** Accepted
**Date:** 2026-05-03

## Context

MVP iniziale aveva pipeline sequenziale `structurer → legal → technical → pii → synthesizer`. Performance budget: analisi 20pp < 90s P95. Misurando profile baseline:

- Legal LLM call: ~30s (RAG + 70B reasoning)
- PII LLM verifier: ~10s
- Technical (regex deterministic): ~1s

Sequenziale → ~41s solo agent steps. Parallelizzando legal+pii+technical → max(30, 10, 1) = ~30s. Riduzione ~25%.

## Decision

Topology nuova:

```
structurer → [legal | technical | pii]  (concurrent)
                       ↓
                 synthesizer
```

**State schema con reducer** (`Annotated[list, add]`) per merge concorrente:

- `findings: Annotated[list[Finding], add]` — concat-only, dedup deferred a synthesizer
- `errors: Annotated[list[str], add]` — accumulo errori parallel
- `final_findings: list[Finding]` — output canonico post-dedup synthesizer

Agenti refactor: ritornano partial state delta `{"findings": [...nuovi]}` invece di mutare input. LangGraph reducer concat automatico.

## Consequences

**Positive**
- Latency reduction ~25% su workload tipico.
- Fault isolation: failure di un branch non blocca altri (retorna `errors` partial state).
- Synthesizer dedup garantisce idempotenza in caso double-run.

**Negative**
- WebSocket events possono arrivare interleaved (legal step 2 + pii step 1 mescolati). UI deve raggrupparli per agent name.
- Verdict cache invalidation più complessa (concurrent checks di stessi chunks).
- Mock test devono accumulate findings invece di mutate.

## Alternatives Considered

- **AsyncIO `gather` manuale**: bypassa LangGraph runtime → perdita Glass Box trace native + checkpointing.
- **Sequential con timeout**: non riduce latency, solo cap upper bound.
- **Process pool**: overhead serialization state grosso, non vale per Python in-process.

## Migration

- Routes consume `final_findings` se presente, fallback `findings` (backward compat).
- UI streaming: nuovo evento `phase` può arrivare 3x ravvicinato (3 agenti partono insieme).
