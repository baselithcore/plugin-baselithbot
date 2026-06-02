"""
Schemas for the hypothesis-driven clinical reasoning loop.

The :class:`ClinicianTurn` collapses one turn of a real clinician's
deliberation into a single structured object: the live differential across
all of medicine, the single highest-information-gain question to ask next,
and the stop/escalation signals. Unlike the legacy OPQRST slot machine, the
question is chosen to *discriminate the current differential*, not to fill a
fixed slot — so a sleep-apnea complaint is probed with sleep questions, a
chest-pain complaint with cardiac questions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .clinical import DifferentialHypothesis


class ProbeQuestion(BaseModel):
    """The next question the clinician chooses to ask the patient."""

    model_config = ConfigDict(extra="forbid")

    text: str
    # Why this question now — what it tests in the differential (≤ short).
    rationale: str = ""
    # The hypothesis or finding this probe is meant to confirm/exclude.
    probes_for: str = ""
    tone: str = Field(default="empathic")


class ClinicianTurn(BaseModel):
    """One turn of hypothesis-driven clinical deliberation."""

    model_config = ConfigDict(extra="forbid")

    # Live differential across all of medicine, ranked descending by
    # confidence. May be empty very early in the interview.
    differential: list[DifferentialHypothesis] = Field(default_factory=list)
    # The single best next question. ``None`` only when ``ready_to_finalize``.
    next_question: ProbeQuestion | None = None
    # The clinician judges enough data has been gathered for the pre-triage.
    ready_to_finalize: bool = False
    # A potential emergency was detected and must be verified/escalated.
    red_flag_suspected: bool = False
    # Brief internal reasoning note for clinician traceability (not shown to
    # the patient).
    reasoning_note: str = ""
