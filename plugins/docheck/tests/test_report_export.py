"""Report markdown/json export rendering."""

import json

from docheck.services.report_export import report_to_json, report_to_markdown

SAMPLE = {
    "report_id": "r-1",
    "doc": {"id": "d-1", "name": "test.pdf", "sha256": "abc", "lang": "it", "pages": 5},
    "score": 78,
    "by_severity": {"FAIL": 1, "WARN": 2, "PASS": 10},
    "summary": "Documento conforme con eccezioni minori.",
    "findings": [
        {
            "rule_id": "GDPR-Art-13",
            "severity": "FAIL",
            "evidence": {
                "chunk_id": "c-1",
                "page": 7,
                "line_start": 142,
                "line_end": 145,
                "bbox": [0, 0, 0, 0],
                "text": "...",
            },
            "policy_ref": {
                "id": "GDPR-Art-13",
                "policy_id": "IT_GDPR_2026",
                "version": "3.0.0",
                "title": "Informativa",
                "excerpt": "Il titolare informa...",
            },
            "explanation": "Manca retention.",
            "suggestion": "Aggiungere clausola.",
            "confidence": 0.92,
            "reasoning": [],
        }
    ],
    "audit": {"engine_version": "0.1.0", "model": "llama-3.3"},
    "signature": "ed25519:abc123",
}


def test_markdown_contains_score_and_findings() -> None:
    md = report_to_markdown(SAMPLE)
    assert "78/100" in md
    assert "GDPR-Art-13" in md
    assert "Il titolare informa..." in md
    assert "ed25519:abc123" in md
    assert "Manca retention." in md


def test_markdown_summary_block() -> None:
    md = report_to_markdown(SAMPLE)
    assert "Documento conforme" in md


def test_json_canonical_sorts_keys() -> None:
    out = report_to_json(SAMPLE)
    parsed = json.loads(out)
    assert parsed["report_id"] == "r-1"
    # Sorted: by_severity comes before doc
    keys = list(parsed.keys())
    assert keys == sorted(keys)
