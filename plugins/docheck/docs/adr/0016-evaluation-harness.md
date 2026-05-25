# ADR-0016: Evaluation harness with regression gate

**Status:** Accepted
**Date:** 2026-05-14
**Authors:** giovanni ippolito <g.ippolito@gdservices.tech>

## Context

CLAUDE.md §7 prescrive un test-set annotato di ~50 contratti IT per
regression precision/recall, ma manca un harness automatico che:

- carichi un test-set ground-truth strutturato,
- esegua la pipeline agentica end-to-end su ciascun documento,
- calcoli metriche per `rule_id`, `severity`, agente,
- confronti con baseline persistita,
- fallisca CI in caso di regressione > soglia configurabile,
- produca report HTML leggibile per audit/stakeholder.

Senza questo gate ogni modifica a prompt, chunking, retrieval o pipeline
agentica può degradare silenziosamente la qualità delle finding,
violando il pillar Glass Box (decisioni LLM verificabili) e il KPI
prodotto (precision target ≥85%).

Vincoli:

- Determinismo: temperature=0 già enforced. Eval deve essere
  riproducibile bit-per-bit con LLM mockato; modalità "live" opzionale
  contro vLLM reale per benchmark periodici.
- Zero egress (CLAUDE.md §4): default mock-mode, live-mode dietro flag
  esplicito non eseguito in CI.
- Modularità: file ≤ 500 LOC (CLAUDE.md §1.1).
- Riusare il grafo esistente (`agents.graph.get_graph`) — niente
  duplicazione pipeline.

## Decision

Aggiungere un harness di valutazione modulare composto da:

1. **Test-set format** — JSONL versionato in
   `docheck-engine/tests/eval/testset.jsonl`. Schema Pydantic
   `EvalCase`:

   ```json
   {
     "id": "case-001",
     "doc_path": "tests/fixtures/contract_01.md",
     "lang": "it",
     "policies": ["IT_GDPR_2026"],
     "doc_type": "contract",
     "expected_findings": [
       {
         "rule_id": "GDPR-Art-13",
         "severity": "FAIL",
         "evidence_contains": "trattamento",
         "policy_id": "IT_GDPR_2026"
       }
     ],
     "tags": ["gdpr", "trattamento-dati"]
   }
   ```

   Match logic: una finding predicted matcha una expected sse
   `rule_id` ∈ ground truth E `severity` coincide E
   `evidence.text` contiene `evidence_contains` (case-insensitive).

2. **Runner** — `services/eval/runner.py`:
   - `async run_cases(cases, llm_fixture=None) -> EvalResult`
   - `llm_fixture` (default mockato): mappa `doc_id → canned LLM
     responses` per riproducibilità. Se `None` → fail fast (live mode
     richiesto esplicitamente via CLI flag).
   - Esegue il grafo via `get_graph().ainvoke(state)` per ogni case.
   - Cattura `findings`, `trace`, latency wall-clock per case.

3. **Scorer** — `services/eval/scorer.py`:
   - `score_case(predicted, expected) -> CaseScore` con TP/FP/FN per
     `rule_id` e per `severity`.
   - Aggrega in `EvalResult` con:
     - `precision`, `recall`, `f1` globale,
     - per-severity confusion matrix 4x4 (FAIL/WARN/PASS/INFO),
     - per-rule precision/recall,
     - per-agent attribution via `trace[].agent`.

4. **Baseline + gate** — `tests/eval/baseline.json` (committato):

   ```json
   {
     "version": "2026-05-14",
     "metrics": {"precision": 0.87, "recall": 0.82, "f1": 0.844},
     "tolerance": 0.02
   }
   ```

   Test pytest `test_eval_regression.py` carica baseline, esegue
   harness, fallisce se `metric_current < metric_baseline - tolerance`.

