"""
Italian 4-color triage scale and deterministic classifier.

The triage engine is intentionally rule-based (non-LLM) so that the colour
assignment remains auditable. The probabilistic ``DifferentialDiagnosis``
informs but does not override the deterministic safety rules: any red flag
unconditionally promotes the code to ``RED``.
"""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from .clinical import DifferentialDiagnosis, SymptomMatrix


class TriageCode(StrEnum):
    """Italian 4-colour triage code."""

    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"
    WHITE = "WHITE"


TRIAGE_TARGET_LATENCY: Final[dict[TriageCode, timedelta]] = {
    TriageCode.RED: timedelta(0),
    TriageCode.YELLOW: timedelta(minutes=15),
    TriageCode.GREEN: timedelta(minutes=120),
    TriageCode.WHITE: timedelta(hours=24),
}


class TriageDecision(BaseModel):
    """The output of the deterministic classifier."""

    model_config = ConfigDict(extra="forbid")

    code: TriageCode
    target_latency_minutes: int
    rationale: str
    red_flag_overrides: list[str] = Field(default_factory=list)


class TriageEngine:
    """Deterministic classifier mapping evidence to a ``TriageCode``.

    Decision order:
        1. Any ``SymptomMatrix.red_flags`` → ``RED``.
        2. Max severity NRS ≥ 8 → at least ``YELLOW``.
        3. Top hypothesis confidence ≥ 0.8 with non-trivial workup → ``YELLOW``.
        4. Otherwise → ``GREEN``, demoted to ``WHITE`` if no acute symptom.
    """

    HIGH_SEVERITY_NRS: Final[int] = 8
    HIGH_CONFIDENCE: Final[float] = 0.8

    def classify(
        self,
        matrix: SymptomMatrix,
        ddx: DifferentialDiagnosis,
    ) -> TriageDecision:
        if matrix.red_flags:
            return TriageDecision(
                code=TriageCode.RED,
                target_latency_minutes=0,
                rationale="Red-flag clinico rilevato. Escalation immediata.",
                red_flag_overrides=list(matrix.red_flags),
            )

        max_nrs = max(
            (s.severity_nrs for s in matrix.symptoms if s.severity_nrs is not None),
            default=0,
        )
        top_conf = ddx.hypotheses[0].confidence if ddx.hypotheses else 0.0

        if max_nrs >= self.HIGH_SEVERITY_NRS:
            return TriageDecision(
                code=TriageCode.YELLOW,
                target_latency_minutes=int(
                    TRIAGE_TARGET_LATENCY[TriageCode.YELLOW].total_seconds() // 60
                ),
                rationale=f"Severità NRS {max_nrs} ≥ {self.HIGH_SEVERITY_NRS}.",
            )

        if top_conf >= self.HIGH_CONFIDENCE and ddx.hypotheses[0].recommended_workup:
            return TriageDecision(
                code=TriageCode.YELLOW,
                target_latency_minutes=int(
                    TRIAGE_TARGET_LATENCY[TriageCode.YELLOW].total_seconds() // 60
                ),
                rationale=(
                    f"Ipotesi prevalente '{ddx.hypotheses[0].condition}' con "
                    f"confidence {top_conf:.2f} e workup richiesto."
                ),
            )

        if not matrix.symptoms:
            return TriageDecision(
                code=TriageCode.WHITE,
                target_latency_minutes=int(
                    TRIAGE_TARGET_LATENCY[TriageCode.WHITE].total_seconds() // 60
                ),
                rationale="Nessun sintomo riferito.",
            )

        # Symptoms present but no NRS measured: default to GREEN, not WHITE.
        # WHITE is reserved for truly non-acute cases; here we have evidence
        # of multiple symptoms that simply lack a quantified severity yet.
        symptom_count = len(matrix.symptoms)
        if max_nrs == 0:
            rationale = (
                f"{symptom_count} sintomi riferiti senza NRS misurato; "
                "valutazione differibile ma raccomandata."
            )
            return TriageDecision(
                code=TriageCode.GREEN,
                target_latency_minutes=int(
                    TRIAGE_TARGET_LATENCY[TriageCode.GREEN].total_seconds() // 60
                ),
                rationale=rationale,
            )

        return TriageDecision(
            code=TriageCode.GREEN,
            target_latency_minutes=int(
                TRIAGE_TARGET_LATENCY[TriageCode.GREEN].total_seconds() // 60
            ),
            rationale=(
                f"Quadro non urgente ({symptom_count} sintomi, max NRS {max_nrs})."
            ),
        )
