"""Deterministic Generator-vs-Challenger DDx review.

The differential ranker (Generator) emits a ranked list of hypotheses
ordered by confidence. This module's :class:`DDxChallenger` re-examines
that list and produces a structured critique with three signals:

    * **missing_pertinent_positives** — typical findings the top
      hypothesis would normally produce but that are absent from the
      symptom matrix (neither affirmed nor denied). Each entry is a soft
      "ask about X next" probe.
    * **contradicting_evidence** — typical findings the patient explicitly
      *denied* that nonetheless support the top hypothesis. These are
      strong "consider an alternative" signals because the model is
      defending a condition the patient is actively ruling out.
    * **competing_alternatives** — runners-up whose confidence sits inside
      a narrow margin of the top hypothesis (``_COMPETITIVE_DELTA``).
      Forces the UI to flag near-ties instead of hiding them.

The review is **deterministic** — no LLM call. It runs in microseconds and
never blocks the interview loop. The structured output is consumed by the
UI ("Challenger says: consider X because Y") and by the clinician audit
trail (rationale for accept/reject decisions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from .agents.differential_dx_agent import _HYPOTHESIS_TYPICAL_FINDINGS
from .models.clinical import DifferentialDiagnosis, SymptomMatrix

# How close the runner-up confidence must be to the top hypothesis to be
# surfaced as a competing alternative. Tighter than the discriminator
# threshold so the Challenger only flags genuine near-ties.
_COMPETITIVE_DELTA: Final[float] = 0.10
# Verdicts mirror the core.meta.generator_challenger.Verdict enum but stay
# string-typed here so the plugin is self-contained.
VERDICT_APPROVED: Final[str] = "APPROVED"
VERDICT_REVISE: Final[str] = "REVISE"
VERDICT_REJECT: Final[str] = "REJECT"


@dataclass
class CompetingAlternative:
    """A runner-up hypothesis within ``_COMPETITIVE_DELTA`` of the top."""

    condition: str
    confidence: float
    confidence_gap: float

    def to_dict(self) -> dict[str, object]:
        return {
            "condition": self.condition,
            "confidence": self.confidence,
            "confidence_gap": self.confidence_gap,
        }


@dataclass
class ChallengerReview:
    """Structured second opinion on a differential."""

    top_hypothesis: str | None
    top_confidence: float | None
    verdict: str
    rationale: str
    missing_pertinent_positives: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    competing_alternatives: list[CompetingAlternative] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "top_hypothesis": self.top_hypothesis,
            "top_confidence": self.top_confidence,
            "verdict": self.verdict,
            "rationale": self.rationale,
            "missing_pertinent_positives": list(self.missing_pertinent_positives),
            "contradicting_evidence": list(self.contradicting_evidence),
            "competing_alternatives": [
                a.to_dict() for a in self.competing_alternatives
            ],
        }


class DDxChallenger:
    """Deterministic Challenger that reviews a :class:`DifferentialDiagnosis`."""

    def __init__(
        self,
        *,
        competitive_delta: float = _COMPETITIVE_DELTA,
        typical_findings: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._delta = competitive_delta
        self._typical = typical_findings or _HYPOTHESIS_TYPICAL_FINDINGS

    def review(
        self, ddx: DifferentialDiagnosis, matrix: SymptomMatrix
    ) -> ChallengerReview:
        """Return a structured critique of ``ddx`` against ``matrix``."""
        if not ddx.hypotheses:
            return ChallengerReview(
                top_hypothesis=None,
                top_confidence=None,
                verdict=VERDICT_REVISE,
                rationale=(
                    "No hypothesis produced by the ranker — request more "
                    "anamnesis turns before validation."
                ),
            )

        top = ddx.hypotheses[0]
        affirmed = {s.canonical_name for s in matrix.symptoms}
        denied = set(matrix.denied_symptoms)
        typical = set(self._typical.get(top.condition, ()))

        # Findings the top hypothesis expects but the patient hasn't been
        # asked / hasn't reported. "Unknown" rather than "false".
        missing = sorted(typical - affirmed - denied)
        # Findings the patient explicitly denied that nonetheless appear in
        # the typical-findings set for the top hypothesis.
        contradicting = sorted(typical & denied)

        # Competing alternatives — within delta of the top confidence.
        competing: list[CompetingAlternative] = []
        for h in ddx.hypotheses[1:]:
            gap = top.confidence - h.confidence
            if gap <= self._delta:
                competing.append(
                    CompetingAlternative(
                        condition=h.condition,
                        confidence=h.confidence,
                        confidence_gap=round(gap, 4),
                    )
                )

        verdict, rationale = self._adjudicate(
            top_confidence=top.confidence,
            missing=missing,
            contradicting=contradicting,
            competing=competing,
        )

        return ChallengerReview(
            top_hypothesis=top.condition,
            top_confidence=top.confidence,
            verdict=verdict,
            rationale=rationale,
            missing_pertinent_positives=missing,
            contradicting_evidence=contradicting,
            competing_alternatives=competing,
        )

    @staticmethod
    def _adjudicate(
        *,
        top_confidence: float,
        missing: list[str],
        contradicting: list[str],
        competing: list[CompetingAlternative],
    ) -> tuple[str, str]:
        if contradicting:
            return (
                VERDICT_REJECT,
                (
                    f"Top hypothesis is contradicted by patient-denied findings: "
                    f"{', '.join(contradicting)}. Re-rank or escalate to "
                    f"clinician before validation."
                ),
            )
        if competing:
            top_competitor = competing[0]
            return (
                VERDICT_REVISE,
                (
                    f"Top hypothesis only leads runner-up "
                    f"'{top_competitor.condition}' by "
                    f"{top_competitor.confidence_gap:.2f} confidence — "
                    f"ask a discriminator before validation."
                ),
            )
        if missing and top_confidence < 0.7:
            return (
                VERDICT_REVISE,
                (
                    f"Top hypothesis is weakly supported (confidence "
                    f"{top_confidence:.2f}); pertinent positives not yet "
                    f"explored: {', '.join(missing)}."
                ),
            )
        return (
            VERDICT_APPROVED,
            (
                "No contradicting evidence and no competing alternatives "
                "within margin. Differential is internally consistent."
            ),
        )
