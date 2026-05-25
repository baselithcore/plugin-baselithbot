"""Regression gate: load committed testset + baseline, fail PR on drop (ADR-0016).

This test runs in pure mock mode using the canned predictions JSON. It
validates the harness plumbing and prevents accidental baseline drift.
Real model-quality regression requires --live mode against vLLM and is
exercised on a separate cadence (see docs/runbooks/eval-harness.md).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docheck.services.eval import (
    CannedProvider,
    check_gate,
    execute,
    load_baseline,
    load_cases,
)

EVAL_DIR = Path(__file__).resolve().parent / "eval"


@pytest.mark.asyncio
async def test_eval_regression_gate() -> None:
    cases = load_cases(EVAL_DIR / "testset.jsonl")
    predictions = json.loads(
        (EVAL_DIR / "predictions.canned.json").read_text(encoding="utf-8")
    )
    provider = CannedProvider(predictions)

    result = await execute(cases, provider, mode="mock")
    baseline = load_baseline(EVAL_DIR / "baseline.json")
    gate = check_gate(result, baseline)

    assert gate.passed, (
        f"eval regression gate failed: {gate.failures}; "
        f"current={result.metric_dict()} baseline={baseline.metrics}"
    )
