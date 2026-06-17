"""
Standalone helpers extracted from InterviewFlowHandler.

``build_interview_preview`` and ``finalize_inline`` are module-level functions
that accept the handler's stateful dependencies as explicit parameters, keeping
``interview_flow.py`` under the 500-LOC hard cap without any behavioural change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.clinical import DifferentialDiagnosis, ReportStatus, TriageReport
from .intake_report import render_intake_report

if TYPE_CHECKING:
    from ..agents.differential_dx_agent import DifferentialDxAgent
    from ..models.triage import TriageEngine


def build_interview_preview(
    snap: Any,
    red_flags: list[str],
    *,
    dx_agent: DifferentialDxAgent,
    triage_engine: TriageEngine,
    limit: int = 5,
    reasoner_ddx: DifferentialDiagnosis | None = None,
) -> dict[str, Any] | None:
    """Build a live preview of the differential the clinician is watching.

    Uses the reasoner's live differential when supplied; otherwise the
    deterministic heuristic ranking (no LLM call). The preview never
    claims to be final.
    """
    matrix = snap.to_matrix(red_flags=red_flags)
    if not matrix.symptoms and not matrix.denied_symptoms:
        return None
    ddx = (
        reasoner_ddx if reasoner_ddx is not None else dx_agent._heuristic_rank(matrix)  # noqa: SLF001 — internal helper
    )
    ddx = ddx.model_copy(update={"hypotheses": ddx.hypotheses[:limit]})
    decision = triage_engine.classify(matrix, ddx)
    intake = render_intake_report(
        matrix,
        medications=list(snap.medications),
        risk_factors=list(snap.risk_factors),
        allergies=list(snap.allergies),
        differential=ddx,
        triage=decision.model_dump(mode="json"),
        discriminator_answers=list(snap.discriminator_answers),
    )
    return {
        "is_preview": True,
        "differential": ddx.model_dump(mode="json"),
        "triage": decision.model_dump(mode="json"),
        "symptom_count": len(matrix.symptoms),
        "red_flag_count": len(matrix.red_flags),
        "denied_symptoms": list(matrix.denied_symptoms),
        "intake_report": intake,
    }


async def finalize_inline(
    *,
    context: dict[str, Any],
    session_id: str,
    question_text: str,
    tone: str,
    evaluation_matches: list[str],
    snap: Any,
    dx_agent: DifferentialDxAgent,
    triage_engine: TriageEngine,
    reasoner_ddx: DifferentialDiagnosis | None = None,
) -> dict[str, Any]:
    """Finalize the interview synchronously using the heuristic ranker.

    The full ``/triage/finalize`` endpoint still runs the LLM-backed
    ranker; this inline path is invoked automatically when the agent
    decides it is done and must return *fast* — a slow LLM call here
    leaves the patient staring at the typing indicator. The clinician
    gets the same payload shape (so the UI doesn't branch) but built
    from the deterministic ranking + intake renderer.
    """
    del context
    pseudonym = f"pt-{session_id[:8]}"
    matrix = snap.to_matrix(red_flags=evaluation_matches)
    # Prefer the reasoner's accumulated differential; fall back to the
    # deterministic ranker when the reasoner is off or was unavailable.
    ddx = (
        reasoner_ddx
        if reasoner_ddx is not None and reasoner_ddx.hypotheses
        else dx_agent._heuristic_rank(matrix)  # noqa: SLF001 — fast path
    )
    decision = triage_engine.classify(matrix, ddx)
    intake_md = render_intake_report(
        matrix,
        medications=list(snap.medications),
        risk_factors=list(snap.risk_factors),
        allergies=list(snap.allergies),
        differential=ddx,
        triage=decision.model_dump(mode="json"),
        discriminator_answers=list(snap.discriminator_answers),
        patient_pseudonym=pseudonym,
        session_id=session_id,
    )
    report = TriageReport(
        session_id=session_id,
        patient_pseudonym=pseudonym,
        symptom_matrix=matrix,
        differential=ddx,
        triage=decision.model_dump(mode="json"),
        status=ReportStatus.PENDING_VALIDATION,
        intake_report=intake_md,
    )
    triage_data = report.model_dump(mode="json")
    return {
        "success": True,
        "data": {
            "session_id": session_id,
            "question": question_text,
            "target_slot": "finalize",
            "tone": tone,
            "progress": 1.0,
            "known_symptoms": [s.canonical_name for s in snap.symptoms],
            "matrix": snap.to_matrix(red_flags=evaluation_matches).model_dump(
                mode="json"
            ),
            "preview": triage_data,
            "auto_finalized": True,
        },
        "metadata": {"session_id": session_id, "auto_finalized": True},
        "message": "Anamnesi completata; report generato.",
    }
