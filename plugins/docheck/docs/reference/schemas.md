# Schemas Reference

JSON contract delle entità principali. Single source of truth: [docheck-shared-schemas/](../../docheck-shared-schemas/) + [docheck-engine/src/docheck/schemas/](../../docheck-engine/src/docheck/schemas/).

## Finding

Output canonico della pipeline di analisi. Schema: [finding.schema.json](../../docheck-shared-schemas/finding.schema.json) (JSON Schema draft 2020-12).

```json
{
  "id": "f-abc123",
  "severity": "FAIL",
  "rule_id": "GDPR-ART-32",
  "policy_ref": {
    "id": "GDPR-ART-32",
    "policy_id": "EU_GDPR_2018",
    "version": "1.0.0",
    "title": "Sicurezza del trattamento",
    "excerpt": "Il titolare del trattamento e il responsabile del trattamento mettono in atto misure tecniche e organizzative adeguate..."
  },
  "evidence": {
    "chunk_id": "doc-x__chunk-42",
    "page": 7,
    "line_start": 12,
    "line_end": 15,
    "bbox": [72.0, 540.0, 523.5, 588.0],
    "text": "Il fornitore non garantisce misure di sicurezza specifiche per i dati personali trattati."
  },
  "explanation": "La clausola identificata non specifica misure tecniche/organizzative come richiesto dall'art. 32 GDPR.",
  "suggestion": "Aggiungere riferimento esplicito a cifratura at-rest, pseudonimizzazione, e procedure di test/valutazione regolare.",
  "confidence": 0.84,
  "reasoning": [
    {
      "step": 1,
      "agent": "legal",
      "action": "retrieve_policy",
      "input": {"query": "sicurezza trattamento dati misure tecniche", "k": 5},
      "output": {"top_hits": ["GDPR-ART-32", "GDPR-ART-25"]},
      "thought": null
    },
    {
      "step": 2,
      "agent": "legal",
      "action": "verify",
      "input": {"chunk_id": "doc-x__chunk-42", "rule_id": "GDPR-ART-32"},
      "output": {"verdict": "FAIL", "confidence": 0.84},
      "thought": "Clausola non specifica misure adeguate."
    }
  ]
}
```

### Severity

| Valore | Significato |
|--------|-------------|
| `FAIL` | Violazione bloccante. Score impact: -8 punti. |
| `WARN` | Attenzione. Score impact: -3 punti. |
| `PASS` | Verifica positiva (raramente emesso, opt-in per visibility). |
| `INFO` | Nota informativa. Score impact: 0. |

### Confidence

`[0.0, 1.0]`. Convenzione:

- `1.0` solo per match deterministico (regex, numeric, format check).
- `≤ 0.85` per output LLM-based (semantic).
- `< 0.5` → tipicamente filtrato dal synthesizer.

### Glass-box constraint

Lato Pydantic engine ([schemas/finding.py](../../docheck-engine/src/docheck/schemas/finding.py)) validator aggiuntivi rispetto al JSON Schema:

- `policy_ref.excerpt` deve essere sub-string di un retrieval result (per agenti RAG).
- `evidence.bbox` non-null su PDF text-based / DOCX. Sintetico ammesso solo per TXT/MD.
- `reasoning` non-empty.

Vedi [explanation/glass-box.md](../explanation/glass-box.md).

## Report

Aggregato firmato di un'analisi.

```json
{
  "report_id": "r-abc123",
  "doc_id": "doc-xyz789",
  "score": 78,
  "by_severity": {"FAIL": 3, "WARN": 5, "PASS": 12, "INFO": 2},
  "findings": [/* array di Finding */],
  "policies_applied": ["DocCheck_Builtin", "EU_GDPR_2018", "MY_NDA_2026"],
  "chunks_evaluated": 142,
  "engine_errors": [],
  "engine_version": "0.1.0",
  "model_id": "llama-3.3-70b-instruct-q4_k_m",
  "embedding_model": "BAAI/bge-m3",
  "signed_at": "2026-05-04T10:23:45.123Z",
  "signature": "ed25519:<hex>"
}
```