5. **CLI** — `python -m docheck.services.eval [--testset PATH]
   [--baseline PATH] [--update-baseline] [--html OUT.html]
   [--live]`:
   - default: usa testset committato, mock LLM, stampa report tabellare,
     exit 0 se gate verde.
   - `--update-baseline`: ricomputa baseline (commit manuale dopo
     review).
   - `--html`: genera report HTML standalone (template inline, no
     dipendenze nuove).
   - `--live`: esegue contro vLLM reale (no-CI, opt-in).

6. **HTML report** — `services/eval/report_html.py` (≤ 200 LOC):
   tabella metriche globali, confusion matrix render via tabella HTML,
   per-case detail con expand (`<details>` HTML nativo). Inline CSS,
   nessuna dipendenza JS.

7. **CI integration**:
   - Test `tests/test_eval_regression.py` parte di `pytest -q` standard.
   - Workflow GitHub Actions (futuro) può artefattare `eval-report.html`
     dal job test.

## Consequences

### Positive

- Regressioni di qualità intercettate al PR, non in produzione.
- Baseline tracciato in git → audit visibile dell'evoluzione qualità.
- Riuso del grafo agentico esistente: nessuna duplicazione di logica.
- Determinismo garantito via mock LLM (cache fixture).
- Report HTML self-contained → distribuzione facile a stakeholder
  non-tecnici.

### Negative / Trade-off

- Mantenere il test-set è effort umano: ogni nuova policy/agent
  richiede update fixture e re-baseline.
- Mock LLM responses devono essere aggiornate quando cambia il
  prompt/output schema. Mitigato da un fixture builder che usa lo
  schema Pydantic per generare scaffold.
- Live-mode benchmark non automatizzato: richiede DGX Spark online,
  fuori scope CI.

### Neutral

- Nessuna nuova dipendenza Python (sklearn-style metric calcolate
  manualmente — pochi numeri).
- Schema testset versionato → migrare richiederà script `jq` o
  Python una-tantum.

## Alternatives considered

### Opzione A — `pytest --benchmark` o `pytest-regressions`

Scartata: orientata a perf/snapshot, non a metriche di qualità
finding. Richiederebbe wrappers comunque; meglio pochi LOC dedicati.

### Opzione B — LangSmith / Helicone hosted eval

Scartata: richiede egress + SaaS esterno → viola CLAUDE.md §4
zero-egress e on-prem-only. Da rivalutare quando arriverà la stesura
on-prem di tool open source equivalenti.

### Opzione C — DeepEval / RAGAS

Scartata: pesanti, dipendenze LLM (giudice esterno) che violano
zero-egress. Buoni per RAG quality ma orthogonali al gate
deterministico richiesto qui. Possibile integrazione future come
metric secondaria opt-in.

## Implementation notes

- Modulo: `docheck-engine/src/docheck/services/eval/` (package).
    - `__init__.py` (re-export API)
    - `models.py` — Pydantic `EvalCase`, `CaseScore`, `EvalResult`
    - `runner.py` — orchestrazione case → graph
    - `scorer.py` — TP/FP/FN, confusion matrix, F1
    - `baseline.py` — load/save/compare baseline
    - `report_html.py` — HTML render
    - `__main__.py` — CLI entry
- Test: `tests/test_eval_harness.py` (unit + integration con fixtures
  esistenti `contract_01.md`, `contract_02.md`).
- Test gate: `tests/test_eval_regression.py` (load baseline, fail su
  drop > tolerance).
- Testset seed: `tests/eval/testset.jsonl` (~5 case iniziali, espandere
  a 50 nelle PR successive).
- Baseline seed: `tests/eval/baseline.json`.
- Runbook: `docs/runbooks/eval-harness.md` (come aggiornare baseline,
  come aggiungere case, come interpretare report).
- Telemetria: log strutturato `eval.run.completed`,
  `eval.gate.failed`.

## References

- CLAUDE.md §5 Glass Box, §7 Test, §9 Performance Budget.
- ADR-0011 doc type taxonomy (policy applicability).
- ADR-0013 chunked extraction.
- Blueprint `05_implementation_plan.md` KPI section (precision ≥85%).
