# ADR-0001: LangGraph for Agentic Orchestration

**Status:** Accepted
**Date:** 2026-05-03

## Context

Pipeline compliance check richiede orchestrazione multi-agente verificabile (Parser → Structurer → Legal/Tech/PII → Synthesizer). Pillar Glass Box impone tracciabilità step-by-step ogni decisione LLM. State condiviso fra nodi con validazione tipata.

## Decision

Adottare **LangGraph** (parte ecosistema LangChain) come orchestratore.

- State machine deterministica con `StateGraph(CheckState)`.
- Nodi async, validazione Pydantic su output.
- Topologia attuale sequenziale: `structurer → legal → technical → pii → synthesizer`.
- Path verso parallelismo legal/tech/pii via fan-out branch in F2 late.

## Consequences

**Positive**
- Tracciabilità nativa: ogni transizione di stato osservabile (Glass Box).
- Tipizzazione TypedDict + Pydantic per state schema.
- Integrazione LangChain tools (`retrieve_policy` etc.).
- Compilazione statica grafo → topologia ispezionabile pre-runtime.

**Negative**
- Nuova dipendenza ecosystem (LangChain core + langgraph).
- Curva apprendimento per parallel branching.

## Alternatives Considered

- **Manual asyncio orchestration**: più semplice, perde routing/state primitives, dovremmo reimplementare retry/repair pattern.
- **Temporal/Prefect**: overkill per use case in-process, aggiunge worker infra.
- **CrewAI**: opinionated multi-agent, meno controllo deterministico, primato della pillar Glass Box richiede grafo esplicito.