### Score

`max(0, 100 - FAIL*8 - WARN*3)`. Punteggio compliance globale 0-100.

### Signature

Ed25519 firmato sul `payload` canonico (sort_keys=True, separators=(",", ":")). Public key da `GET /api/v1/info/pubkey`.

Verifica esterna:

```python
from nacl.signing import VerifyKey
import json

verify_key = VerifyKey(bytes.fromhex(public_key_hex))
payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
verify_key.verify(payload_bytes, bytes.fromhex(signature.removeprefix("ed25519:")))
# raises BadSignatureError se invalido
```

## Policy

```json
{
  "id": "EU_GDPR_2018",
  "version": "1.0.0",
  "title": "Regolamento UE 2016/679 (GDPR)",
  "scope": "eu",
  "lang": "it",
  "active": true,
  "rule_count": 42,
  "system": false
}
```

### Campi

- `id` — slug stabile, lowercase + underscore preferito. Unique.
- `version` — SemVer. `(id, version)` chiave composita.
- `scope` — `world` | `eu` | `it` | `custom`.
- `lang` — ISO 639-1 (`it`, `en`, ...).
- `active` — solo una versione `active=true` per `id`.
- `system` — `true` solo per built-in `DocCheck_Builtin` (read-only).

### Rule

```json
{
  "id": "GDPR-ART-32",
  "policy_id": "EU_GDPR_2018",
  "policy_version": "1.0.0",
  "rule_type": "semantic",
  "severity": "FAIL",
  "excerpt": "Il titolare del trattamento e il responsabile...",
  "matcher": "misur[ae]\\s+tecnich[ae]|cifratur[ae]",
  "title": "Misure tecniche e organizzative adeguate",
  "default_confidence": 0.8,
  "system": false,
  "enabled": true
}
```

`rule_type`: `semantic` (LLM RAG) o `deterministic` (regex/numeric/format). `matcher` opzionale: regex per pre-filter veloce.

## CheckState (interno LangGraph)

Schema: [docheck-engine/src/docheck/schemas/state.py](../../docheck-engine/src/docheck/schemas/state.py).

```python
class CheckState(TypedDict, total=False):
    doc_id: str
    lang: str
    chunks: list[Chunk]
    structure: list[StructureNode]
    selected_policies: list[str]
    findings: list[Finding]
    final_findings: list[Finding]
    score: int
    by_severity: dict[str, int]
    trace: list[ReasoningStep]
    errors: list[str]
    doc_type: str
    doc_type_confidence: float
```

Solo backend, non esposto via API.

## AuditEntry

```json
{
  "seq": 142,
  "ts": "2026-05-04T10:23:45.123Z",
  "tenant_id": "default",
  "user_id": "u-admin",
  "action": "analyze",
  "resource": "document:doc-xyz789",
  "payload_hash": "<sha256-hex>",
  "prev_hash": "<sha256-hex>",
  "entry_hash": "<sha256-hex>",
  "signature": "ed25519:<hex>"
}
```

`payload` originale recuperabile via `GET /api/v1/audit/{seq}` (con permission `audit:read`).

## Decision

Override umano su un finding (workflow di review).

```json
{
  "report_id": "r-abc123",
  "finding_id": "f-abc123",
  "decision": "accept" | "reject" | "defer",
  "rationale": "Falso positivo: contesto è esempio template.",
  "decided_by": "u-compliance-1",
  "decided_at": "2026-05-04T11:00:00Z"
}
```

Audit-loggato. Non modifica il `Finding` originale (immutabile post-firma).

## Vedi anche

- [api/endpoints.md](../api/endpoints.md) — endpoints CRUD per ogni entità.
- [explanation/glass-box.md](../explanation/glass-box.md) — perché Finding ha questi campi.
- [docheck-shared-schemas/](../../docheck-shared-schemas/) — JSON Schema source.
