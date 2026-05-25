# Agentic Flow

doCheck usa LangGraph per orchestrare una pipeline multi-agente con parallel fan-out e validazione strutturata.

## Topology

```
                  ┌──> legal ──┐
classifier → structurer ──┼──> technical ──┼──> synthesizer → END
                  └──> pii ────┘
```

Implementazione: [docheck-engine/src/docheck/agents/graph.py](../../docheck-engine/src/docheck/agents/graph.py).

## State

```python
class ParallelState(TypedDict, total=False):
    doc_id: str
    lang: str
    chunks: list[Chunk]
    structure: list[StructureNode]
    selected_policies: list[str]
    findings: Annotated[list[Finding], add]   # reducer-merged
    final_findings: list[Finding]              # synthesizer output
    score: int
    by_severity: dict[str, int]
    trace: Annotated[list[ReasoningStep], add]
    errors: Annotated[list[str], add]
    doc_type: str
    doc_type_confidence: float
    doc_type_low_confidence: bool
    doc_type_rationale: str
```

`Annotated[list[X], add]` permette merge concorrente sicuro fra branch paralleli (`legal`, `technical`, `pii` scrivono `findings` concorrentemente; LangGraph applica `operator.add` per concatenare).

## Per agente

### Classifier ([agents/classifier.py](../../docheck-engine/src/docheck/agents/classifier.py))

- Determina `doc_type` (es. `nda`, `privacy_policy`, `service_agreement`, `gdpr_dpa`) usando primi N chunks + LLM JSON-mode.
- Output: `{doc_type, doc_type_confidence ∈ [0,1], doc_type_rationale}`.
- Se confidence < threshold → `doc_type_low_confidence=true`, agenti downstream applicano logica conservativa.
- Vedi [ADR-0011 — Document type taxonomy](../adr/0011-document-type-taxonomy.md).

### Structurer ([agents/structurer.py](../../docheck-engine/src/docheck/agents/structurer.py))

- Estrae gerarchia (titoli, articoli, clausole numerate) via LLM JSON-mode.
- Output: `state.structure: list[StructureNode]` con `id`, `level`, `title`, `chunk_ids`.
- Permette agent downstream di referenziare unità semantiche invece di chunk crudi.

### Legal ([agents/legal.py](../../docheck-engine/src/docheck/agents/legal.py))

- RAG su policy IT/EU/world index.
- Tools: `retrieve_policy(query, k)`, `check_clause_presence(clause_pattern)`, `extract_obligation(text)`.
- Hard rule: cita SOLO excerpt restituiti dal retrieval. Sub-string match enforced lato Pydantic validator.
- Confidence ≤ 0.85 (semantic, mai 1.0).

### Technical ([agents/technical/](../../docheck-engine/src/docheck/agents/technical/))

Modulo splittato per LOC limit:
- `engine.py` — orchestratore.
- `patterns.py` — regex dictionary (codice fiscale, P.IVA, IBAN, date format, ecc.).
- `severity.py` — mapping severity per rule deterministica.
- `rules/` — moduli per famiglia di check (formato date, deadline strict, identificativi, ecc.).

Confidence `1.0` su match deterministico (regex/numeric). Severity può essere FAIL/WARN/INFO.

### PII ([agents/pii.py](../../docheck-engine/src/docheck/agents/pii.py))

Ensemble:
1. Regex pre-filter (nomi, email, telefoni, codici fiscali, ecc.) → candidati.
2. LLM verifier in JSON-mode → rifiuta candidati in contesto "esempio/placeholder/template" (riduce falsi positivi).

Output severity tipicamente `FAIL` (sensitive data) o `WARN` (esposizione potenziale).

### Synthesizer ([agents/synthesizer.py](../../docheck-engine/src/docheck/agents/synthesizer.py))

- Dedup `(chunk_id, rule_id) → max(confidence)` — evita duplicati cross-agent.
- Ordina per severity poi confidence.
- Calcola `score = max(0, 100 - FAIL*8 - WARN*3)`.
- Calcola `by_severity = {FAIL: n, WARN: n, PASS: n, INFO: n}`.
- Output finale: `final_findings`.

## Glass-box guarantee per agente

Ogni `Finding` (Pydantic model in [schemas/finding.py](../../docheck-engine/src/docheck/schemas/finding.py)) richiede:

```python
class Finding(BaseModel):
    id: str
    severity: Literal["FAIL", "WARN", "PASS", "INFO"]
    rule_id: str
    policy_ref: PolicyRef           # excerpt verbatim
    evidence: Evidence              # bbox + chunk_id + page
    explanation: str
    confidence: float
    reasoning: list[ReasoningStep]
```

Validator custom enforce:
- `evidence.bbox` non-null (eccezione: testo plain TXT/MD senza layout → `bbox = (0, line_start, page_width, line_end)` sintetico).
- `policy_ref.excerpt` substring di un retrieval result reale.
- `reasoning` chain non-empty.

Validation fail → repair retry (max 1) con prompt che mostra l'errore al LLM → se ancora fail, finding scartato + warning in `state.errors`.

## Eventi pipeline

Ogni agente emette eventi via [services/events.py](../../docheck-engine/src/docheck/services/events.py) → WebSocket `/ws/analysis/{doc_id}`:

```ts
type Event =
  | { type: "phase",    phase: "started" | "classifier" | "structurer" | "legal" | "technical" | "pii" | "synthesizer" | "done" | "error" }
  | { type: "progress", current: number, total: number, label?: string }
  | { type: "finding",  finding: Finding }
  | { type: "trace",    step: ReasoningStep }
  | { type: "report",   report_id: string };
```

Frontend consuma via hook [useAnalysisStream](../../docheck-ui/lib/useAnalysisStream.ts).

## Performance

Budget: < 90s P95 per doc 20pp su DGX Spark con `Llama-3.3-70B Q4_K_M`.

Ottimizzazioni:
- Parallel fan-out (3 agent concurrent).
- Verdict cache cross-document (`sha256(chunk_hash || rule_id || rule_version || model_id)`).
- Retrieval k contestuale (chunks evidence-relevant, no full-policy dump).
- BGE-M3 embedding pre-computed e indexato.

## Aggiungere un agente

1. Crea `agents/<name>.py` con `async def run(state: ParallelState) -> ParallelState`.
2. Registra in [graph.py](../../docheck-engine/src/docheck/agents/graph.py): `add_node` + `add_edge`.
3. Esporta in `agents/__init__.py`.
4. Output via Pydantic `Finding` (validation enforced).
5. Aggiungi prompt template in [blueprint/07_prompt_templates.md](../../blueprint/07_prompt_templates.md).
6. Test E2E in `tests/test_pipeline.py`.
7. Aggiorna `Event.phase` enum + UI `PhaseIndicator`.

## Vedi anche

- [ADR-0001 — LangGraph orchestration](../adr/0001-langgraph-agentic-orchestration.md).
- [ADR-0007 — Parallel fan-out](../adr/0007-parallel-fanout-langgraph.md).
- [glass-box.md](glass-box.md) — perché Finding ha questi campi.
- [modules/agents.md](../modules/agents.md) — reference rapida.
