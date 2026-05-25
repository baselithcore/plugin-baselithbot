# Tutorial 2 — Scrivi la tua prima policy

Obiettivo: creare, attivare e testare una policy custom in 20 minuti.

Prerequisiti: [Tutorial 1](01-first-analysis.md) completato.

## Concetti

| Termine | Definizione |
|---------|-------------|
| **Policy** | Set di regole versionate, scoped (IT/EU/world/custom), attivabile/disattivabile. |
| **Rule** | Singola regola: tipo (`semantic` o `deterministic`), severity (`FAIL`/`WARN`/`PASS`/`INFO`), excerpt verbatim citato, matcher opzionale (regex/lemma). |
| **Excerpt** | Testo verbatim della clausola/normativa. **Citato letteralmente** in `Finding.policy_ref.excerpt`. Substring-match enforced contro retrieval result. |
| **Built-in policy** | `DocCheck_Builtin` — sempre applicata, read-only, regole deterministiche baseline. |

Backing schema: [docheck-engine/src/docheck/db/models.py](../../docheck-engine/src/docheck/db/models.py) (`Policy`, `Rule`).

## Opzione A — UI (consigliata)

1. Sidebar → **Policies** → **+ New policy**.
2. Compila:
   - **id**: `MY_NDA_2026` (lowercase + underscore preferito).
   - **version**: `1.0.0` (SemVer).
   - **title**: `NDA Aziendale Standard 2026`.
   - **scope**: `custom`.
   - **lang**: `it`.
3. Aggiungi rule:
   - **rule_type**: `semantic` (default) o `deterministic`.
   - **severity**: `FAIL` per violazione bloccante, `WARN` per attenzione, `INFO` per nota.
   - **excerpt**: testo verbatim della clausola che la rule cerca/verifica. Es: `"Le parti si impegnano a non divulgare informazioni riservate per un periodo non inferiore a 5 anni."`
   - **matcher** (opzionale): pattern lemma o regex. Es: `"durata.*?(\\d+)\\s+ann[io]"`.
4. Salva → policy creata in stato `active=false`.
5. **Attiva**: toggle → `POST /api/v1/policies/{id}/{version}/active`.

## Opzione B — YAML import

Crea `my-nda-policy.yaml`:

```yaml
id: MY_NDA_2026
version: 1.0.0
title: NDA Aziendale Standard 2026
scope: custom
lang: it
active: true
rules:
  - id: NDA-DURATION-MIN
    rule_type: semantic
    severity: WARN
    excerpt: |
      Le parti si impegnano a mantenere la riservatezza delle informazioni
      confidenziali per un periodo non inferiore a 5 (cinque) anni
      dalla data di sottoscrizione del presente accordo.
    matcher: 'durat[ae].*?(\d+)\s+ann[io]'

  - id: NDA-GOVERNING-LAW-IT
    rule_type: deterministic
    severity: FAIL
    excerpt: |
      Il presente accordo è regolato dalla legge italiana. Foro competente: Milano.
    matcher: 'legge\s+itali[ao]n[ae]|foro\s+(competente|esclusivo)'

  - id: NDA-PII-PROCESSING
    rule_type: semantic
    severity: FAIL
    excerpt: |
      Il trattamento di dati personali avviene nel rispetto del
      Regolamento UE 2016/679 (GDPR) e del D.lgs. 196/2003 e s.m.i.
```

Import via API:

```bash
curl -X POST http://localhost:8765/api/v1/policies/import \
  -H "Authorization: Bearer <jwt>" \
  -F "file=@my-nda-policy.yaml"
```

Import via UI: **Policies** → **Import YAML**.

## Opzione C — Ingest da URL o documento

Per partire da una normativa esistente (es. testo legge):

```bash
# Da URL
curl -X POST http://localhost:8765/api/v1/policies/ingest/url \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"url": "file:///path/to/normative.pdf", "title": "GDPR EU"}'

# Da documento già caricato
curl -X POST http://localhost:8765/api/v1/policies/ingest/document \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "doc-abc123", "title": "Codice Privacy IT"}'
```

L'ingest agent estrae structure → propone rule candidate → user review prima di attivazione.

## Test della policy

1. Carica un documento target via [Tutorial 1 step 6](01-first-analysis.md#step-6--carica-un-documento).
2. Lancia analisi: la nuova policy attiva è inclusa automaticamente in `policies_applied`.
3. Findings UI: filtra per `policy_id == MY_NDA_2026`.
4. Verifica: ogni finding cita verbatim un `excerpt` di una tua rule (substring).

Per analisi mirata:

```bash
curl -X POST http://localhost:8765/api/v1/documents/<doc_id>/analyze \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"policies": ["MY_NDA_2026"], "lang": "it"}'
```

`DocCheck_Builtin` viene comunque applicata (glass-box: trasparente in `policies_applied`).

## Versioning

- Policy è `(id, version)` chiave composita.
- Modifica = clone in nuova versione: `POST /api/v1/policies/{id}/{version}/clone`.
- Versione vecchia rimane disponibile (audit trail riproducibile).
- `active=true` solo su una versione alla volta per `id`.

## Glass-box guarantee

Il sistema **rifiuta** finding la cui `policy_ref.excerpt` non è substring di un retrieval result effettivo. Per questo:

- Scrivi excerpt **fedeli al documento policy reale**.
- Non parafrasare; copia-incolla letterale.
- Manteni interpunzione e maiuscole.

Se l'agente non riesce a citare un excerpt esistente → finding scartato → severity downgrade o skip + log warning.

## Test set di regression

Best practice: per ogni policy, mantenere un set di documenti annotati (positivi + negativi) e validare precision/recall via [scripts/kpi.py](../../scripts/kpi.py).

Procedura: [docs/runbooks/kpi-evaluation.md](../runbooks/kpi-evaluation.md).

## Prossimi passi

- [Spiegazione — Glass Box](../explanation/glass-box.md): perché excerpt verbatim non è negoziabile.
- [Reference — Schema policy](../reference/schemas.md#policy): JSON contract completo.
- [API — Policies endpoints](../api/endpoints.md#policies): CRUD, import, activate.
