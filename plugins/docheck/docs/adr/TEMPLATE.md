# ADR-NNNN: <titolo conciso della decisione>

**Status:** Proposed | Accepted | Superseded by ADR-XXXX | Deprecated
**Date:** YYYY-MM-DD
**Authors:** nome cognome <email>
**Reviewers:** nome cognome <email>, ...

## Context

Quale forza tecnica / problema / vincolo motiva questa decisione? Qual è lo stato attuale del sistema? Quali requisiti di prodotto/sicurezza/performance entrano in gioco?

Cita: blueprint rilevanti, ADR precedenti, issue/PR aperte, normative o vincoli legali.

## Decision

Cosa è stato deciso, in modo dichiarativo. Una frase principale + dettagli di implementazione minimi sufficienti a comprendere lo scope.

Esempio: "Adottiamo Postgres 15 con Row-Level Security come backend DB per il path multi-tenant. SQLite resta per single-tenant MVP."

## Consequences

### Positive

- ...
- ...

### Negative / Trade-off

- ...
- ...

### Neutral

- Cambi operativi, runbook da aggiornare, training, ecc.

## Alternatives considered

### Opzione A — <nome>

Breve descrizione. Perché scartata.

### Opzione B — <nome>

Breve descrizione. Perché scartata.

## Implementation notes

(opzionale) Pointer a:

- Codice / migration: `path/to/file`
- Test che dimostrano la decisione: `tests/...`
- Runbook operativo: `docs/runbooks/...`

## References

- Spec / RFC esterni.
- Documentazione fornitore.
- Articoli rilevanti.

---

> Convenzioni:
>
> - `NNNN` = 4 cifre con padding zero. Numerazione progressiva. Verifica `docs/adr/` per il prossimo libero.
> - Nome file: `NNNN-titolo-kebab-case.md`. Niente accenti.
> - Una decisione per ADR. Decisioni che si superano → nuovo ADR con `Superseded by` + update old ADR `Status`.
> - Tieni il documento conciso. ADR di 5 pagine è un design doc, non un ADR.
