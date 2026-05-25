# ADR-0013: Chunked policy extraction for long source texts

**Status:** Accepted
**Date:** 2026-05-14
**Authors:** giovanni ippolito <g.ippolito@gdservices.tech>

## Context

L'ingest LLM di policy (`services/policy_ingest.py`) opera su un singolo
prompt con cap `_MAX_TEXT_CHARS = 60_000` e tronca il sorgente con il marker
`[...TRUNCATED...]`. Conseguenze:

- Testi regolatori lunghi (Codice Civile, D.lgs. 50/2016 integrale, GDPR
  full text, contratti master) eccedono il cap → obblighi nelle sezioni
  finali vengono silenziosamente persi.
- L'utente non esperto non riceve alcun segnale che il contenuto è stato
  tagliato: la policy risulta povera di regole senza ragione apparente.
- Anche entro il cap, un singolo prompt troppo lungo degrada la qualità di
  estrazione (LLM tende a saltare sezioni o a duplicare le prime).

Vincoli:

- Glass Box (CLAUDE.md §5): ogni `excerpt` deve restare verbatim e
  rintracciabile nel sorgente. Niente summarization a monte.
- Determinismo (CLAUDE.md §5): temperature=0 + comportamento riproducibile.
- LLM on-prem (CLAUDE.md §3): vLLM su DGX Spark, finestra contesto limitata
  dal modello servito, no fallback su modelli cloud a larga finestra.

## Decision

Per sorgenti che superano `CHUNK_TRIGGER_CHARS = 40_000` caratteri:

1. **Splitter strutturato** (`services/policy_chunking.py`): split il testo
   su marcatori d'articolo / sezione (`Art. N`, `Articolo N`, `Article N`,
   `§ N`, `Section N`, `Sezione N`). Se nessun marker viene trovato,
   fallback su pack di paragrafi (`\n\n`) fino a `CHUNK_TARGET_CHARS = 20_000`.
2. **Estrazione per chunk**: ogni chunk viene passato al medesimo prompt
   LLM di estrazione (system+user invariati) → JSON con `rules`.
3. **Cap totale**: massimo `CHUNK_MAX_COUNT = 20` chunk per ingest. Eccesso
   viene fuso adiacente (merge greedy). Protegge da costi runaway.
4. **Merge + dedup**: l'unione delle regole estratte viene deduplicata per
   chiave `_normalize(excerpt)` (whitespace-collapse + lowercase). Prima
   occorrenza vince. Mantiene Glass Box: ogni `excerpt` resta verbatim
   substring di **almeno una** porzione del sorgente.
5. **Grounding invariato**: `_enforce_excerpts` continua a girare
   sull'intero `source_text` originale, non sui chunk. Nessuna regola può
   sopravvivere senza match verbatim sul sorgente completo.
6. **Telemetria**: log `policy_ingest.chunked_extraction` con
   `chunk_count`, `rules_per_chunk[]`, `dedup_drop`, `total_grounded`.

Path single-shot esistente (≤ trigger) resta invariato per
backward-compatibility.

## Consequences

### Positive

- Niente truncation silenziosa su policy lunghe.
- Copertura più uniforme: ogni sezione del sorgente riceve un prompt
  dedicato → meno bias verso le prime pagine.
- Telemetria per chunk rende diagnosticabile il calo qualità.
- Modulo `policy_chunking.py` testabile in isolamento (pure functions).

### Negative / Trade-off

- Latenza ingest cresce ~N× (N = chunk count). Bounded da `CHUNK_MAX_COUNT`.
- Token cost cresce ~N×. Accettabile: ingest è operazione rara e on-prem
  (no metered API).
- Possibili duplicati semantici tra chunk (stessa obbligazione menzionata
  in articoli diversi). Mitigato dal dedup excerpt-based; residuo è
  audit-safe perché ogni regola resta grounded.

### Neutral

- Niente cambio API pubblica: `ingest_from_url` / `ingest_from_document` /
  `ingest` mantengono signature.
- Niente migration DB. Tutto il chunking è in-memory durante l'ingest.

## Alternatives considered

### Opzione A — Aumentare `_MAX_TEXT_CHARS`

Scartata: degrada la qualità per via del contesto LLM saturato; non
risolve il problema oltre la finestra del modello servito.

### Opzione B — Summarization preliminare del sorgente

Scartata: viola Glass Box (l'`excerpt` non sarebbe più verbatim) e
introduce un layer di hallucination prima dell'estrazione.

### Opzione C — Estrazione parallela (asyncio.gather)

Posticipata: la versione sequenziale è più semplice da rendere
deterministica e da rate-limit. Parallelismo bounded può essere aggiunto
in un ADR successivo se la latenza diventa un problema misurato.

## Implementation notes

- Codice: `docheck-engine/src/docheck/services/policy_chunking.py` (nuovo),
  `docheck-engine/src/docheck/services/policy_ingest.py` (modifiche
  orchestration).
- Test: `docheck-engine/tests/test_policy_chunking.py`,
  `docheck-engine/tests/test_policy_ingest_chunked.py`.
- Telemetria: chiavi `policy_ingest.chunked_extraction`,
  `policy_ingest.chunk_extract_failed`.

## References

- CLAUDE.md §5 Glass Box.
- ADR-0009 policy CRUD + YAML portability.
