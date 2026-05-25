"""Factory functions for the optional ML services.

Kept in a dedicated module so the plugin entrypoint stays under the
500-line cap and the ML wiring can be unit-tested in isolation
(without the full plugin lifecycle).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.red_agent.enrichers import (
    AttackMapperEnricher,
    ComplianceMapperEnricher,
    EpssKevEnricher,
    GreyNoiseEnricher,
    OSVEnricher,
    ReachabilityEnricher,
    RiskScoringEnricher,
    VEXStore,
    VexEnricher,
)
from plugins.red_agent.ml.dedup import SemanticDedupService
from plugins.red_agent.ml.models import AnomalyDetectorService, FPClassifierService
from plugins.red_agent.ml.triage import LLMTriageService

if TYPE_CHECKING:
    from plugins.red_agent.audit import AuditLogger
    from plugins.red_agent.config import RedAgentConfig
    from plugins.red_agent.events import ScanEventBus
    from plugins.red_agent.ml.tasks import AnomalyDetectorTask

logger = get_logger(__name__)


def build_triage_service(config: "RedAgentConfig") -> LLMTriageService:
    """Build the LLM triage service.

    Resolves :class:`core.services.llm.service.LLMService` from the
    global ``ServiceRegistry`` when registered (the typical path during
    plugin init). Falls back to constructing a fresh service so the
    triage layer still works in test/dev environments where the core
    bootstrap has not registered an LLM. Any failure leaves ``llm=None``
    and the resulting service runs in disabled mode.
    """
    llm: Any = None
    if config.llm_triage_enabled:
        try:
            from core.services.llm.service import LLMService

            llm = (
                ServiceRegistry.get(LLMService)
                if ServiceRegistry.has(LLMService)
                else LLMService()
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("red_agent.triage.llm_unavailable", extra={"err": str(e)})
    return LLMTriageService(
        llm=llm,
        model=config.llm_triage_model,
        enabled=config.llm_triage_enabled,
        batch_size=config.llm_triage_batch_size,
        drop_false_positives=config.llm_triage_drop_false_positives,
        min_confidence_to_override=config.llm_triage_min_confidence_to_override,
    )


def build_dedup_service(config: "RedAgentConfig") -> SemanticDedupService:
    """Build the semantic-dedup service.

    Resolves :class:`core.services.vectorstore.service.VectorStoreService`
    from the registry and instantiates a small SentenceTransformer
    (``all-MiniLM-L6-v2``, 384-dim) for embeddings. Any failure leaves
    the corresponding dependency as ``None`` and the service runs in
    disabled mode (pass-through).
    """
    vectorstore: Any = None
    embedder: Any = None
    if config.semantic_dedup_enabled:
        try:
            from core.services.vectorstore.service import VectorStoreService

            vectorstore = (
                ServiceRegistry.get(VectorStoreService)
                if ServiceRegistry.has(VectorStoreService)
                else VectorStoreService()
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.dedup.vectorstore_unavailable", extra={"err": str(e)}
            )
        try:
            from sentence_transformers import (  # type: ignore[import-untyped]
                SentenceTransformer,
            )

            embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.dedup.embedder_unavailable", extra={"err": str(e)}
            )
    return SemanticDedupService(
        vectorstore=vectorstore,
        embedder=embedder,
        collection=config.semantic_dedup_collection,
        threshold=config.semantic_dedup_threshold,
        enabled=config.semantic_dedup_enabled,
    )


def build_fp_classifier(config: "RedAgentConfig") -> FPClassifierService:
    """Build the M1 false-positive classifier.

    Disabled mode is the default (no model artifact at the configured
    path). Operators ship a trained joblib via the same channel that
    delivers signed plugin bundles.
    """
    return FPClassifierService(
        model_path=config.ml_fp_classifier_model_path,
        drop_threshold=config.ml_fp_classifier_drop_threshold,
        enabled=config.ml_fp_classifier_enabled,
    )


def build_anomaly_detector(config: "RedAgentConfig") -> AnomalyDetectorService:
    """Build the M3 host anomaly detector."""
    return AnomalyDetectorService(
        contamination=config.ml_anomaly_contamination,
        min_samples=config.ml_anomaly_min_samples,
        enabled=config.ml_anomaly_detector_enabled,
    )


def build_epss_kev_enricher(config: "RedAgentConfig") -> EpssKevEnricher:
    """Build the EPSS + CISA KEV threat-intel enricher."""
    return EpssKevEnricher(
        enabled=config.epss_kev_enricher_enabled,
        bump_severity_on_kev=config.epss_kev_bump_severity_on_kev,
        high_epss_threshold=config.epss_kev_high_epss_threshold,
        kev_cache_ttl_seconds=config.epss_kev_cache_ttl_seconds,
        request_timeout_seconds=config.epss_kev_request_timeout_seconds,
    )


def build_attack_mapper(config: "RedAgentConfig") -> AttackMapperEnricher:
    """Build the CWE -> MITRE ATT&CK technique mapper."""
    return AttackMapperEnricher(enabled=config.attack_mapper_enabled)


def build_osv_enricher(config: "RedAgentConfig") -> OSVEnricher:
    """Build the OSV.dev advisory enricher."""
    return OSVEnricher(
        enabled=config.osv_enricher_enabled,
        request_timeout_seconds=config.osv_request_timeout_seconds,
        max_concurrent_requests=config.osv_max_concurrent_requests,
    )


def build_greynoise_enricher(config: "RedAgentConfig") -> GreyNoiseEnricher:
    """Build the GreyNoise IP-reputation enricher."""
    api_key: str | None = None
    if config.greynoise_api_key is not None:
        try:
            api_key = config.greynoise_api_key.get_secret_value()
        except Exception:  # noqa: BLE001
            api_key = None
    return GreyNoiseEnricher(
        enabled=config.greynoise_enricher_enabled,
        api_key=api_key,
        request_timeout_seconds=config.greynoise_request_timeout_seconds,
        max_concurrent_requests=config.greynoise_max_concurrent_requests,
    )


def build_vex_enricher(config: "RedAgentConfig") -> VexEnricher:
    """Build the VEX (OpenVEX + CycloneDX VEX) suppression enricher."""
    store: VEXStore | None = None
    if config.vex_enabled and config.vex_directory:
        store = VEXStore(directory=config.vex_directory)
    return VexEnricher(
        store=store,
        enabled=config.vex_enabled,
        suppress_not_affected=config.vex_suppress_not_affected,
        suppress_fixed=config.vex_suppress_fixed,
    )


def build_risk_scorer(config: "RedAgentConfig") -> RiskScoringEnricher:
    """Build the VPR-style risk-scoring enricher."""
    return RiskScoringEnricher(
        enabled=config.risk_scoring_enabled,
        kev_multiplier=config.risk_kev_multiplier,
        max_epss_multiplier=config.risk_max_epss_multiplier,
    )


def build_compliance_mapper(config: "RedAgentConfig") -> ComplianceMapperEnricher:
    """Build the compliance-pack control mapper."""
    return ComplianceMapperEnricher(enabled=config.compliance_mapper_enabled)


def build_reachability_enricher(config: "RedAgentConfig") -> ReachabilityEnricher:
    """Build the SCA reachability enricher."""
    from plugins.red_agent.models import Severity

    sev_map: dict[str, Severity] = {
        "info": Severity.INFO,
        "low": Severity.LOW,
        "medium": Severity.MEDIUM,
        "high": Severity.HIGH,
    }
    return ReachabilityEnricher(
        enabled=config.reachability_enabled,
        drop_unreachable=config.reachability_drop_unreachable,
        drop_unreachable_max_severity=sev_map.get(
            config.reachability_drop_max_severity, Severity.MEDIUM
        ),
        max_files_scanned=config.reachability_max_files,
    )


def register_ml_services(
    config: "RedAgentConfig",
) -> tuple[
    LLMTriageService,
    SemanticDedupService,
    FPClassifierService,
    AnomalyDetectorService,
    EpssKevEnricher,
    AttackMapperEnricher,
    VexEnricher,
    ReachabilityEnricher,
    RiskScoringEnricher,
    ComplianceMapperEnricher,
    OSVEnricher,
    GreyNoiseEnricher,
]:
    """Build every ML/enrichment service and register it in the global registry.

    Returns the tuple ``(triage, dedup, fp_classifier, anomaly_detector,
    epss_kev, attack_mapper, vex, reachability, risk_scorer, compliance,
    osv, greynoise)`` so the caller can pass them straight into the
    ``RedAgent`` constructor without re-resolving from the registry.
    """
    triage = build_triage_service(config)
    dedup = build_dedup_service(config)
    fp_classifier = build_fp_classifier(config)
    anomaly_detector = build_anomaly_detector(config)
    epss_kev = build_epss_kev_enricher(config)
    attack_mapper = build_attack_mapper(config)
    vex = build_vex_enricher(config)
    reachability = build_reachability_enricher(config)
    risk_scorer = build_risk_scorer(config)
    compliance = build_compliance_mapper(config)
    osv = build_osv_enricher(config)
    greynoise = build_greynoise_enricher(config)
    ServiceRegistry.register(LLMTriageService, triage)
    ServiceRegistry.register(SemanticDedupService, dedup)
    ServiceRegistry.register(FPClassifierService, fp_classifier)
    ServiceRegistry.register(AnomalyDetectorService, anomaly_detector)
    ServiceRegistry.register(EpssKevEnricher, epss_kev)
    ServiceRegistry.register(AttackMapperEnricher, attack_mapper)
    ServiceRegistry.register(VexEnricher, vex)
    ServiceRegistry.register(ReachabilityEnricher, reachability)
    ServiceRegistry.register(RiskScoringEnricher, risk_scorer)
    ServiceRegistry.register(ComplianceMapperEnricher, compliance)
    ServiceRegistry.register(OSVEnricher, osv)
    ServiceRegistry.register(GreyNoiseEnricher, greynoise)
    return (
        triage,
        dedup,
        fp_classifier,
        anomaly_detector,
        epss_kev,
        attack_mapper,
        vex,
        reachability,
        risk_scorer,
        compliance,
        osv,
        greynoise,
    )


def maybe_start_anomaly_task(
    *,
    config: "RedAgentConfig",
    detector: AnomalyDetectorService,
    audit: "AuditLogger",
    events: "ScanEventBus",
) -> "AnomalyDetectorTask | None":
    """Spawn :class:`AnomalyDetectorTask` when toggle + dependencies are present.

    Returns the started task (so the caller can wire ``stop()`` on
    plugin shutdown) or ``None`` when the toggle is off or required
    backends are not registered.
    """
    if not config.ml_anomaly_detector_enabled:
        return None
    try:
        from plugins.red_agent.persistence import (
            AgentPersistence,
            AgentTelemetryStore,
        )

        agents = ServiceRegistry.get(AgentPersistence)
        telemetry = ServiceRegistry.get(AgentTelemetryStore)
    except Exception as e:  # noqa: BLE001
        logger.info(
            "red_agent.ml.anomaly.task_not_started_missing_deps",
            extra={"err": str(e)},
        )
        return None
    if agents is None or telemetry is None or not telemetry.available:
        logger.info("red_agent.ml.anomaly.task_not_started_missing_deps")
        return None

    from plugins.red_agent.ml.tasks import AnomalyDetectorTask

    task = AnomalyDetectorTask(
        detector=detector,
        telemetry=telemetry,
        agents=agents,
        audit=audit,
        events=events,
        config=config,
    )
    task.start()
    return task
