# ADR-0014: Coverage report on policy ingest

**Status:** Accepted
**Date:** 2026-05-14
**Authors:** giovanni ippolito <g.ippolito@gdservices.tech>

## Context

Dopo ADR-0013 (chunked extraction) il pipeline di ingest LLM produce un
insieme di regole verbatim-grounded a partire dal sorgente. L'utente non
esperto, però, non ha alcun segnale per giudicare se l'estrazione ha
catturato **tutti** gli obblighi del testo o solo una frazione: il numero
di regole estratte da solo non è informativo (5 regole possono essere
ottime su un contratto breve e pessime su un Codice).

Conseguenza concreta: l'utente carica una policy ("Codice degli Appalti"),
vede 7 regole estratte, accetta — senza sapere che il sorgente conteneva
~40 obblighi distinti e che il sistema controllerà solo 7/40.

Vincoli:

- Glass Box (CLAUDE.md §5): qualsiasi conteggio mostrato all'utente deve
  essere riconducibile a substring verbatim del sorgente. No counters
  fabbricati dall'LLM.
- Determinismo: temperature=0, riproducibile.
- Costo: aumento del token budget per ingest accettabile (operazione rara,
  on-prem).

## Decision

Sull'happy path di `services.policy_ingest.ingest`, dopo l'estrazione
delle regole, eseguire un **secondo passaggio LLM dedicato alla coverage**
che enumera tutti gli obblighi/divieti/requisiti distinti rilevati nel
sorgente con il loro excerpt verbatim. Sul risultato:

1. Validare ogni elemento detected con la medesima logica grounding
   (`_enforce_excerpts` su source_text completo).
2. Confrontare gli excerpt detected con gli excerpt delle regole estratte:
   `match` se l'excerpt detected è loose-contenuto in almeno un excerpt
   extracted (o viceversa).
3. Computare:
   - `extracted_count` = numero regole grounded estratte.
   - `detected_count` = numero obblighi grounded rilevati nel pass coverage.
   - `coverage_ratio` = `extracted_count / max(1, detected_count)`,
     clamped a `[0, 1]`.
   - `gaps[]` = elenco (max 20) di detected non matched dalle estratte;
     ciascun gap espone `{label, excerpt, severity_hint}`. Glass Box: ogni
     excerpt è verbatim substring del sorgente.
4. Restituire il blocco `coverage` come parte della response degli
   endpoint `POST /api/v1/policies/ingest/url` e
   `POST /api/v1/policies/ingest/document` (nuovo response model
   `IngestPolicyOut = PolicyOut + coverage?`). Endpoint pre-esistenti
   restano su `PolicyOut` invariato.
5. Per sorgenti lunghi (chunked path, ADR-0013) la coverage pass viene
   eseguita per chunk e merged con dedup excerpt-based.
6. Coverage **non** è persistito sul modello `Policy` in questa ADR:
   resta solo nella response dell'ingest + log strutturato
   `policy_ingest.coverage_report`. Persistenza è un follow-up.
7. Soft-fail: se la coverage pass solleva eccezione LLM, l'ingest
   prosegue ugualmente, `coverage=None` viene restituito e
   `policy_ingest.coverage_failed` viene loggato. La coverage è
   informativa, **non** un gate sull'ingest.

## Consequences

### Positive

- Segnale immediato per l'utente non esperto: "estratte 7 su 40 = 18%
  coverage" rende esplicito che la policy è incompleta.
- Gap list operazionale: utente può creare manualmente regole sui detected
  mancanti, oppure azionare il loop "suggerisci ancora" (PR3 / ADR
  futuro).
- Soft-fail: zero impatto sulla disponibilità dell'ingest se LLM ha hiccup.

### Negative / Trade-off

- Costo token raddoppiato per ingest (chunked: ~2N call invece di N).
  Accettabile su DGX on-prem, non metered.
- Coverage ratio è una stima: dipende dalla capacità dell'LLM di
  enumerare. Documentato come "stima" nella UI, non come metrica esatta.
- Possibili falsi positivi nei gap (LLM elenca obblighi presenti ma
  coperti da un'altra regola con wording diverso). Mitigato dal match
  loose substring; residuo accettabile.

### Neutral

- Nessuna migration DB. La response degli endpoint cambia ma in modo
  additivo (campo opzionale) → compatibile con client esistenti.

## Alternatives considered

### Opzione A — Persistere coverage sul modello Policy

Posticipata: richiede migration Alembic e UI per visualizzazione
storica. Far prima il loop informativo + raccogliere feedback utente.

### Opzione B — Embedding-based coverage (no second LLM call)

Scartata per ora: avrebbe bisogno di un corpus annotato di
"obbligazione canonica" per ogni framework, fuori scope MVP. Il second
LLM pass è più semplice e sfrutta lo stesso runtime già in piedi.

### Opzione C — Counter euristico via regex

Scartata: regole moderne (codici, contratti) usano linguaggio troppo
vario; regex produrrebbe stime grossolane non utili come segnale.

## Implementation notes

- Nuovo modulo: `docheck-engine/src/docheck/services/policy_coverage.py`.
- Modifica orchestration: `docheck-engine/src/docheck/services/policy_ingest.py`.
- Nuovo response model: `IngestPolicyOut` in
  `docheck-engine/src/docheck/api/policies.py`, applicato agli endpoint
  `ingest/url` e `ingest/document`.
- Test: `docheck-engine/tests/test_policy_coverage.py`.
- Telemetria: `policy_ingest.coverage_report`,
  `policy_ingest.coverage_failed`.

## References

- ADR-0013 chunked extraction.
- CLAUDE.md §5 Glass Box.
