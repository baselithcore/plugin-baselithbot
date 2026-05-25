# Runbook: KPI Evaluation

Misura precision/recall su test set annotato.

## Test set format

JSONL — uno per documento. Vedi [testset.example.jsonl](../../docheck-engine/tests/fixtures/testset.example.jsonl).

```json
{
  "doc_path": "path/to/doc.pdf",
  "lang": "it",
  "policies": ["IT_GDPR_2026"],
  "expected_findings": [
    {
      "rule_id": "GDPR-Art-13",
      "chunk_text_contains": "retention",
      "severity": "FAIL"
    }
  ]
}
```

## Annotazione

- 50 contratti IT (target MVP).
- Annotazione manuale da Compliance Officer.
- ≥2 reviewer per accordo Cohen κ ≥ 0.7.

## Run

```bash
uv run python scripts/kpi.py \
  --testset docheck-engine/tests/fixtures/testset.jsonl \
  --report kpi_report.json
```

## Output

```
Precision: 0.870  Recall: 0.812  F1: 0.840
Report → kpi_report.json
```

## Acceptance gate

Script esce con `FAIL` se:

- Precision < 0.85
- Recall < 0.80

KPI inclusi in CI nightly job (TODO F2 late).

## Matching

Finding match expected se:

- `rule_id` identico
- `severity` identico (se specificato in expected)
- `chunk_text_contains` substring presente in `evidence.text`

Match greedy uno-a-uno per evitare double-count.
