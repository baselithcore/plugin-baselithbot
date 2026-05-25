# ADR-0011: Document type taxonomy + classifier + conditional routing

**Status:** Accepted
**Date:** 2026-05-03

## Context

doCheck pipeline trattava ogni input come "contratto", ma il prodotto è un
revisore di conformità per **qualunque documento aziendale** soggetto a norme
(contratti, policy interne, procedure, DPIA, audit report ISO, manuali, spec
tecniche, regolamenti). Limiti del pipeline pre-ADR:

- Nessun campo `doc_type` su `Document`. Tipo non noto a runtime.
- `StructurerAgent` con tassonomia node-types hard-coded per contratti
  (`article`, `clause`, ...): inadatta per DPIA (`processing_activity`,
  `risk_assessment`), procedure (`step`, `prerequisite`), audit report
  (`control`, `evidence`).
- `LegalComplianceAgent` recupera policy via similarity senza filtrare per
  applicabilità al tipo di documento → cross-contamination (regole ISO 27001
  matchate su NDA, regole GDPR DPA matchate su manuale tecnico).
- `Policy` non dichiara su quali tipi documento si applica.
- Nessuna fase di classificazione documento all'ingest.

Best practice moderne (LayoutLMv3, Document AI, compliance pipelines 2025)
richiedono:

1. Document classification step **prima** di structuring/extraction.
2. Per-type taxonomy schema-guided extraction.
3. Policy applicability matrix (quali norme valgono per quale tipo).
4. Multi-framework awareness (GDPR, ISO 27001, NIS2, AI Act, ...) con tagging
   esplicito su policy.

## Decision

Adottare tassonomia documento + agente classifier + routing condizionale.

### Tassonomia (`DocType`)

Stringhe canoniche, lower-snake. Modulo `core/doc_taxonomy.py`:

```
contract              # contratti, NDA, MSA, DPA
policy                # policy interne, regolamenti, codici di condotta
procedure             # SOP, manuali operativi, runbook
dpia                  # DPIA / PIA, valutazioni di impatto
audit_report          # report di audit, certificazioni, attestazioni
manual                # manuali utente, guide tecniche
technical_spec        # specifiche tecniche, RFC, design doc
regulatory_text       # testi normativi (uso tipico: ingest come policy, non revisione)
other                 # fallback non classificato
```

### Node-type taxonomy per `DocType`

Mappa `DocType → list[node_type]` in `core/doc_taxonomy.py`. Structurer riceve
in prompt la sub-tassonomia applicabile invece di lista hard-coded.

### Classifier agent

Nuovo `agents/classifier.py`. LLM zero-shot su primo head di chunk (≤2k token),
emette `{doc_type, confidence, rationale}`. Confidence < 0.55 → `other` con
flag `low_confidence=true` (richiede HITL future).

Il classifier gira **prima** dello structurer, popola `state.doc_type`.

### Routing condizionale (graph)

Per MVP, fan-out parallelo ai 3 agent (legal, technical, pii) resta. Filtro
per `doc_type` applicato **all'interno** di ciascun agent (skip se non
applicabile) anziché skip nodo del graph: minor invasività, conserva merge
reducer findings.

Mappa default agent applicability:

```
contract        → legal, technical, pii
policy          → legal, pii
procedure       → technical, legal
dpia            → legal, pii, technical
audit_report    → legal, technical
manual          → technical
technical_spec  → technical
regulatory_text → (nessuno: input read-only per ingest, non target di review)
other           → legal, technical, pii (full fan-out)
```

### Policy applicability matrix

`Policy` ottiene due campi opzionali JSON:

- `applicable_doc_types: list[DocType]` (vuoto = tutti)
- `frameworks: list[str]` (e.g. `["GDPR","ISO27001"]`, vuoto = nessun tag)

`legal.retrieve_policy()` accetta `doc_type` e applica filtro:
`(applicable_doc_types is empty) OR (doc_type in applicable_doc_types)`.

### Schema state

`CheckState` e `ParallelState` aggiungono:

- `doc_type: str` (DocType value)
- `doc_type_confidence: float`
- `doc_type_low_confidence: bool`

### DB schema

Migration Alembic 0008:

- `documents.doc_type TEXT NULL` (default null per backward compat)
- `documents.doc_type_confidence REAL NULL`
- `policies.applicable_doc_types TEXT NULL` (JSON serialized)
- `policies.frameworks TEXT NULL` (JSON serialized)

Backfill: NULL = "unknown", trattato come `other`. Nessuna riscrittura record
esistenti.

## Consequences

**Positive**

- Pipeline coerente con qualunque documento di compliance.
- Cross-contamination policy ridotta via applicability matrix.
- Glass-box mantenuto: classifier emette `rationale` che entra nel reasoning
  trace.
- Routing flessibile: nuovi `DocType` aggiungibili senza riscrivere graph.
- Aderenza a best practice document-AI 2025 (classify-before-extract).

**Negative**

- +1 LLM call per documento (classifier) → +200ms tipici, +token cost.
- Possibile miss-classification → mitigato da confidence threshold + fallback
  `other` (full fan-out).
- Policy senza `applicable_doc_types` continuano ad applicarsi a tutti
  (compatibilità retroattiva). Migrazione esplicita in fase successiva.

**Alternatives considered**

1. *Skip node nel LangGraph in base a doc_type*: invasivo sul reducer dei
   findings; complica testing.
2. *Classification deterministica via euristica filename/MIME*: troppo
   fragile (`.pdf` non dice nulla del contenuto).
3. *Ontologia gerarchica multi-livello (DocType → SubType)*: over-engineering
   per MVP. Estendibile in ADR successiva.
4. *Multi-label classification (un doc può essere contract+dpia)*: rinviato.
   MVP sceglie singolo top-1.

## Follow-up

- Test set classifier su 50 documenti misti (target precision ≥ 0.85 sul tipo
  top-1).
- ADR successiva per HITL su `low_confidence`.
- ADR successiva per multi-framework cross-mapping (es. GDPR ↔ ISO 27701).
