"""Metric calculation for the evaluation harness (ADR-0016).

Match logic between predicted Finding and ExpectedFinding:
  rule_id matches AND severity matches AND
  evidence_contains is a case-insensitive substring of evidence.text
  (whitespace-collapsed).

Each expected finding can be matched at most once. Greedy on first match.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .models import (
    AgentMetric,
    CaseScore,
    ConfusionMatrix,
    EvalCase,
    EvalResult,
    ExpectedFinding,
    FindingMatch,
    RuleMetric,
    Severity,
)

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", (text or "").strip().lower())


def _evidence_text(predicted: Any) -> str:
    ev = getattr(predicted, "evidence", None) or (predicted.get("evidence") if isinstance(predicted, dict) else None)
    if ev is None:
        return ""
    text = getattr(ev, "text", None)
    if text is None and isinstance(ev, dict):
        text = ev.get("text")
    return text or ""


def _attr(predicted: Any, name: str) -> Any:
    if isinstance(predicted, dict):
        return predicted.get(name)
    return getattr(predicted, name, None)


def _matches(predicted: Any, expected: ExpectedFinding) -> bool:
    if _attr(predicted, "rule_id") != expected.rule_id:
        return False
    if str(_attr(predicted, "severity")) != expected.severity:
        return False
    needle = _norm(expected.evidence_contains)
    hay = _norm(_evidence_text(predicted))
    return bool(needle) and needle in hay


def _agent_of(predicted: Any) -> str | None:
    reasoning = _attr(predicted, "reasoning") or []
    for step in reasoning:
        agent = step.get("agent") if isinstance(step, dict) else getattr(step, "agent", None)
        if agent:
            return str(agent)
    return None


def score_case(
    case: EvalCase,
    predicted: Iterable[Any],
    latency_ms: float = 0.0,
    error: str | None = None,
) -> CaseScore:
    predicted_list = list(predicted)
    expected = list(case.expected_findings)
    used_expected: set[int] = set()
    matched: list[FindingMatch] = []
    spurious: list[FindingMatch] = []

    for pred in predicted_list:
        match_idx: int | None = None
        for i, exp in enumerate(expected):
            if i in used_expected:
                continue
            if _matches(pred, exp):
                match_idx = i
                break
        sev = str(_attr(pred, "severity") or "INFO")
        rid = str(_attr(pred, "rule_id") or "")
        ev_text = _evidence_text(pred)[:200]
        agent = _agent_of(pred)
        if match_idx is not None:
            used_expected.add(match_idx)
            matched.append(
                FindingMatch(
                    rule_id=rid,
                    severity=sev,  # type: ignore[arg-type]
                    matched_evidence=ev_text,
                    agent=agent,
                )
            )
        else:
            spurious.append(
                FindingMatch(
                    rule_id=rid,
                    severity=sev,  # type: ignore[arg-type]
                    matched_evidence=ev_text,
                    agent=agent,
                )
            )

    missed = [exp for i, exp in enumerate(expected) if i not in used_expected]

    return CaseScore(
        case_id=case.id,
        tp=len(matched),
        fp=len(spurious),
        fn=len(missed),
        matched=matched,
        missed=missed,
        spurious=spurious,
        latency_ms=latency_ms,
        error=error,
    )


def aggregate(case_scores: list[CaseScore], cases: list[EvalCase]) -> EvalResult:
    confusion = ConfusionMatrix()
    per_rule: dict[str, RuleMetric] = {}
    per_agent: dict[str, AgentMetric] = {}

    case_by_id = {c.id: c for c in cases}

    for cs in case_scores:
        case = case_by_id.get(cs.case_id)
        if case is None:
            continue

        for m in cs.matched:
            confusion.add(_severity(m.severity), _severity(m.severity))
            r = per_rule.setdefault(m.rule_id, RuleMetric(rule_id=m.rule_id))
            r.tp += 1
            if m.agent:
                a = per_agent.setdefault(m.agent, AgentMetric(agent=m.agent))
                a.findings_emitted += 1
                a.findings_matched += 1

        for sp in cs.spurious:
            r = per_rule.setdefault(sp.rule_id, RuleMetric(rule_id=sp.rule_id))
            r.fp += 1
            if sp.agent:
                a = per_agent.setdefault(sp.agent, AgentMetric(agent=sp.agent))
                a.findings_emitted += 1

        for ms in cs.missed:
            r = per_rule.setdefault(ms.rule_id, RuleMetric(rule_id=ms.rule_id))
            r.fn += 1

    return EvalResult(
        cases=case_scores,
        confusion=confusion,
        per_rule=sorted(per_rule.values(), key=lambda r: r.rule_id),
        per_agent=sorted(per_agent.values(), key=lambda a: a.agent),
    )


def _severity(value: str) -> Severity:
    v = (value or "").upper()
    if v in {"FAIL", "WARN", "PASS", "INFO"}:
        return v  # type: ignore[return-value]
    return "INFO"
