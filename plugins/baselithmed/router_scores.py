"""
Scores, interactions, DDx challenge, FHIR export and EHR push routes.

Extracted from router.py to keep every file under the 500-LOC cap.
All logic is identical — this is a pure mechanical split.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from .audit import AuditEventType
from .audit_utils import _append_audit
from .idempotency import IdempotencyCache
from .challenger import DDxChallenger
from .ehr import EhrPusher
from .fhir import triage_report_to_fhir_bundle
from .metrics import (
    CHALLENGER_VERDICTS,
    EHR_PUSH_ATTEMPTS,
    INTERACTIONS_FINDINGS,
    normalize_label,
    safe_increment,
)
from .models.clinical import TriageReport, Vitals
from .safety.interactions import check_interactions
from .score_suggester import suggest_scores
from .scores import compute_all_scores
from .tracing import clinical_span
from .webhooks import WebhookEventType
from .tier2_scores import (
    AlvaradoInput,
    CentorInput,
    Cha2ds2VascInput,
    GcsInput,
    HasBledInput,
    HeartScoreInput,
    OttawaAnkleInput,
    OttawaKneeInput,
    PercInput,
    TimiInput,
    WellsDvtInput,
    WellsPeInput,
    compute_alvarado,
    compute_centor,
    compute_cha2ds2_vasc,
    compute_gcs,
    compute_has_bled,
    compute_heart,
    compute_ottawa_ankle,
    compute_ottawa_knee,
    compute_perc,
    compute_timi,
    compute_wells_dvt,
    compute_wells_pe,
)
from .security import require_clinical_user, require_clinical_validator


def create_scores_router(plugin_instance: Any) -> APIRouter:
    """Build the scores / interactions / FHIR / EHR sub-router."""

    router = APIRouter(prefix="", tags=["BaselithMed"])

    clinical_user_dep = Depends(require_clinical_user())
    clinical_validator_dep = Depends(require_clinical_validator())
    idempotency_cache = IdempotencyCache()

    @router.get(
        "/sessions/{session_id}/scores",
        dependencies=[clinical_user_dep],
    )
    async def get_scores(session_id: str) -> dict[str, Any]:
        # Prefer the report's matrix (finalized state) over the bare vitals
        # cache so the scoring inputs and the report stay in sync.
        get_report = getattr(plugin_instance, "get_report", None)
        get_vitals = getattr(plugin_instance, "get_vitals", None)
        stored_vitals = get_vitals(session_id) if callable(get_vitals) else None
        report_obj = get_report(session_id) if callable(get_report) else None
        if isinstance(report_obj, TriageReport):
            matrix = report_obj.symptom_matrix
            if matrix.vitals is None and isinstance(stored_vitals, Vitals):
                matrix = matrix.model_copy(update={"vitals": stored_vitals})
            return {
                "session_id": session_id,
                "scores": compute_all_scores(matrix),
            }
        from .models.clinical import SymptomMatrix

        vitals_arg = stored_vitals if isinstance(stored_vitals, Vitals) else None
        matrix = SymptomMatrix(vitals=vitals_arg)
        return {
            "session_id": session_id,
            "scores": compute_all_scores(matrix),
        }

    @router.get(
        "/triage/{session_id}/interactions",
        dependencies=[clinical_user_dep],
    )
    async def get_interactions(session_id: str) -> dict[str, Any]:
        get_report = getattr(plugin_instance, "get_report", None)
        report = get_report(session_id) if callable(get_report) else None
        if not isinstance(report, TriageReport):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No finalized report for this session.",
            )
        findings = check_interactions(report.symptom_matrix)
        for f in findings:
            safe_increment(
                INTERACTIONS_FINDINGS,
                severity=normalize_label(f.severity.value),
                kind=normalize_label(f.kind),
            )
        return {
            "session_id": session_id,
            "findings": [f.to_dict() for f in findings],
        }

    @router.get(
        "/triage/{session_id}/challenge",
        dependencies=[clinical_user_dep],
    )
    async def challenge(session_id: str) -> dict[str, Any]:
        get_report = getattr(plugin_instance, "get_report", None)
        report = get_report(session_id) if callable(get_report) else None
        if not isinstance(report, TriageReport):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No finalized report for this session.",
            )
        review = DDxChallenger().review(report.differential, report.symptom_matrix)
        safe_increment(CHALLENGER_VERDICTS, verdict=normalize_label(review.verdict))
        return {"session_id": session_id, "review": review.to_dict()}

    @router.get(
        "/sessions/{session_id}/scores/suggest",
        dependencies=[clinical_user_dep],
    )
    async def get_score_suggestions(session_id: str) -> dict[str, Any]:
        get_report = getattr(plugin_instance, "get_report", None)
        report = get_report(session_id) if callable(get_report) else None
        if isinstance(report, TriageReport):
            matrix = report.symptom_matrix
        else:
            from .models.clinical import SymptomMatrix

            get_vitals = getattr(plugin_instance, "get_vitals", None)
            stored_vitals = get_vitals(session_id) if callable(get_vitals) else None
            matrix = SymptomMatrix(
                vitals=stored_vitals if isinstance(stored_vitals, Vitals) else None
            )
        suggestions = suggest_scores(matrix)
        return {
            "session_id": session_id,
            "suggestions": [s.to_dict() for s in suggestions],
        }

    @router.post(
        "/sessions/{session_id}/scores/heart",
        dependencies=[clinical_user_dep],
    )
    async def post_heart(session_id: str, body: HeartScoreInput) -> dict[str, Any]:
        result = compute_heart(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/wells-pe",
        dependencies=[clinical_user_dep],
    )
    async def post_wells_pe(session_id: str, body: WellsPeInput) -> dict[str, Any]:
        result = compute_wells_pe(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/wells-dvt",
        dependencies=[clinical_user_dep],
    )
    async def post_wells_dvt(session_id: str, body: WellsDvtInput) -> dict[str, Any]:
        result = compute_wells_dvt(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/centor",
        dependencies=[clinical_user_dep],
    )
    async def post_centor(session_id: str, body: CentorInput) -> dict[str, Any]:
        result = compute_centor(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/perc",
        dependencies=[clinical_user_dep],
    )
    async def post_perc(session_id: str, body: PercInput) -> dict[str, Any]:
        result = compute_perc(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/timi",
        dependencies=[clinical_user_dep],
    )
    async def post_timi(session_id: str, body: TimiInput) -> dict[str, Any]:
        result = compute_timi(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/gcs",
        dependencies=[clinical_user_dep],
    )
    async def post_gcs(session_id: str, body: GcsInput) -> dict[str, Any]:
        result = compute_gcs(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/alvarado",
        dependencies=[clinical_user_dep],
    )
    async def post_alvarado(session_id: str, body: AlvaradoInput) -> dict[str, Any]:
        result = compute_alvarado(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/ottawa-ankle",
        dependencies=[clinical_user_dep],
    )
    async def post_ottawa_ankle(
        session_id: str, body: OttawaAnkleInput
    ) -> dict[str, Any]:
        result = compute_ottawa_ankle(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/ottawa-knee",
        dependencies=[clinical_user_dep],
    )
    async def post_ottawa_knee(
        session_id: str, body: OttawaKneeInput
    ) -> dict[str, Any]:
        result = compute_ottawa_knee(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/cha2ds2-vasc",
        dependencies=[clinical_user_dep],
    )
    async def post_cha2ds2_vasc(
        session_id: str, body: Cha2ds2VascInput
    ) -> dict[str, Any]:
        result = compute_cha2ds2_vasc(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.post(
        "/sessions/{session_id}/scores/has-bled",
        dependencies=[clinical_user_dep],
    )
    async def post_has_bled(session_id: str, body: HasBledInput) -> dict[str, Any]:
        result = compute_has_bled(body)
        return {"session_id": session_id, "score": result.to_dict()}

    @router.get(
        "/triage/{session_id}/fhir",
        dependencies=[clinical_user_dep],
    )
    async def export_fhir(session_id: str) -> dict[str, Any]:
        get_report = getattr(plugin_instance, "get_report", None)
        report = get_report(session_id) if callable(get_report) else None
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No finalized report for this session.",
            )
        return triage_report_to_fhir_bundle(report)

    @router.post(
        "/triage/{session_id}/push-to-ehr",
        dependencies=[clinical_validator_dep],
    )
    async def push_to_ehr(
        session_id: str,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        cache_route = f"push-to-ehr:{session_id}"
        if idempotency_key:
            cached = idempotency_cache.get(cache_route, idempotency_key)
            if cached is not None:
                return cached
        get_report = getattr(plugin_instance, "get_report", None)
        report = get_report(session_id) if callable(get_report) else None
        if not isinstance(report, TriageReport):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No finalized report for this session.",
            )
        pusher: EhrPusher | None = getattr(plugin_instance, "ehr_pusher", None)
        if pusher is None or not pusher.enabled:
            safe_increment(EHR_PUSH_ATTEMPTS, outcome="disabled")
            return {
                "session_id": session_id,
                "result": {
                    "disabled": True,
                    "ok": False,
                    "status_code": None,
                    "error": "EHR push not configured.",
                    "response_preview": None,
                },
            }
        with clinical_span("baselithmed.ehr.push", session_id=session_id):
            result = await pusher.push(report)
        outcome = "success" if result.ok else "failure"
        safe_increment(EHR_PUSH_ATTEMPTS, outcome=outcome)
        dispatcher = getattr(plugin_instance, "webhook_dispatcher", None)
        if not result.ok and dispatcher is not None and dispatcher.enabled:
            try:
                await dispatcher.dispatch(
                    WebhookEventType.EHR_PUSH_FAILED,
                    {
                        "status_code": result.status_code,
                        "error": result.error,
                    },
                    session_id=session_id,
                )
            except Exception:  # noqa: BLE001 — webhook never breaks push
                pass
        _append_audit(
            plugin_instance,
            event_type=AuditEventType.TRIAGE_FINALIZED,
            session_id=session_id,
            actor="system:ehr_push",
            payload={"result": result.to_dict()},
            summary={
                "ehr_push_outcome": outcome,
                "ehr_status_code": result.status_code,
            },
        )
        response = {"session_id": session_id, "result": result.to_dict()}
        if idempotency_key and result.ok:
            idempotency_cache.put(cache_route, idempotency_key, response)
        return response

    return router
