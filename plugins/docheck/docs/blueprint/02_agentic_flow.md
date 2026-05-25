# 2. Flusso Agentico (LangGraph)

State machine deterministica. Ogni nodo agente emette `trace_event` consumato dal pannello Glass Box UI.

## 2.1 State Schema

```python
from typing import TypedDict, Literal
from pydantic import BaseModel

class Chunk(BaseModel):
    id: str
    text: str
    page: int
    line_start: int
    line_end: int
    bbox: tuple[float, float, float, float]   # x0,y0,x1,y1
    token_count: int

class StructureNode(BaseModel):
    id: str
    type: Literal["title","section","article","clause","table","signature"]
    label: str
    parent_id: str | None
    page: int
    line_start: int
    line_end: int
    chunk_ids: list[str]

class PolicyRef(BaseModel):
    id: str            # "GDPR-Art-13"
    policy_id: str     # "IT_GDPR_2026"
    version: str
    excerpt: str

class Citation(BaseModel):
    chunk_id: str
    page: int
    line_start: int
    line_end: int
    bbox: tuple[float, float, float, float]

class ReasoningStep(BaseModel):
    step: int
    agent: str
    action: str | None
    input: dict | None
    output: dict | None
    thought: str | None

class Finding(BaseModel):
    id: str
    severity: Literal["FAIL","WARN","PASS","INFO"]
    rule_id: str
    policy_ref: PolicyRef
    evidence: Citation
    explanation: str
    suggestion: str | None
    confidence: float
    reasoning: list[ReasoningStep]

class CheckState(TypedDict):
    doc_id: str
    lang: str
    chunks: list[Chunk]
    structure: list[StructureNode]
    selected_policies: list[str]    # policy ids @ versions
    findings: list[Finding]
    trace: list[ReasoningStep]
    errors: list[str]
```

Validazione Pydantic obbligatoria su output di ogni nodo. Findings senza `evidence` o `policy_ref.excerpt` rifiutati.

## 2.2 Graph Topology

```
            [START]
               │
               ▼
        ┌──────────────┐
        │ ParserAgent  │   PDF/DOCX/XLSX/MD → chunks con bbox
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │ Structurer   │   gerarchia articoli/clausole
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │   Router     │   determina agenti da invocare in parallelo
        └──┬───────┬───┘
           │       │       │
           ▼       ▼       ▼
        ┌─────┐ ┌─────┐ ┌─────┐
        │Legal│ │Tech │ │ PII │   (parallel branch)
        └──┬──┘ └──┬──┘ └──┬──┘
           └───┬───┴────┬──┘
               ▼
        ┌──────────────┐
        │ Synthesizer  │   dedup, score, summary
        └──────┬───────┘
               ▼
            [END]
```

## 2.3 Agenti

### ParserAgent

- Routing per mime-type: `pdfplumber` (PDF nativo), **PaddleOCR** (PDF scan, layout-aware tabelle), `python-docx` (DOCX con revisioni), `openpyxl` (XLSX), markdown-it (MD).
- Output: `chunks` con coordinate `{page, line_start, line_end, bbox}` per highlight UI preciso.
- Detection lingua chunk via `lingua-py` → popola `state.lang`.

### StructurerAgent (LLM)

- Prompt template `B.1` (vedi `07_prompt_templates.md`).
- Estrae gerarchia titoli/articoli/clausole numerate.
- Critico per riferimento "Art. 7.2 contratto".

### LegalComplianceAgent (ReAct + tools)

- RAG su policy IT/EU/world preindicizzate + custom.
- Tools:
    - `retrieve_policy(query, policy_scope, top_k=5)` → list di rule
    - `check_clause_presence(clause_type, chunks)` → bool + chunk_ids
    - `extract_obligation(text)` → list `{actor, obligation, deadline?}`
- Hard rules: NEVER inventare policy, citare verbatim.

### TechnicalComplianceAgent

- Deterministic-first: regex (codice fiscale, partita IVA, IBAN IT, email, date ISO), numeric limits (XLSX), format checks (font, header/footer markers, branding).
- Semantic fallback solo per regole tipo `presence` o `style`.

### PIIDetectorAgent (ensemble)

- Pipeline: regex → NER (`xlm-roberta-large-finetuned-conll03` locale) → LLM verifier per ridurre falsi positivi.
- Reject candidati in contesto "esempio", "placeholder", "registro pubblico".

### SynthesizerAgent

- Dedup findings (`chunk_id + rule_id` → keep highest confidence).
- Score: `100 - (FAIL*8 + WARN*3)` floor 0.
- Summary executive in `state.lang`, max 3 frasi, no nuovi claim.

## 2.4 Multilingua

- **Embedding:** BGE-M3 nativo IT + EN + 100+ lingue.
- **LLM:** Llama-3.3-70B Instruct supporta IT/EN solidi. Routing prompt template per lingua.
- **Detection:** chunk-level via `lingua-py`. Policy retrieval filtrato per lingua matching.
- **Fallback:** se documento IT ma policy solo EN → traduzione embedding cross-lingua via BGE-M3 (semantic match nativo).

## 2.5 Pre-caricamento Policy Default

Pacchetti seed indicizzati all'install:

**Tier 1 — IT (preselezionate)**

- `IT_GDPR_2026` — informativa, retention, base legale, DPIA
- `IT_Codice_Civile_Contratti` — recesso, foro competente, limitazioni responsabilità
- `IT_Codice_Consumo` — clausole vessatorie, diritto recesso B2C

**Tier 2 — EU (selezionabili)**

- `EU_GDPR_2016_679`
- `EU_AI_Act_2024`
- `EU_NIS2_Directive`

**Tier 3 — World (opt-in)**

- `ISO_27001_Annex_A`
- `NIST_CSF_2.0`
- `SOC2_Trust_Criteria`

## 2.6 Glass Box Garantita

Ogni `Finding` impone schema con:

- `evidence` (chunk_id, page, line_start/end, bbox) → click UI scroll+highlight
- `policy_ref.excerpt` verbatim (no parafrasi)
- `reasoning` chain (passi LLM con tool call log)

Validation Pydantic rifiuta finding non tracciabili → 1 retry con `repair_prompt`, poi failover deterministico (skip nodo, log warning, `state.errors`).

## 2.7 Guardrails Comuni

- `temperature=0.1`, `top_p=0.9`, `max_tokens` cap per nodo.
- JSON-mode forzato (vLLM grammar / outlines).
- Validation retry max 1, poi failover.
- Token budget: chunk text passato per riferimento `{chunk_id}` quando possibile, full text solo per agente attivo.
