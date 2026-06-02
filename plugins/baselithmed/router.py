"""
FastAPI router for BaselithMed.

Exposes the conversational endpoints (``/interview``, ``/triage/finalize``)
and the clinician-only validation endpoint. The router is intentionally thin:
all clinical logic lives in the flow handlers.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from .audit import AuditEventType
from .idempotency import IdempotencyCache
from .challenger import DDxChallenger
from .ehr import EhrPusher
from .fhir import triage_report_to_fhir_bundle
from .metrics import (
    CHALLENGER_VERDICTS,
    EHR_PUSH_ATTEMPTS,
    FINALIZE_LATENCY,
    INTERACTIONS_FINDINGS,
    INTERVIEW_TURN_LATENCY,
    INTERVIEW_TURNS,
    SESSIONS_CREATED,
    TRIAGE_DECISIONS,
    VALIDATIONS,
    normalize_label,
    safe_increment,
    safe_observe,
)
from .models.clinical import TriageReport, Vitals
from .safety.interactions import check_interactions
from .safety.phi import redact_dict
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


def _append_audit(
    plugin_instance: Any,
    *,
    event_type: AuditEventType,
    session_id: str,
    actor: str,
    payload: Any,
    summary: dict[str, Any],
) -> None:
    """Best-effort audit append. Never raises into the response path.

    Summaries are PHI-redacted before persistence so the durable ledger
    cannot leak Italian Codice Fiscale / phone / email / DOB even when
    the upstream caller forgot to scrub them.
    """
    ledger = getattr(plugin_instance, "audit_ledger", None)
    if ledger is None:
        return
    try:
        clean_summary = redact_dict(summary)
        if not isinstance(clean_summary, dict):
            clean_summary = summary
        ledger.append(
            event_type=event_type,
            session_id=session_id,
            actor=actor,
            payload=payload,
            summary=clean_summary,
        )
    except Exception:  # noqa: BLE001 — audit must never break the request
        pass


class CreateSessionRequest(BaseModel):
    patient_pseudonym: str | None = None


class SessionCreated(BaseModel):
    session_id: str
    patient_pseudonym: str


class InterviewTurnRequest(BaseModel):
    session_id: str
    utterance: str = Field(min_length=1, max_length=4000)


class FinalizeRequest(BaseModel):
    session_id: str
    patient_pseudonym: str | None = None


class ValidationRequest(BaseModel):
    approved: bool
    clinician_id: str
    notes: str | None = None


def create_router(plugin_instance: Any) -> APIRouter:
    """Build the BaselithMed API router bound to a plugin instance."""

    router = APIRouter(prefix="", tags=["BaselithMed"])

    @router.get("/info")
    async def info() -> dict[str, Any]:
        provider = plugin_instance._provider  # noqa: SLF001
        return {
            "plugin": plugin_instance.metadata.name,
            "version": plugin_instance.metadata.version,
            "model_id": getattr(provider, "model_id", None) if provider else None,
            "host": getattr(provider, "api_base", None) if provider else None,
            "context_window": getattr(provider, "context_window", None)
            if provider
            else None,
        }

    @router.get("/health")
    async def health() -> dict[str, Any]:
        """Liveness probe — always 200 once the router is mounted.

        Kubernetes liveness should NOT fail when LLM is unavailable
        because that would cause a kubelet to kill the pod over a
        transient upstream outage. Readiness (below) is the gated probe.
        """
        return {"status": "alive", "plugin": plugin_instance.metadata.name}

    @router.get("/ready")
    async def ready() -> dict[str, Any]:
        """Readiness probe — 200 only when handlers + audit ledger ready.

        Returns 503 with structured detail otherwise so the load balancer
        can stop routing traffic until initialization completes.
        """
        checks = {
            "interview_handler": plugin_instance.interview_handler is not None,
            "triage_handler": plugin_instance.triage_handler is not None,
            "provider": getattr(plugin_instance, "_provider", None) is not None,
        }
        audit = getattr(plugin_instance, "audit_ledger", None)
        if audit is not None:
            try:
                checks["audit_chain_valid"] = bool(audit.verify())
            except Exception:  # noqa: BLE001
                checks["audit_chain_valid"] = False
        all_ok = all(checks.values())
        if not all_ok:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not_ready", "checks": checks},
            )
        return {"status": "ready", "checks": checks}

    clinical_user_dep = Depends(require_clinical_user())
    clinical_validator_dep = Depends(require_clinical_validator())
    idempotency_cache = IdempotencyCache()

    @router.post(
        "/sessions",
        response_model=SessionCreated,
        dependencies=[clinical_user_dep],
    )
    async def create_session(req: CreateSessionRequest) -> SessionCreated:
        session_id = str(uuid4())
        pseudonym = req.patient_pseudonym or f"pt-{session_id[:8]}"
        plugin_instance.register_session(session_id, pseudonym)
        safe_increment(SESSIONS_CREATED)
        return SessionCreated(session_id=session_id, patient_pseudonym=pseudonym)

    @router.post("/interview", dependencies=[clinical_user_dep])
    async def interview_turn(req: InterviewTurnRequest) -> dict[str, Any]:
        handler = plugin_instance.interview_handler
        if handler is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plugin not initialized.",
            )
        turn_id = str(uuid4())
        started_at = time.perf_counter()
        with clinical_span(
            "baselithmed.interview.turn",
            session_id=req.session_id,
            turn_id=turn_id,
            utterance_length=len(req.utterance),
        ):
            result = await handler.handle(
                query=req.utterance,
                context={"session_id": req.session_id, "turn_id": turn_id},
            )
        safe_observe(INTERVIEW_TURN_LATENCY, time.perf_counter() - started_at)
        safe_increment(INTERVIEW_TURNS)
        _append_audit(
            plugin_instance,
            event_type=AuditEventType.INTERVIEW_TURN,
            session_id=req.session_id,
            actor="patient",
            payload={"utterance": req.utterance, "turn_id": turn_id},
            summary={
                "turn_id": turn_id,
                "utterance_length": len(req.utterance),
                "result_status": result.get("status"),
            },
        )
        return result

    @router.post("/triage/finalize", dependencies=[clinical_user_dep])
    async def finalize(req: FinalizeRequest) -> dict[str, Any]:
        handler = plugin_instance.triage_handler
        if handler is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plugin not initialized.",
            )
        started_at = time.perf_counter()
        with clinical_span(
            "baselithmed.triage.finalize",
            session_id=req.session_id,
            has_pseudonym=req.patient_pseudonym is not None,
        ):
            result = await handler.handle(
                query="",
                context={
                    "session_id": req.session_id,
                    "patient_pseudonym": req.patient_pseudonym,
                },
            )
        safe_observe(FINALIZE_LATENCY, time.perf_counter() - started_at)
        report_dict = result.get("data") if isinstance(result, dict) else None
        triage_code = None
        report_status = None
        if isinstance(report_dict, dict):
            triage = report_dict.get("triage")
            if isinstance(triage, dict):
                triage_code = triage.get("code")
            report_status = report_dict.get("status")
            if triage_code:
                safe_increment(TRIAGE_DECISIONS, code=normalize_label(triage_code))
            # Fire webhooks: always TRIAGE_FINALIZED; additionally
            # RED_FLAG_DETECTED when the deterministic engine surfaced any
            # red flag (matrix.red_flags non-empty in the report payload).
            dispatcher = getattr(plugin_instance, "webhook_dispatcher", None)
            if dispatcher is not None and dispatcher.enabled:
                try:
                    import asyncio as _asyncio

                    loop = _asyncio.get_running_loop()
                    loop.create_task(
                        dispatcher.dispatch(
                            WebhookEventType.TRIAGE_FINALIZED,
                            {
                                "triage_code": triage_code,
                                "status": report_status,
                            },
                            session_id=req.session_id,
                        )
                    )
                    matrix = report_dict.get("symptom_matrix") or {}
                    red_flags = (
                        matrix.get("red_flags") if isinstance(matrix, dict) else None
                    )
                    if red_flags:
                        loop.create_task(
                            dispatcher.dispatch(
                                WebhookEventType.RED_FLAG_DETECTED,
                                {"red_flags": list(red_flags)},
                                session_id=req.session_id,
                            )
                        )
                except RuntimeError:
                    pass
            try:
                report_obj = TriageReport.model_validate(report_dict)
                # Graft any captured vitals onto the report's matrix so
                # downstream FHIR/scores see a coherent payload.
                get_vitals = getattr(plugin_instance, "get_vitals", None)
                stored_vitals = (
                    get_vitals(req.session_id) if callable(get_vitals) else None
                )
                if (
                    isinstance(stored_vitals, Vitals)
                    and report_obj.symptom_matrix.vitals is None
                ):
                    new_matrix = report_obj.symptom_matrix.model_copy(
                        update={"vitals": stored_vitals}
                    )
                    report_obj = report_obj.model_copy(
                        update={"symptom_matrix": new_matrix}
                    )
                store = getattr(plugin_instance, "store_report", None)
                if callable(store):
                    store(req.session_id, report_obj)
            except Exception:  # noqa: BLE001 — cache miss must not fail finalize
                pass
        _append_audit(
            plugin_instance,
            event_type=AuditEventType.TRIAGE_FINALIZED,
            session_id=req.session_id,
            actor="system",
            payload={"result": result},
            summary={
                "triage_code": triage_code,
                "report_status": report_status,
            },
        )
        return result

    @router.post(
        "/triage/{session_id}/validate",
        dependencies=[clinical_validator_dep],
    )
    async def validate(
        session_id: str,
        req: ValidationRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        cache_route = f"validate:{session_id}"
        if idempotency_key:
            cached = idempotency_cache.get(cache_route, idempotency_key)
            if cached is not None:
                return cached
        ok_validated = plugin_instance.record_validation(
            session_id=session_id,
            approved=req.approved,
            clinician_id=req.clinician_id,
            notes=req.notes,
        )
        if not ok_validated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unknown session or report not awaiting validation.",
            )
        safe_increment(VALIDATIONS, approved=normalize_label(req.approved))
        response = {"session_id": session_id, "validated": req.approved}
        if idempotency_key:
            idempotency_cache.put(cache_route, idempotency_key, response)
        return response

    @router.put(
        "/sessions/{session_id}/vitals",
        dependencies=[clinical_user_dep],
    )
    async def set_vitals(session_id: str, vitals: Vitals) -> dict[str, Any]:
        store = getattr(plugin_instance, "store_vitals", None)
        if not callable(store):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vitals capture unavailable.",
            )
        store(session_id, vitals)
        return {"session_id": session_id, "vitals": vitals.model_dump(mode="json")}

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

    @router.post(
        "/retention/purge",
        dependencies=[clinical_validator_dep],
    )
    async def purge_retention() -> dict[str, Any]:
        purge = getattr(plugin_instance, "purge_expired_sessions", None)
        if not callable(purge):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Retention policy unavailable.",
            )
        report = purge()
        return {
            "report": report.to_dict(),
            "retention_days": getattr(
                plugin_instance.retention_policy, "retention_days", None
            )
            if hasattr(plugin_instance, "retention_policy")
            else None,
        }

    @router.get(
        "/calibration/stats",
        dependencies=[clinical_validator_dep],
    )
    async def get_calibration_stats() -> dict[str, Any]:
        store = getattr(plugin_instance, "calibration_store", None)
        if store is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Calibration store unavailable.",
            )
        return store.report().to_dict()

    @router.get(
        "/audit/{session_id}",
        dependencies=[clinical_validator_dep],
    )
    async def get_audit(session_id: str) -> dict[str, Any]:
        ledger = getattr(plugin_instance, "audit_ledger", None)
        if ledger is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Audit ledger unavailable.",
            )
        entries = [e.to_dict() for e in ledger.entries(session_id=session_id)]
        return {
            "session_id": session_id,
            "entries": entries,
            "chain_valid": ledger.verify(),
        }

    return router
