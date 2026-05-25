# Runbook — Evaluation Harness

ADR di riferimento: [ADR-0016](../adr/0016-evaluation-harness.md).

Lo harness valuta la qualità della pipeline agentica producendo metriche
precision/recall/F1 contro un test-set ground-truth committato. È un
**gate CI obbligatorio** in modalità mock; la modalità `--live`
contro vLLM è opt-in per benchmark periodici.

---

## 1. Layout

```
docheck-engine/
├── src/docheck/services/eval/
│   ├── __init__.py        # public API
│   ├── __main__.py        # CLI
│   ├── models.py          # EvalCase / EvalResult / Baseline
│   ├── runner.py          # orchestratore
│   ├── scorer.py          # TP/FP/FN + confusion matrix
│   ├── baseline.py        # load/save/check_gate
│   └── report_html.py     # HTML self-contained
└── tests/
    ├── eval/
    │   ├── testset.jsonl              # ground truth
    │   ├── predictions.canned.json    # mock predictions
    │   └── baseline.json              # gate threshold
    ├── test_eval_harness.py           # unit
    └── test_eval_regression.py        # CI gate
```

---

## 2. Eseguire l'harness

### Mock mode (default, riproducibile)

```bash
cd docheck-engine
python -m docheck.services.eval \
  --testset tests/eval/testset.jsonl \
  --baseline tests/eval/baseline.json \
  --predictions tests/eval/predictions.canned.json \
  --html /tmp/eval-report.html
```

Output:

```
cases=3 TP=3 FP=0 FN=0
precision=1.0000 recall=1.0000 f1=1.0000
gate=PASS precision+0.0000 recall+0.0000 f1+0.0000
html report written to /tmp/eval-report.html
```

Exit code: `0` se gate verde, `1` se regressione, `2` se errore di
configurazione.

### Live mode (opt-in, no-CI)

Richiede vLLM raggiungibile + un `doc_loader` che converte un `EvalCase`
in `state` per il grafo. Da abilitare in una PR successiva — oggi lo
script stampa "live mode requires a doc_loader implementation; not yet
wired" ed esce 2.

---

## 3. Aggiornare il test-set

1. Aggiungere il documento sotto `tests/fixtures/<doc>.md` (o sub-dir).
2. Aggiungere una riga JSONL a `tests/eval/testset.jsonl`:
   ```json
   {"id": "case-NNN", "doc_path": "tests/fixtures/<doc>.md",
    "lang": "it", "policies": ["IT_GDPR_2026"],
    "doc_type": "contract",
    "expected_findings": [
      {"rule_id": "GDPR-Art-13", "severity": "FAIL",
       "evidence_contains": "trattamento", "policy_id": "IT_GDPR_2026"}
    ],
    "tags": ["gdpr"]}
   ```
3. Aggiungere la predizione canned corrispondente in
   `tests/eval/predictions.canned.json` per il caso (mock mode).
4. Eseguire i test:
   ```bash
   pytest tests/test_eval_harness.py tests/test_eval_regression.py -q
   ```
5. Se la baseline va aggiornata, vedi §4.

---

## 4. Aggiornare la baseline

La baseline (`tests/eval/baseline.json`) si aggiorna **solo dopo
review manuale**. Il workflow:

```bash
python -m docheck.services.eval \
  --testset tests/eval/testset.jsonl \
  --predictions tests/eval/predictions.canned.json \
  --baseline tests/eval/baseline.json \
  --update-baseline \
  --tolerance 0.02
```

Committare il delta in PR separata, citando:

- ragione del bump (es. nuovo agente, prompt revision, fixture growth);
- delta numerico `precision/recall/f1`;
- ADR di riferimento se la modifica deriva da una nuova decisione.

---

## 5. Interpretare il report HTML

Il report è autoconsistente (no JS, no asset esterni). Sezioni:

- **KPI cards**: precision/recall/F1, totali TP/FP/FN, # case.
- **Regression gate**: PASS/FAIL + delta vs baseline.
- **Confusion matrix**: severità predetta vs attesa, 4×4. Diagonale =
  accordo, off-diagonal = mismatch.
- **Per-rule metrics**: F1 per `rule_id` per spottare regole deboli.
- **Per-agent attribution**: quante finding ha emesso/azzeccato ogni
  agente (Legal/Technical/PII/Synthesizer).
- **Cases**: dettaglio per case con expand `<details>`. Tre tabelle
  per case: matched, spurious (FP), missed (FN).

---

## 6. Integrazione CI

`test_eval_regression.py` parte di `pytest -q` standard:

```yaml
# .github/workflows/test.yml (estratto)
- name: Run pytest
  run: |
    cd docheck-engine
    pytest -q
- name: Upload eval report (on failure)
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: eval-report
    path: docheck-engine/eval-report.html
```

Per artefattare il report a ogni run, aggiungere uno step esplicito che
invoca `python -m docheck.services.eval ... --html eval-report.html`.

---

## 7. FAQ

**Q: la mock mode non testa la qualità reale del modello.**
A: corretto. Cattura regressioni di plumbing (schema break, scorer bug,
contract drift). La qualità modello richiede `--live` contro vLLM,
eseguito a cadenza settimanale fuori CI.

**Q: posso confrontare due baseline?**
A: `git diff tests/eval/baseline.json` mostra il delta. La storia di
git è la timeline qualità.

**Q: il `tolerance` è troppo permissivo?**
A: default 0.02 (2 punti). Diminuire se il test-set cresce e diventa
statisticamente robusto (>50 case).

---

## 8. Roadmap

- [ ] Live-mode `doc_loader` che istanzia `state` reale (parser + chunk
      + retrieval).
- [ ] Confusion matrix nello stdout summary (oltre HTML).
- [ ] Esportare risultati in formato OpenTelemetry per dashboard
      Grafana (ADR futura — observability).
- [ ] Per-tag breakdown (es. F1 per `tags=["gdpr"]`) in HTML.
