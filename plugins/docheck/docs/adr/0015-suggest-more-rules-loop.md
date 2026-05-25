# ADR-0015: Suggest-more rules loop

**Status:** Accepted
**Date:** 2026-05-14
**Authors:** giovanni ippolito <g.ippolito@gdservices.tech>

## Context

ADR-0014 espone all'utente la coverage stimata di una policy ingerita
(es. 7 regole estratte su 40 obblighi rilevati). L'utente non-esperto,
visto il gap, ha bisogno di un'azione semplice per **completare** la
policy senza dover scrivere regole a mano una per una.

Vincoli:

- Glass Box (CLAUDE.md §5): ogni regola suggerita deve avere un excerpt
  verbatim grounded sul sorgente originale.
- Sicurezza: il sorgente NON è persistito sul DB oltre l'URI. La rete
  egress durante analisi è bloccata (CLAUDE.md §4) ma le operazioni di
  ingest/suggest sono operate da utenti autorizzati e accedono a fonti
  esterne via HTTP outbound durante l'azione esplicita di import — già
  permessa per `POST /policies/ingest/url`.
- Determinismo: temperature=0, riproducibile su stessa sorgente +
  excerpt esistenti.

## Decision

Aggiungere un endpoint dedicato per chiedere all'LLM di **proporre
nuove regole** complementari, escludendo quelle già presenti, senza
persistere automaticamente nulla. L'utente sceglie quali accettare in UI.

1. Nuovo endpoint:

   ```
   POST /api/v1/policies/{policy_id}/{version}/suggest-rules
   body: {"source_url"?: string, "source_text"?: string}
   auth: principal con permesso `policy:write`
   response: {"suggestions": [{rule_type, severity, excerpt, matcher?, rationale?}]}
   ```

   `source_url` e `source_text` sono mutuamente esclusivi (validazione
   Pydantic). Almeno uno richiesto. `source_url` riusa lo stesso fetcher
   sandboxato di `services.policy_ingest._fetch_url` (size cap, schema
   allowlist, no redirect cross-host illeciti).

2. Nuovo modulo `services/policy_suggest.py`:
   - `suggest_more(db, pid, version, source_text) -> list[dict]`
   - Carica gli excerpt esistenti della policy dal DB.
   - Riusa `policy_ingest._llm_extract` (single-shot) o
     `policy_ingest._chunked_extract` (chunked) a seconda della lunghezza
     del sorgente.
   - Applica `_enforce_excerpts` (grounding verbatim).
   - Filtra candidati i cui excerpt sono loose-match con un excerpt
     esistente (riusa logica `policy_coverage._detected_matches_extracted`
     riesportata).
   - Cap di `MAX_SUGGESTIONS = 30` per response.
   - **Non** chiama `policy_svc.add_rule`: ritorna solo proposte.

3. L'utente accetta/rifiuta in UI. L'accept invia `POST /policies/{pid}/
   {version}/rules` (endpoint esistente) una volta per regola scelta.

4. Audit: ogni call a suggest-rules emette
   `audit.append_audit(action="policy.suggest.requested", payload={
   source: url|text, candidates: N})`. Le successive creazioni di regole
   sono già auditate dall'endpoint `add_rule` esistente.

5. UI: pulsante "Suggerisci altre regole" sul `PolicyDetailPane`. Apre
   dialog che accetta URL **oppure** upload documento, riusa lo stesso
   componente `PolicySourcePicker` o estende `UrlIngestDialog`. Al
   completamento, mostra lista checkbox dei candidati con excerpt
   anteprima + severità. Bottone "Aggiungi selezionate" itera POST
   rules.

## Consequences

### Positive

- Loop incrementale: utente parte da policy povera, raffina senza
  expertise.
- Glass Box invariato: ogni suggerimento è grounded verbatim sul
  sorgente fornito al momento.
- Zero side-effect: nessuna persistenza implicita — solo proposte.
- Riuso ampio del codice esistente (extraction, chunking, grounding,
  fetch URL).

### Negative / Trade-off

- L'utente deve ri-fornire il sorgente (URL o file) ad ogni round. Non
  persistiamo il body originale per privacy/footprint; ADR futura potrà
  decidere policy retention testo sorgente.
- Costo token: 1 LLM call per ronda (più chunked se lungo). Accettabile.
- Possibile drift: sessioni successive su sorgenti leggermente diversi
  producono duplicati gestiti dal filtro existing-loose-match ma non
  garantiti al 100%.

### Neutral

- Endpoint additivo; nessuna migration DB.
- Endpoint esistenti invariati.

## Alternatives considered

### Opzione A — Persistere il source_text sul Policy

Posticipata: aumenta footprint DB e impatti privacy. Da valutare a
seguito di feedback reale d'uso.

### Opzione B — Auto-apply delle suggestion sopra soglia confidence

Scartata: viola il principio di operator-in-the-loop e Glass Box
("operator può sempre rifiutare").

### Opzione C — Estendere `POST /policies/ingest/*` con flag

`merge_into=policy_id`

Scartata: ambigua semantica (versioning, conflitti id), preferibile un
endpoint dedicato con response esplicita di proposte.

## Implementation notes

- Codice: `docheck-engine/src/docheck/services/policy_suggest.py` (nuovo),
  endpoint in `docheck-engine/src/docheck/api/policies.py`.
- Test: `docheck-engine/tests/test_policy_suggest.py`.
- UI: nuovo componente in
  `docheck-ui/components/policy/SuggestRulesDialog.tsx`,
  trigger nel `PolicyDetailPane`. i18n keys
  `policies.suggest.*`.
- Telemetria: `policy_suggest.requested`,
  `policy_suggest.dedup_drop`, `policy_suggest.grounding_drop`.

## References

- ADR-0013 chunked extraction.
- ADR-0014 coverage report.
- CLAUDE.md §5 Glass Box.
