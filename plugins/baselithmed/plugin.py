"""
BaselithMed plugin entrypoint.

Composes the LLM provider, symptom graph, agents, flow handlers, router and
HITL manager into a single registration surface for the core
:class:`core.plugins.PluginRegistry`. Domain logic is delegated to the
specialized modules under this package; this file only wires them together.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from core.human.interaction import HumanIntervention
from core.observability.logging import get_logger
from core.plugins import AgentPlugin, GraphPlugin, RouterPlugin

from .agents.anamnesis_agent import AnamnesisAgent
from .agents.clinical_reasoner import ClinicalReasoner
from .agents.differential_dx_agent import DifferentialDxAgent
from .audit import AuditEventType, AuditLedger
from .calibration import CalibrationStore
from .ehr import EhrPusher
from .flows.interview_flow import InterviewFlowHandler
from .flows.triage_flow import TriageFlowHandler
from .metrics import DX_TOP1_CONFIDENCE, safe_observe
from .persistence import SQLiteAuditBackend
from .plugin_init import (
    _setup_agents_and_handlers,
    _setup_audit,
    _setup_ehr,
    _setup_providers,
    _setup_retention,
    _setup_retention_runner,
    _setup_webhooks,
)
from .retention import PurgeReport, RetentionPolicy, RetentionRunner, purge_expired
from .safety.phi import redact
from .webhooks import (
    WebhookDispatcher,
    WebhookEventType,
)
from .graph.entities import (
    SYMPTOM_GRAPH_ENTITIES,
    SYMPTOM_GRAPH_RELATIONSHIPS,
)
from .graph.repository import SymptomGraphRepository
from .models.clinical import ReportStatus
from .providers.medgemma_ollama import OllamaMedGemmaProvider
from .router import create_router

logger = get_logger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent / "ui" / "dist"


class BaselithMedPlugin(AgentPlugin, RouterPlugin, GraphPlugin):
    """Empathic anamnesis + DDx + standardized triage plugin."""

    def __init__(self) -> None:
        super().__init__()
        self._provider: OllamaMedGemmaProvider | None = None
        self._fast_provider: OllamaMedGemmaProvider | None = None
        self._graph_repo = SymptomGraphRepository()
        self._human = HumanIntervention()
        self._anamnesis_agent: AnamnesisAgent | None = None
        self._dx_agent: DifferentialDxAgent | None = None
        self._reasoner: ClinicalReasoner | None = None
        self.interview_handler: InterviewFlowHandler | None = None
        self.triage_handler: TriageFlowHandler | None = None
        self._sessions: dict[str, dict[str, Any]] = {}
        self._validations: dict[str, dict[str, Any]] = {}
        self._reports: dict[str, Any] = {}
        self._vitals: dict[str, Any] = {}
        self._audit_backend: SQLiteAuditBackend | None = None
        self._audit = AuditLedger()
        self._calibration = CalibrationStore()
        self._ehr_pusher: EhrPusher = EhrPusher()
        self._retention = RetentionPolicy()
        self._retention_runner: RetentionRunner | None = None
        self._webhooks = WebhookDispatcher()

    async def initialize(self, config: dict[str, Any]) -> None:
        await super().initialize(config)
        _setup_retention(self, config)
        _setup_audit(self, config)
        _setup_ehr(self, config)
        _setup_providers(self, config)
        _setup_agents_and_handlers(self, config)
        _setup_webhooks(self, config)
        _setup_retention_runner(self, config)

    async def shutdown(self) -> None:
        if self._retention_runner is not None:
            await self._retention_runner.stop()
            self._retention_runner = None
        if (
            self._fast_provider is not None
            and self._fast_provider is not self._provider
        ):
            await self._fast_provider.close()
        self._fast_provider = None
        if self._provider is not None:
            await self._provider.close()
            self._provider = None
        if self._audit_backend is not None:
            self._audit_backend.close()
            self._audit_backend = None
        await super().shutdown()

    def create_agent(self, service: Any, **kwargs: Any) -> Any:
        del service, kwargs
        if self._anamnesis_agent is None:
            raise RuntimeError("BaselithMed not initialized; call initialize() first.")
        return self._anamnesis_agent

    def get_agents(self) -> list[Any]:
        agents: list[Any] = []
        if self._anamnesis_agent is not None:
            agents.append(self._anamnesis_agent)
        if self._dx_agent is not None:
            agents.append(self._dx_agent)
        return agents

    def create_router(self) -> Any:
        return create_router(self)

    def register_entity_types(self) -> list[dict[str, Any]]:
        return SYMPTOM_GRAPH_ENTITIES

    def register_relationship_types(self) -> list[dict[str, Any]]:
        return SYMPTOM_GRAPH_RELATIONSHIPS

    def get_intent_patterns(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "med_anamnesis_intake",
                "patterns": [
                    "sintomo",
                    "dolore",
                    "non mi sento",
                    "ho male",
                    "soffro di",
                    "mi fa male",
                    "da quando",
                ],
                "handler": "interview",
                "priority": 250,
            },
            {
                "name": "med_anamnesis_followup",
                "patterns": ["peggiora", "migliora", "frequenza", "irradia"],
                "handler": "interview",
                "priority": 240,
            },
            {
                "name": "med_triage_finalize",
                "patterns": ["riassumi", "report", "concludi visita", "finalizza"],
                "handler": "triage",
                "priority": 260,
            },
        ]

    def get_flow_handlers(self) -> dict[str, Any]:
        if self.interview_handler is None or self.triage_handler is None:
            return {}
        return {
            "med_anamnesis_intake": self.interview_handler.handle,
            "med_anamnesis_followup": self.interview_handler.handle,
            "med_triage_finalize": self.triage_handler.handle,
        }

    def get_ui_tabs(self) -> list[dict[str, str]]:
        return [{"id": "baselithmed", "label": "Triage clinico"}]

    def get_static_assets_path(self) -> Path | None:
        return _STATIC_DIR if _STATIC_DIR.exists() else None

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "model_id": {"type": "string"},
                        "temperature": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "context_window": {"type": "integer", "minimum": 2048},
                    },
                },
                "triage": {
                    "type": "object",
                    "properties": {
                        "scale": {"const": "IT_4_COLOR"},
                        "human_gate": {"const": "HARD"},
                    },
                },
            },
        }

    # --- helpers used by the router -----------------------------------------

    def register_session(self, session_id: str, pseudonym: str) -> None:
        self._sessions[session_id] = {"pseudonym": pseudonym}
        self._retention.mark_touched(session_id)
        self._audit.append(
            event_type=AuditEventType.SESSION_CREATED,
            session_id=session_id,
            actor="system",
            payload={"pseudonym": pseudonym},
            summary={"pseudonym": pseudonym},
        )

    def record_validation(
        self,
        *,
        session_id: str,
        approved: bool,
        clinician_id: str,
        notes: str | None,
    ) -> bool:
        if session_id not in self._sessions:
            return False
        self._retention.mark_touched(session_id)
        new_status = (
            ReportStatus.VALIDATED.value if approved else ReportStatus.REJECTED.value
        )
        safe_notes = redact(notes) if notes else notes
        self._validations[session_id] = {
            "approved": approved,
            "clinician_id": clinician_id,
            "notes": safe_notes,
            "status": new_status,
        }
        cached = self._reports.get(session_id)
        if cached is not None and hasattr(cached, "model_copy"):
            self._reports[session_id] = cached.model_copy(
                update={
                    "status": ReportStatus(new_status),
                    "validator_signature": clinician_id,
                }
            )
        self._audit.append(
            event_type=AuditEventType.VALIDATION_RECORDED,
            session_id=session_id,
            actor=clinician_id,
            payload={
                "approved": approved,
                "clinician_id": clinician_id,
                "notes": safe_notes,
            },
            summary={"approved": approved, "status": new_status},
        )
        # Record calibration sample using the stored report's top
        # hypothesis as the model's "bet". Skip when no hypothesis exists
        # (empty DDx) so we never penalize the model for evidence-free
        # sessions.
        report = self._reports.get(session_id)
        if report is not None and hasattr(report, "differential"):
            hyps = report.differential.hypotheses
            if hyps:
                top = hyps[0]
                try:
                    self._calibration.record(
                        session_id=session_id,
                        hypothesis=top.condition,
                        predicted_confidence=float(top.confidence),
                        outcome=1 if approved else 0,
                    )
                except Exception:  # noqa: BLE001 — calibration is non-critical
                    pass
                safe_observe(DX_TOP1_CONFIDENCE, float(top.confidence))
        # Fan out webhook (fire-and-forget). Scheduling rather than
        # awaiting keeps the synchronous record_validation path uncoupled
        # from network latency. If there is no running loop (CLI / unit
        # test contexts) the dispatch is silently skipped.
        if self._webhooks.enabled:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self._webhooks.dispatch(
                        WebhookEventType.VALIDATION_RECORDED,
                        {
                            "approved": approved,
                            "status": new_status,
                            "clinician_id": clinician_id,
                        },
                        session_id=session_id,
                    )
                )
            except RuntimeError:
                pass
        return True

    @property
    def calibration_store(self) -> CalibrationStore:
        return self._calibration

    @property
    def ehr_pusher(self) -> EhrPusher:
        return self._ehr_pusher

    @property
    def webhook_dispatcher(self) -> WebhookDispatcher:
        return self._webhooks

    @property
    def audit_ledger(self) -> AuditLedger:
        return self._audit

    def store_report(self, session_id: str, report: Any) -> None:
        """Cache the latest finalized report so FHIR/audit can read it."""
        self._reports[session_id] = report
        self._retention.mark_touched(session_id)

    def get_report(self, session_id: str) -> Any | None:
        return self._reports.get(session_id)

    def store_vitals(self, session_id: str, vitals: Any) -> None:
        """Cache captured vitals for use by clinical-score calculators."""
        self._vitals[session_id] = vitals
        self._retention.mark_touched(session_id)

    def get_vitals(self, session_id: str) -> Any | None:
        return self._vitals.get(session_id)

    @property
    def retention_policy(self) -> RetentionPolicy:
        return self._retention

    def purge_expired_sessions(self) -> PurgeReport:
        """Crypto-shred all per-session data past the retention window."""
        return purge_expired(self, self._retention)
