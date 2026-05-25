# Module: agents

Multi-agent compliance pipeline orchestrato via LangGraph.

## Topology (parallel fan-out)

```
structurer → [legal | technical | pii]  (concurrent)
                       ↓
                 synthesizer
```

Vedi [ADR-0007](../adr/0007-parallel-fanout-langgraph.md). Findings sono concat-merged via reducer; synthesizer dedup ed emette `final_findings` canonico.

Stato condiviso: [`CheckState`](../../docheck-engine/src/docheck/schemas/state.py).

## Agents

### structurer

Estrae gerarchia (titoli, articoli, clausole) via LLM JSON-mode. Output: `state.structure: list[StructureNode]`.

### legal

RAG su policy IT/EU/world. Tools: `retrieve_policy`, `check_clause_presence`, `extract_obligation`. Hard rule: cita SOLO excerpt restituiti da retrieval (no invenzioni).

### technical

Deterministic checks (regex, numeric limits, format). Confidence 1.0 su match, ≤0.85 su semantic.

### pii

Ensemble: regex pre-filter + LLM verifier. Riduce falsi positivi rifiutando candidati in contesto "esempio/placeholder".

### synthesizer

Dedup `(chunk_id, rule_id) → max(confidence)`. Score `100 - FAIL*8 - WARN*3` (floor 0).

## Adding a new agent

1. Crea `src/docheck/agents/<name>.py` con funzione async `run(state) -> state`.
2. Registra in [`graph.py`](../../docheck-engine/src/docheck/agents/graph.py) `add_node` + `add_edge`.
3. Esporta in `agents/__init__.py`.
4. Validazione output via Pydantic.
5. Aggiungi prompt template in [`07_prompt_templates.md`](../../blueprint/07_prompt_templates.md).
6. Test E2E in `tests/test_pipeline.py`.

## Guardrails

- `temperature=0.1`, `top_p=0.9`.
- Repair retry su validation fail (max 1).
- Failover deterministico: skip nodo, push errore in `state.errors`.
- Token budget: passa `chunk_id` per riferimento dove possibile.
