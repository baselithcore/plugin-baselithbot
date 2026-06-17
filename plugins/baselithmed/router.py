"""
FastAPI router for BaselithMed.

Exposes the conversational endpoints (``/interview``, ``/triage/finalize``)
and the clinician-only validation endpoint. The router is intentionally thin:
all clinical logic lives in the flow handlers.

Sub-routers (scores/interactions/FHIR/EHR and admin) are assembled here via
``include_router`` — see ``router_scores.py`` and ``router_admin.py``.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from .audit import AuditEventType
from .idempotency import IdempotencyCache
from .metrics import (
    FINALIZE_LATENCY,
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
from .tracing import clinical_span
from .audit_utils import _append_audit
from .webhooks import WebhookEventType
from .security import require_clinical_user, require_clinical_validator
from .router_scores import create_scores_router
from .router_admin import create_admin_router


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

    router.include_router(create_scores_router(plugin_instance))
    router.include_router(create_admin_router(plugin_instance))

    return router
