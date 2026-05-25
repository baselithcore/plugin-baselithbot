"""Unit tests for the evaluation harness modules (ADR-0016)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docheck.services.eval import (
    Baseline,
    CannedProvider,
    EvalCase,
    ExpectedFinding,
    aggregate,
    baseline_from_result,
    check_gate,
    execute,
    load_baseline,
    load_cases,
    render_html,
    save_baseline,
    score_case,
)


def _case(case_id: str, expected: list[ExpectedFinding]) -> EvalCase:
    return EvalCase(
        id=case_id,
        doc_path="tests/fixtures/contract_01.md",
        lang="it",
        policies=["IT_GDPR_2026"],
        expected_findings=expected,
    )


def _pred(rule_id: str, severity: str, text: str, agent: str = "LegalComplianceAgent") -> dict:
    return {
        "id": f"pred-{rule_id}",
        "rule_id": rule_id,
        "severity": severity,
        "evidence": {"chunk_id": "c1", "page": 1, "line_start": 1, "line_end": 2, "bbox": [0, 0, 1, 1], "text": text},
        "reasoning": [{"step": 1, "agent": agent}],
    }


def test_score_case_perfect_match() -> None:
    case = _case(
        "c1",
        [ExpectedFinding(rule_id="R1", severity="FAIL", evidence_contains="trattamento")],
    )
    score = score_case(case, [_pred("R1", "FAIL", "I dati saranno trattamento conforme")])
    assert score.tp == 1
    assert score.fp == 0
    assert score.fn == 0
    assert score.precision == 1.0
    assert score.recall == 1.0


def test_score_case_false_positive_and_false_negative() -> None:
    case = _case(
        "c1",
        [ExpectedFinding(rule_id="R1", severity="FAIL", evidence_contains="trattamento")],
    )
    score = score_case(case, [_pred("R2", "WARN", "altro contenuto")])
    assert score.tp == 0
    assert score.fp == 1
    assert score.fn == 1
    assert score.precision == 0.0
    assert score.recall == 0.0


def test_score_case_severity_mismatch_counts_as_miss() -> None:
    case = _case(
        "c1",
        [ExpectedFinding(rule_id="R1", severity="FAIL", evidence_contains="x")],
    )
    score = score_case(case, [_pred("R1", "WARN", "text contains x here")])
    assert score.tp == 0
    assert score.fn == 1
    assert score.fp == 1


def test_score_case_each_expected_matched_once() -> None:
    case = _case(
        "c1",
        [ExpectedFinding(rule_id="R1", severity="FAIL", evidence_contains="x")],
    )
    score = score_case(case, [_pred("R1", "FAIL", "x here"), _pred("R1", "FAIL", "x here too")])
    assert score.tp == 1
    assert score.fp == 1
    assert score.fn == 0


def test_aggregate_per_rule_and_per_agent() -> None:
    case = _case(
        "c1",
        [
            ExpectedFinding(rule_id="R1", severity="FAIL", evidence_contains="alpha"),
            ExpectedFinding(rule_id="R2", severity="WARN", evidence_contains="beta"),
        ],
    )
    score = score_case(
        case,
        [
            _pred("R1", "FAIL", "alpha word", agent="LegalComplianceAgent"),
            _pred("R2", "WARN", "beta word", agent="TechnicalAgent"),
        ],
    )
    result = aggregate([score], [case])
    assert result.tp == 2
    assert result.fp == 0
    assert result.fn == 0
    assert {r.rule_id for r in result.per_rule} == {"R1", "R2"}
    assert {a.agent for a in result.per_agent} == {"LegalComplianceAgent", "TechnicalAgent"}


def test_baseline_roundtrip(tmp_path: Path) -> None:
    base = Baseline(version="2026-05-14", metrics={"precision": 0.8, "recall": 0.7, "f1": 0.747}, tolerance=0.02)
    p = tmp_path / "baseline.json"
    save_baseline(p, base)
    loaded = load_baseline(p)
    assert loaded == base


def test_check_gate_pass_within_tolerance() -> None:
    case = _case("c1", [ExpectedFinding(rule_id="R1", severity="FAIL", evidence_contains="x")])
    result = aggregate([score_case(case, [_pred("R1", "FAIL", "x here")])], [case])
    base = baseline_from_result(result, version="2026-05-14", tolerance=0.02)
    gate = check_gate(result, base)
    assert gate.passed
    assert gate.failures == []


def test_check_gate_fails_on_regression() -> None:
    case = _case("c1", [ExpectedFinding(rule_id="R1", severity="FAIL", evidence_contains="x")])
    result_now = aggregate([score_case(case, [_pred("R2", "FAIL", "y here")])], [case])
    base = Baseline(version="prev", metrics={"precision": 1.0, "recall": 1.0, "f1": 1.0}, tolerance=0.02)
    gate = check_gate(result_now, base)
    assert not gate.passed
    assert any("precision" in f for f in gate.failures)
    assert gate.deltas["precision"] < 0


@pytest.mark.asyncio
async def test_execute_with_canned_provider() -> None:
    case = _case("c1", [ExpectedFinding(rule_id="R1", severity="FAIL", evidence_contains="trattamento")])
    provider = CannedProvider({"c1": [_pred("R1", "FAIL", "I dati di trattamento")]})
    result = await execute([case], provider, mode="mock")
    assert result.tp == 1
    assert result.mode == "mock"
    assert result.cases[0].latency_ms >= 0
    assert result.started_at and result.finished_at


def test_load_cases_from_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "ts.jsonl"
    p.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "c1",
                        "doc_path": "x.md",
                        "policies": ["P1"],
                        "expected_findings": [{"rule_id": "R1", "severity": "FAIL", "evidence_contains": "y"}],
                    }
                ),
                "# comment line",
                "",
                json.dumps(
                    {
                        "id": "c2",
                        "doc_path": "y.md",
                        "policies": [],
                        "expected_findings": [],
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    cases = load_cases(p)
    assert [c.id for c in cases] == ["c1", "c2"]


def test_render_html_smoke() -> None:
    case = _case("c1", [ExpectedFinding(rule_id="R1", severity="FAIL", evidence_contains="x")])
    score = score_case(case, [_pred("R1", "FAIL", "x in body")])
    result = aggregate([score], [case])
    html = render_html(result)
    assert "<html" in html and "</html>" in html
    assert "precision" in html
    assert "R1" in html


def test_render_html_with_gate_failure_block() -> None:
    case = _case("c1", [ExpectedFinding(rule_id="R1", severity="FAIL", evidence_contains="x")])
    score = score_case(case, [_pred("R2", "FAIL", "y")])
    result = aggregate([score], [case])
    base = Baseline(version="prev", metrics={"precision": 1.0, "recall": 1.0, "f1": 1.0}, tolerance=0.01)
    gate = check_gate(result, base)
    html = render_html(result, gate=gate)
    assert "FAIL" in html
    assert "Regression gate" in html
