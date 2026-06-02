"""
BaselithMed plugin entrypoint.

Composes the LLM provider, symptom graph, agents, flow handlers, router and
HITL manager into a single registration surface for the core
:class:`core.plugins.PluginRegistry`. Domain logic is delegated to the
specialized modules under this package; this file only wires them together.
"""

from __future__ import annotations

import asyncio
import os
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
from .ehr import EhrPushConfig, EhrPusher
from .flows.interview_flow import InterviewFlowHandler
from .flows.triage_flow import TriageFlowHandler
from .lexicons import DEFAULT_LANGUAGE, load_symptom_lexicon
from .metrics import DX_TOP1_CONFIDENCE, safe_observe
from .persistence import SQLiteAuditBackend
from .retention import PurgeReport, RetentionPolicy, RetentionRunner, purge_expired
from .safety.phi import redact
from .webhooks import (
    WebhookConfig,
    WebhookDispatcher,
    WebhookEventType,
    WebhookTarget,
)
from .graph.entities import (
    SYMPTOM_GRAPH_ENTITIES,
    SYMPTOM_GRAPH_RELATIONSHIPS,
)
from .graph.repository import SymptomGraphRepository
from .models.clinical import ReportStatus
from .providers.medgemma_ollama import OllamaMedGemmaProvider
from .router import create_router
from .safety.redflags import RedFlagEvaluator

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
        retention_cfg = config.get("retention", {}) if isinstance(config, dict) else {}
        retention_days_raw = (
            retention_cfg.get("days") or os.getenv("BASELITHMED_RETENTION_DAYS") or 30
        )
        try:
            self._retention.retention_days = int(retention_days_raw)
        except (TypeError, ValueError):
            logger.warning(
                "Invalid BASELITHMED_RETENTION_DAYS=%r; defaulting to 30.",
                retention_days_raw,
            )
            self._retention.retention_days = 30
        audit_cfg = config.get("audit", {}) if isinstance(config, dict) else {}
        audit_path = audit_cfg.get("sqlite_path") or os.getenv(
            "BASELITHMED_AUDIT_DB_PATH"
        )
        if audit_path:
            try:
                self._audit_backend = SQLiteAuditBackend(audit_path)
                self._audit = AuditLedger(backend=self._audit_backend)
                logger.info(
                    "BaselithMed audit ledger persisted to SQLite: %s",
                    audit_path,
                )
            except Exception as exc:  # noqa: BLE001 — degrade to in-memory
                logger.warning(
                    "Failed to open SQLite audit backend %r (%s); "
                    "continuing with in-memory ledger.",
                    audit_path,
                    exc,
                )
        ehr_cfg_dict = config.get("ehr", {}) if isinstance(config, dict) else {}
        ehr_config: EhrPushConfig | None = None
        if ehr_cfg_dict.get("url"):
            try:
                ehr_config = EhrPushConfig.model_validate(ehr_cfg_dict)
            except Exception as exc:  # noqa: BLE001 — invalid config disables push
                logger.warning(
                    "BaselithMed EHR config invalid (%s); push disabled.", exc
                )
        if ehr_config is None:
            ehr_config = EhrPushConfig.from_env()
        if ehr_config is not None:
            self._ehr_pusher = EhrPusher(ehr_config)
            logger.info("BaselithMed EHR push enabled: %s", ehr_config.url)
        provider_cfg = config.get("provider", {}) if isinstance(config, dict) else {}
        host = provider_cfg.get("host") or os.getenv("BASELITHMED_OLLAMA_HOST")
        num_predict_raw = provider_cfg.get("num_predict")
        keep_alive = str(provider_cfg.get("keep_alive", "30m"))
        context_window = int(provider_cfg.get("context_window", 8192))
        temperature = float(provider_cfg.get("temperature", 0.2))
        # Main provider — quality-sensitive finalize DDx ranking.
        self._provider = OllamaMedGemmaProvider(
            api_base=host,
            model_id=(
                provider_cfg.get("model_id")
                or os.getenv("BASELITHMED_MODEL_ID")
                or "medgemma:4b"
            ),
            temperature=temperature,
            context_window=context_window,
            keep_alive=keep_alive,
            num_predict=int(num_predict_raw) if num_predict_raw else None,
        )
        # Optional fast provider — latency-sensitive per-turn extraction +
        # anamnesis questions. When ``fast_model_id`` is unset the main
        # provider is reused (single-model behaviour, fully backward-compat).
        fast_model_id = provider_cfg.get("fast_model_id") or os.getenv(
            "BASELITHMED_FAST_MODEL_ID"
        )
        if fast_model_id and fast_model_id != self._provider.model_id:
            self._fast_provider = OllamaMedGemmaProvider(
                api_base=host,
                model_id=str(fast_model_id),
                temperature=temperature,
                context_window=context_window,
                keep_alive=keep_alive,
                num_predict=int(num_predict_raw) if num_predict_raw else None,
            )
            logger.info(
                "BaselithMed dual-model: fast=%s, finalize=%s",
                fast_model_id,
                self._provider.model_id,
            )
        else:
            self._fast_provider = self._provider
        # Per-turn LLM budget. With a fast model (~1-2s) keep it tight; with
        # only a big model (medgemma:27b, ~13-15s) raise it or every turn
        # falls back to the deterministic question/DDx bank.
        turn_timeout = float(
            provider_cfg.get("turn_timeout_seconds")
            or os.getenv("BASELITHMED_TURN_TIMEOUT_SECONDS")
            or 3.0
        )
        self._anamnesis_agent = AnamnesisAgent(
            provider=self._fast_provider,
            graph=self._graph_repo,
            turn_timeout_seconds=turn_timeout,
        )
        lang = (
            provider_cfg.get("language")
            or os.getenv("BASELITHMED_LANG")
            or DEFAULT_LANGUAGE
        )
        canonicalization_lexicon: tuple[tuple[str, str, str | None], ...] | None
        canonicalization_lexicon = None
        try:
            loaded = load_symptom_lexicon(lang)
            canonicalization_lexicon = loaded
            logger.info(
                "BaselithMed canonicalization lexicon: %s (%d entries)",
                lang,
                len(loaded),
            )
        except Exception as exc:  # noqa: BLE001 — fall back to default IT
            logger.warning(
                "BaselithMed lexicon load for %r failed (%s); using default Italian.",
                lang,
                exc,
            )
        self._dx_agent = DifferentialDxAgent(
            provider=self._provider,
            fast_provider=self._fast_provider,
            canonicalization_lexicon=canonicalization_lexicon,
            turn_timeout_seconds=turn_timeout,
        )
        # Hypothesis-driven clinical reasoner. Off by default for zero
        # regression; enable via ``reasoning.enabled`` in plugins.yaml. The
        # live loop uses the fast provider by default (latency-sensitive);
        # set ``reasoning.model: main`` to use the larger finalize model.
        reasoning_cfg = config.get("reasoning", {}) if isinstance(config, dict) else {}
        use_reasoner = bool(reasoning_cfg.get("enabled", False))
        reasoner_model = str(reasoning_cfg.get("model", "fast")).lower()
        reasoner_provider = (
            self._provider if reasoner_model == "main" else self._fast_provider
        )
        self._reasoner = ClinicalReasoner(
            provider=reasoner_provider,
            turn_timeout_seconds=turn_timeout,
        )
        if use_reasoner:
            logger.info(
                "BaselithMed hypothesis-driven reasoner ENABLED (model=%s).",
                reasoner_provider.model_id,
            )
        red_flags = RedFlagEvaluator()
        self.interview_handler = InterviewFlowHandler(
            anamnesis_agent=self._anamnesis_agent,
            dx_agent=self._dx_agent,
            graph=self._graph_repo,
            red_flags=red_flags,
            reasoner=self._reasoner,
            use_reasoner=use_reasoner,
        )
        self.triage_handler = TriageFlowHandler(
            dx_agent=self._dx_agent,
            graph=self._graph_repo,
            human=self._human,
            red_flags=red_flags,
        )
        # Late-bind so InterviewFlowHandler can finalize inline when the
        # anamnesis loop has no more slots to ask.
        self.interview_handler.set_triage_handler(self.triage_handler)
        # Optional background retention runner. The interval defaults to
        # 24 h; setting it to 0 (or unsetting the env var) keeps the
        # runner off — admin endpoint POST /retention/purge stays usable.
        runner_interval_raw = retention_cfg.get("runner_interval_seconds") or os.getenv(
            "BASELITHMED_RETENTION_RUNNER_INTERVAL_SECONDS"
        )
        try:
            runner_interval = float(runner_interval_raw) if runner_interval_raw else 0.0
        except (TypeError, ValueError):
            runner_interval = 0.0
        webhook_cfg_raw = config.get("webhooks") if isinstance(config, dict) else None
        try:
            if isinstance(webhook_cfg_raw, dict) and webhook_cfg_raw.get("targets"):
                targets = [
                    WebhookTarget.model_validate(t) for t in webhook_cfg_raw["targets"]
                ]
                self._webhooks = WebhookDispatcher(WebhookConfig(targets=targets))
            else:
                env_cfg = WebhookConfig.from_env()
                if env_cfg.targets:
                    self._webhooks = WebhookDispatcher(env_cfg)
        except Exception as exc:  # noqa: BLE001 — disable webhooks on bad cfg
            logger.warning("BaselithMed webhook config invalid (%s).", exc)
        if self._webhooks.enabled:
            logger.info(
                "BaselithMed webhooks enabled: %d target(s).",
                len(self._webhooks._config.targets),
            )
        if runner_interval > 0:
            runner = RetentionRunner(
                self, self._retention, interval_seconds=runner_interval
            )
            runner.start()
            self._retention_runner = runner
            logger.info(
                "BaselithMed retention runner enabled (every %.0fs).",
                runner_interval,
            )

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
