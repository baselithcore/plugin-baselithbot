# 4. Data Flow + Schema JSON Report

## 4.1 Event Flow End-to-End

```
upload
  → virus scan stub
  → mime detect
  → parse + OCR (PaddleOCR se scan)
  → chunk + embed (BGE-M3)
  → policy retrieval (ChromaDB)
  → multi-agent check (LangGraph)
  → synthesis (dedup + score)
  → audit log (append-only, hash-chained)
  → render WS streaming
  → export signed report (Ed25519)
```

Ogni step emette evento WebSocket consumato da UI per progress bar e streaming findings.

## 4.2 Schema Finding (Canonico)

```json
{
  "report_id": "uuid-v4",
  "doc": {
    "id": "doc-uuid",
    "name": "contratto_fornitore_v3.pdf",
    "sha256": "abc123...",
    "lang": "it",
    "pages": 24
  },
  "policies_applied": ["IT_GDPR_2026@v3", "Custom_NDA_v2"],
  "score": 78,
  "summary": "Documento sostanzialmente conforme. Rilevate 3 violazioni critiche su retention dati e foro competente.",
  "by_severity": { "FAIL": 3, "WARN": 5, "PASS": 42 },
  "findings": [
    {
      "id": "f-001",
      "severity": "FAIL",
      "policy_ref": {
        "id": "GDPR-Art-13",
        "policy_id": "IT_GDPR_2026",
        "version": "3.0.0",
        "title": "Informativa interessati",
        "excerpt": "Il titolare informa l'interessato del periodo di conservazione dei dati personali..."
      },
      "evidence": {
        "chunk_id": "c-42",
        "page": 7,
        "line_start": 142,
        "line_end": 145,
        "bbox": [120, 340, 480, 410],
        "text": "I dati saranno trattati per finalità contrattuali."
      },
      "explanation": "Manca informativa periodo di conservazione dati (Art. 13.2.a GDPR).",
      "suggestion": "Aggiungere clausola conservazione dati con periodo specifico (es. '24 mesi dalla cessazione del rapporto').",
      "reasoning": [
        {
          "step": 1,
          "agent": "LegalComplianceAgent",
          "action": "retrieve_policy",
          "input": { "query": "informativa retention", "policy_scope": "IT_GDPR" },
          "output": { "rule_ids": ["GDPR-Art-13", "GDPR-Art-5"] }
        },
        {
          "step": 2,
          "agent": "LegalComplianceAgent",
          "thought": "chunk c-42 menziona finalità ma non periodo conservazione richiesto da Art.13.2.a"
        },
        {
          "step": 3,
          "agent": "LegalComplianceAgent",
          "action": "check_clause_presence",
          "input": { "clause_type": "data_retention" },
          "output": { "present": false }
        }
      ],
      "confidence": 0.92
    }
  ],
  "audit": {
    "user_id": "user-uuid",
    "user_email": "g.ippolito@gdservices.tech",
    "ts": "2026-05-03T10:12:00Z",
    "engine_version": "0.1.0",
    "model": "llama-3.3-70b-q4km",
    "embedding_model": "bge-m3"
  },
  "signature": "ed25519:base64-sig..."
}
```

## 4.3 Caching Strategy

| Cache | Key | Value | Invalidation |
|-------|-----|-------|--------------|
| `embedding_cache` | `sha256(text) + model_id` | Chroma vector ref | Model change |
| `policy_index_cache` | `policy_id + version` | Chroma collection | Policy version bump |
| `verdict_cache` | `sha256(chunk) + rule_id + rule_version + model_id` | Finding JSON | Rule version bump |

Cache hit ratio target ≥ 60% su workload tipico (riesecuzioni e doc simili).

## 4.4 Validation Layers

1. **Input validation** — Pydantic su request FastAPI (mime, size cap 50MB MVP).
2. **Agent output validation** — Pydantic schema per ogni nodo. Reject finding senza `evidence.bbox` o `policy_ref.excerpt`.
3. **Report final validation** — JSON Schema completo prima firma Ed25519.
4. **Signature validation** — chain Ed25519 verificabile post-export con public key esposta.

## 4.5 WebSocket Events (UI streaming)

```typescript
type WSEvent =
  | { type: "phase",   phase: "parsing"|"indexing"|"analyzing"|"synthesizing"|"done"|"error" }
  | { type: "progress", current: number, total: number, label?: string }
  | { type: "finding",  finding: Finding }
  | { type: "trace",    step: ReasoningStep }
  | { type: "report",   report: Report }
  | { type: "error",    code: string, message: string }
```

UI consuma stream → aggiorna findings list progressivamente, animazione fade-in card.

## 4.6 Export Report

- Formati: PDF (con highlight rendering), Markdown, JSON canonico.
- Firma Ed25519 inclusa in metadata PDF (`/Sig` field) e JSON `signature`.
- Hash documento originale (sha256) embedded per non-ripudio.
- Verifica esterna possibile via `docheck verify report.pdf --pubkey ...`.
