"""
Triage finalization flow.

Builds the standardized :class:`TriageReport`, then asks the
:class:`HumanIntervention` manager for validation. The handler never returns
a ``VALIDATED`` status on its own — that transition belongs to the clinician
endpoint in the router.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from core.human.interaction import HumanIntervention
from core.observability.logging import get_logger
from core.plugins.result import ok

from ..agents.differential_dx_agent import DifferentialDxAgent
from ..graph.repository import SymptomGraphRepository
from ..models.clinical import ReportStatus, TriageReport
from ..models.triage import TriageEngine
from ..safety.redflags import RedFlagEvaluator
from .intake_report import render_intake_report

logger = get_logger(__name__)


class TriageFlowHandler:
    """Finalize a session into a :class:`TriageReport` pending validation."""

    def __init__(
        self,
        *,
        dx_agent: DifferentialDxAgent,
        graph: SymptomGraphRepository,
        human: HumanIntervention,
        engine: TriageEngine | None = None,
        red_flags: RedFlagEvaluator | None = None,
    ) -> None:
        self._dx = dx_agent
        self._graph = graph
        self._human = human
        self._engine = engine or TriageEngine()
        self._red_flags = red_flags or RedFlagEvaluator()

    async def handle(
        self,
        query: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        del query  # the finalize intent ignores the trailing user utterance
        session_id = str(context.get("session_id") or uuid4())
        pseudonym = str(context.get("patient_pseudonym") or f"pt-{session_id[:8]}")

        evaluation = self._red_flags.evaluate(self._graph, session_id)
        snapshot = self._graph.snapshot(session_id)
        matrix = snapshot.to_matrix(red_flags=evaluation.matches)

        ddx = await self._dx.rank(matrix)
        decision = self._engine.classify(matrix, ddx)

        intake_md = render_intake_report(
            matrix,
            medications=list(snapshot.medications),
            risk_factors=list(snapshot.risk_factors),
            allergies=list(snapshot.allergies),
            differential=ddx,
            triage=decision.model_dump(mode="json"),
            discriminator_answers=list(snapshot.discriminator_answers),
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

        # The clinician validates the report via the explicit
        # ``POST /triage/{session_id}/validate`` endpoint. Only call the
        # synchronous ``HumanIntervention.request_approval`` when an
        # interactive callback is wired — otherwise the default behaviour
        # auto-rejects every report (``request_approval`` returns ``False``
        # when no callback is registered), which is what produced the
        # spurious ``STATO REJECTED`` badge on first finalize. With no
        # callback, leave the report ``PENDING_VALIDATION`` so the UI
        # surfaces a validate/reject choice to the clinician.
        request_id: str = session_id
        has_human_callback = getattr(self._human, "callback", None) is not None
        if has_human_callback:
            try:
                approved = await self._human.request_approval(
                    action_description=(
                        f"Validare il triage report per la sessione {session_id} "
                        f"(codice {decision.code.value})."
                    ),
                    context={"report_id": session_id, "code": decision.code.value},
                    timeout=None,
                )
                report = report.model_copy(
                    update={
                        "validation_request_id": request_id,
                        "status": (
                            ReportStatus.VALIDATED
                            if approved
                            else ReportStatus.REJECTED
                        ),
                    }
                )
            except Exception as exc:  # noqa: BLE001 — log and keep pending
                logger.warning(
                    "HumanIntervention unavailable, report remains PENDING: %s",
                    exc,
                )
        else:
            report = report.model_copy(update={"validation_request_id": request_id})

        envelope = ok(
            data=report.model_dump(mode="json"),
            message=f"Triage report ready ({report.status.value}).",
            metadata={
                "requires_human": report.status == ReportStatus.PENDING_VALIDATION,
                "session_id": session_id,
                "validation_request_id": request_id,
            },
        )
        return envelope.model_dump(mode="json")
