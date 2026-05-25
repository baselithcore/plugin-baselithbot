"""Pydantic models for the evaluation harness (ADR-0016).

EvalCase: ground-truth annotation for a single document.
CaseScore: per-case TP/FP/FN with attribution.
EvalResult: aggregate metrics across all cases.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["FAIL", "WARN", "PASS", "INFO"]


class ExpectedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    severity: Severity
    evidence_contains: str = Field(..., min_length=1)
    policy_id: str | None = None


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    doc_path: str
    lang: str = "it"
    policies: list[str] = Field(default_factory=list)
    doc_type: str = "contract"
    expected_findings: list[ExpectedFinding] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class FindingMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    severity: Severity
    matched_evidence: str
    agent: str | None = None


class CaseScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    matched: list[FindingMatch] = Field(default_factory=list)
    missed: list[ExpectedFinding] = Field(default_factory=list)
    spurious: list[FindingMatch] = Field(default_factory=list)
    latency_ms: float = 0.0
    error: str | None = None

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0


class ConfusionMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    labels: list[Severity] = Field(
        default_factory=lambda: ["FAIL", "WARN", "PASS", "INFO"]  # type: ignore[arg-type]
    )
    cells: dict[str, dict[str, int]] = Field(default_factory=dict)

    def add(self, expected: Severity, predicted: Severity) -> None:
        row = self.cells.setdefault(expected, {})
        row[predicted] = row.get(predicted, 0) + 1


class RuleMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0


class AgentMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str
    findings_emitted: int = 0
    findings_matched: int = 0


class EvalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: list[CaseScore] = Field(default_factory=list)
    confusion: ConfusionMatrix = Field(default_factory=ConfusionMatrix)
    per_rule: list[RuleMetric] = Field(default_factory=list)
    per_agent: list[AgentMetric] = Field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    mode: Literal["mock", "live"] = "mock"

    @property
    def tp(self) -> int:
        return sum(c.tp for c in self.cases)

    @property
    def fp(self) -> int:
        return sum(c.fp for c in self.cases)

    @property
    def fn(self) -> int:
        return sum(c.fn for c in self.cases)

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0

    def metric_dict(self) -> dict[str, float]:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
        }


class Baseline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    metrics: dict[str, float]
    tolerance: float = 0.02


class GateOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    failures: list[str] = Field(default_factory=list)
    deltas: dict[str, float] = Field(default_factory=dict)
