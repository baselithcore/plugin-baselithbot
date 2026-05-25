"""Evaluation harness package (ADR-0016).

Public API:
    EvalCase, ExpectedFinding, EvalResult, CaseScore, Baseline, GateOutcome
    execute, load_cases, CannedProvider, LivePipelineProvider
    score_case, aggregate
    load_baseline, save_baseline, baseline_from_result, check_gate
    render_html
"""

from .baseline import (
    baseline_from_result,
    check_gate,
    load_baseline,
    save_baseline,
)
from .models import (
    Baseline,
    CaseScore,
    ConfusionMatrix,
    EvalCase,
    EvalResult,
    ExpectedFinding,
    GateOutcome,
)
from .report_html import render_html
from .runner import (
    CannedProvider,
    LivePipelineProvider,
    execute,
    load_cases,
)
from .scorer import aggregate, score_case

__all__ = [
    "Baseline",
    "CannedProvider",
    "CaseScore",
    "ConfusionMatrix",
    "EvalCase",
    "EvalResult",
    "ExpectedFinding",
    "GateOutcome",
    "LivePipelineProvider",
    "aggregate",
    "baseline_from_result",
    "check_gate",
    "execute",
    "load_baseline",
    "load_cases",
    "render_html",
    "save_baseline",
    "score_case",
]
