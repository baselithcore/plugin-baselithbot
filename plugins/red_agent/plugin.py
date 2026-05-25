"""Red Agent plugin entrypoint."""

from __future__ import annotations

import asyncio
from typing import Any

from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from core.plugins.agent_plugin import AgentPlugin
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.approvals import ApprovalRegistry
from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.events import (
    ActivityEventBus,
    ScanEngagementIndex,
    ScanEventBus,
)
from plugins.red_agent.graph import VulnerabilityGraph
from plugins.red_agent.integrations import (
    AutoRemediationService,
    WebhookNotifier,
    WebhookReceiver,
)
from plugins.red_agent.models import Severity as _Severity
from plugins.red_agent.ml.factories import (
    maybe_start_anomaly_task,
    register_ml_services,
)
from plugins.red_agent.ml.tasks import AnomalyDetectorTask
from plugins.red_agent.persistence import (
    AgentAuditLog,
    AgentCertPersistence,
    AgentPersistence,
    AgentTelemetryStore,
    ApprovalPersistence,
    EngagementPersistence,
    EnrollmentTokenPersistence,
    FingerprintStore,
    PolicyStore,
    RedAgentPersistence,
    TargetPersistence,
    ensure_schema,
)
from plugins.red_agent.policy import apply_overrides
from plugins.red_agent.rules_of_engagement import RuleOfEngagementEngine
from plugins.red_agent.tasks import AuditRetentionTask, ScheduleDispatcherTask
from plugins.red_agent.routers import (
    activity_router,
    agents_router,
    approve_router,
    autopr_router,
    engagements_router,
    file_scan_router,
    findings_router,
    graph_chat_router,
    graph_router,
    health_router,
    playbooks_router,
    preflight_router,
    reports_router,
    scan_router,
    settings_router,
    targets_router,
    triage_router,
    webhooks_router,
    ws_router,
)
from plugins.red_agent.sandbox_runner import SandboxRunner

logger = get_logger(__name__)


def _resolve_dsn(plugin_dsn: str | None) -> str:
    """Plugin-level DSN takes precedence; fall back to core StorageConfig."""
    if plugin_dsn:
        return plugin_dsn
    try:
        from core.config.storage import get_storage_config

        cfg = get_storage_config()
        if not cfg.postgres_enabled:
            return ""
        return cfg.conninfo
    except Exception as e:  # noqa: BLE001
        logger.warning("red_agent.dsn.resolve_failed", extra={"err": str(e)})
        return ""


_SEVERITY_FROM_STR: dict[str, _Severity] = {
    "info": _Severity.INFO,
    "low": _Severity.LOW,
    "medium": _Severity.MEDIUM,
    "high": _Severity.HIGH,
    "critical": _Severity.CRITICAL,
}


def _severity_from_str(value: str) -> _Severity:
    return _SEVERITY_FROM_STR.get(value.lower(), _Severity.HIGH)


class RedAgentPlugin(AgentPlugin):
    """Plugin glue: registers services, mounts routers, returns agent."""

    name = "red_agent"
    version = "0.1.0"

    def __init__(self) -> None:
        super().__init__()
        self._agent: RedAgent | None = None
        self._retention_task: AuditRetentionTask | None = None
        self._scheduler_task: ScheduleDispatcherTask | None = None
        self._anomaly_task: AnomalyDetectorTask | None = None
        self._prepull_task: asyncio.Task[None] | None = None
        self._grpc_server: Any = None

    async def initialize(self, config: dict[str, Any]) -> None:
        await super().initialize(config)
        ra_config = RedAgentConfig()

        dsn = _resolve_dsn(self.get_config("postgres_dsn", ""))
        if dsn:
            schema_ok = await ensure_schema(dsn)
            if not schema_ok:
                logger.warning("red_agent.schema.unavailable_running_in_degraded_mode")
        else:
            logger.warning("red_agent.dsn.missing_running_in_memory_mode")

        policy_store = PolicyStore(dsn=dsn)
        ServiceRegistry.register(PolicyStore, policy_store)
        if policy_store.available:
            try:
                overrides = await policy_store.load()
                if overrides:
                    apply_overrides(ra_config, overrides)
                    logger.info(
                        "red_agent.policy.overrides_applied",
                        extra={"keys": sorted(overrides.keys())},
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("red_agent.policy.load_failed", extra={"err": str(e)})

        ServiceRegistry.register(RedAgentConfig, ra_config)

        persistence = RedAgentPersistence(dsn=dsn)
        ServiceRegistry.register(RedAgentPersistence, persistence)

        try:
            reconciled = await persistence.reconcile_orphaned_scans()
            if reconciled:
                logger.warning(
                    "red_agent.scans.orphans_reconciled",
                    extra={"count": reconciled},
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.scans.orphan_reconcile_failed", extra={"err": str(e)}
            )

        fingerprints = FingerprintStore(dsn=dsn)
        ServiceRegistry.register(FingerprintStore, fingerprints)

        engagements = EngagementPersistence(dsn=dsn)
        ServiceRegistry.register(EngagementPersistence, engagements)

        roe_engine = RuleOfEngagementEngine(store=engagements)
        ServiceRegistry.register(RuleOfEngagementEngine, roe_engine)

        targets = TargetPersistence(dsn=dsn)
        ServiceRegistry.register(TargetPersistence, targets)

        # Endpoint-daemon stores: register unconditionally so routers can
        # return 503 cleanly when DSN is missing.
        ServiceRegistry.register(AgentPersistence, AgentPersistence(dsn=dsn))
        ServiceRegistry.register(AgentCertPersistence, AgentCertPersistence(dsn=dsn))
        ServiceRegistry.register(
            EnrollmentTokenPersistence, EnrollmentTokenPersistence(dsn=dsn)
        )
        ServiceRegistry.register(AgentAuditLog, AgentAuditLog(dsn=dsn))
        ServiceRegistry.register(AgentTelemetryStore, AgentTelemetryStore(dsn=dsn))

        self._maybe_register_agent_ca()

        graph_client = self._build_graph_client(ra_config)
        graph = VulnerabilityGraph(client=graph_client, config=ra_config)
        ServiceRegistry.register(VulnerabilityGraph, graph)

        audit = AuditLogger(dsn=dsn)
        ServiceRegistry.register(AuditLogger, audit)

        sandbox: Any = await self._select_sandbox(ra_config)
        ServiceRegistry.register(SandboxRunner, sandbox)

        # Dev convenience: with mock sandbox active, auto-grant scope so
        # arbitrary targets work without populating ``scope_allowlist``.
        from plugins.red_agent.mock_sandbox import MockSandboxRunner as _Mock

        if isinstance(sandbox, _Mock):
            if not ra_config.bug_bounty_mode and not ra_config.scope_allowlist:
                ra_config.bug_bounty_mode = True
                logger.warning(
                    "red_agent.scope.dev_auto_granted",
                    extra={
                        "reason": (
                            "mock sandbox active and scope_allowlist empty; "
                            "bug_bounty_mode forced on for dev so guardrails "
                            "do not reject every target as OUT_OF_SCOPE."
                        ),
                    },
                )
            if not ra_config.allow_internal_targets:
                ra_config.allow_internal_targets = True

        events = ScanEventBus()
        ServiceRegistry.register(ScanEventBus, events)

        activity_bus = ActivityEventBus()
        ServiceRegistry.register(ActivityEventBus, activity_bus)

        engagement_index = ScanEngagementIndex()
        ServiceRegistry.register(ScanEngagementIndex, engagement_index)

        approvals_store = ApprovalPersistence(dsn=dsn) if dsn else None
        approvals = ApprovalRegistry(store=approvals_store)
        ServiceRegistry.register(ApprovalRegistry, approvals)
        if approvals_store is not None:
            try:
                rehydrated = await approvals.rehydrate()
                if rehydrated:
                    logger.info(
                        "red_agent.approvals.rehydrated_on_boot",
                        extra={"count": rehydrated},
                    )
            except Exception:  # noqa: BLE001
                logger.warning("approval rehydrate at boot failed")

        (
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
        ) = register_ml_services(ra_config)

        webhook = WebhookNotifier(
            enabled=ra_config.webhook_enabled,
            url=ra_config.webhook_url,
            secret=(
                ra_config.webhook_secret.get_secret_value()
                if ra_config.webhook_secret is not None
                else None
            ),
            min_severity=_severity_from_str(ra_config.webhook_min_severity),
            request_timeout_seconds=ra_config.webhook_request_timeout_seconds,
            max_concurrent_requests=ra_config.webhook_max_concurrent_requests,
            retry_count=ra_config.webhook_retry_count,
            replay_protection=ra_config.webhook_replay_protection,
        )
        ServiceRegistry.register(WebhookNotifier, webhook)

        webhook_receiver = WebhookReceiver(
            enabled=ra_config.webhook_in_enabled,
            secret=(
                ra_config.webhook_in_secret.get_secret_value()
                if ra_config.webhook_in_secret is not None
                else None
            ),
            require_signature=ra_config.webhook_in_require_signature,
            replay_protection=ra_config.webhook_replay_protection,
            replay_window_seconds=ra_config.webhook_replay_window_seconds,
            nonce_cache_size=ra_config.webhook_replay_nonce_cache_size,
        )
        ServiceRegistry.register(WebhookReceiver, webhook_receiver)

        autopr = AutoRemediationService(
            enabled=ra_config.auto_remediation_enabled,
            github_token=(
                ra_config.auto_remediation_github_token.get_secret_value()
                if ra_config.auto_remediation_github_token is not None
                else None
            ),
            request_timeout_seconds=(
                ra_config.auto_remediation_request_timeout_seconds
            ),
        )
        ServiceRegistry.register(AutoRemediationService, autopr)

        self._agent = RedAgent(
            config=ra_config,
            persistence=persistence,
            graph=graph,
            audit=audit,
            sandbox=sandbox,
            events=events,
            approvals=approvals,
            triage=triage,
            dedup=dedup,
            fp_classifier=fp_classifier,
            epss_kev=epss_kev,
            attack_mapper=attack_mapper,
            vex=vex,
            reachability=reachability,
            risk_scorer=risk_scorer,
            compliance=compliance,
            fingerprints=fingerprints,
            osv=osv,
            greynoise=greynoise,
            webhook=webhook,
            roe=roe_engine,
        )
        ServiceRegistry.register(RedAgent, self._agent)
        self._anomaly_task = maybe_start_anomaly_task(
            config=ra_config,
            detector=anomaly_detector,
            audit=audit,
            events=events,
        )

        if dsn:
            self._retention_task = AuditRetentionTask(dsn=dsn, config=ra_config)
            self._retention_task.start()
            self._scheduler_task = ScheduleDispatcherTask(
                agent=self._agent, targets=targets
            )
            self._scheduler_task.start()

        await self._maybe_start_grpc_server()

        logger.info("red_agent.plugin.initialized")

    async def shutdown(self) -> None:
        if self._grpc_server is not None:
            await self._grpc_server.stop()
            self._grpc_server = None
        if self._anomaly_task is not None:
            await self._anomaly_task.stop()
        if self._scheduler_task is not None:
            await self._scheduler_task.stop()
        if self._retention_task is not None:
            await self._retention_task.stop()
        if self._prepull_task is not None and not self._prepull_task.done():
            self._prepull_task.cancel()
            await asyncio.gather(self._prepull_task, return_exceptions=True)
        if self._agent is not None and self._agent.epss_kev is not None:
            try:
                await self._agent.epss_kev.aclose()
            except Exception:  # noqa: BLE001
                pass
        if self._agent is not None and self._agent.osv is not None:
            try:
                await self._agent.osv.aclose()
            except Exception:  # noqa: BLE001
                pass
        if self._agent is not None and self._agent.greynoise is not None:
            try:
                await self._agent.greynoise.aclose()
            except Exception:  # noqa: BLE001
                pass
        if self._agent is not None and self._agent.webhook is not None:
            try:
                await self._agent.webhook.aclose()
            except Exception:  # noqa: BLE001
                pass
        autopr = ServiceRegistry.get(AutoRemediationService)
        if autopr is not None:
            try:
                await autopr.aclose()
            except Exception:  # noqa: BLE001
                pass
        from plugins.red_agent.persistence._conn import close_pools

        await close_pools()
        await super().shutdown()

    async def _maybe_start_grpc_server(self) -> None:
        from plugins.red_agent._plugin_lifecycle import maybe_start_grpc_server

        self._grpc_server = await maybe_start_grpc_server()

    def get_router_prefix(self) -> str:
        return "/red-agent"

    def get_routers(self) -> list[Any]:
        """Routers to be mounted by the API gateway."""
        return [
            targets_router,
            engagements_router,
            # approve_router must come before scan_router: both share prefix
            # `/scans`. scan_router has `GET /scans/{scan_id}` (UUID), which
            # would otherwise shadow `GET /scans/pending-approvals` and yield
            # a 422 when "pending-approvals" fails UUID parsing.
            approve_router,
            scan_router,
            file_scan_router,
            findings_router,
            triage_router,
            graph_router,
            graph_chat_router,
            ws_router,
            reports_router,
            preflight_router,
            settings_router,
            agents_router,
            health_router,
            webhooks_router,
            autopr_router,
            playbooks_router,
            activity_router,
        ]

    def create_agent(self, service: Any, **kwargs: Any) -> RedAgent:
        del service, kwargs
        if self._agent is None:
            raise RuntimeError("Red Agent plugin not initialized")
        return self._agent

    async def _select_sandbox(self, config: RedAgentConfig) -> Any:
        from plugins.red_agent._plugin_sandbox import select_sandbox

        return await select_sandbox(
            config,
            on_prepull_task=lambda task: setattr(self, "_prepull_task", task),
        )

    def get_intent_patterns(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "security_scan",
                "patterns": ["scan", "pentest", "vuln", "audit security"],
                "priority": 100,
            }
        ]

    @staticmethod
    def _maybe_register_agent_ca() -> None:
        from plugins.red_agent._plugin_lifecycle import maybe_register_agent_ca

        maybe_register_agent_ca()

    @staticmethod
    def _build_graph_client(config: RedAgentConfig) -> Any:
        from plugins.red_agent._plugin_lifecycle import build_graph_client

        return build_graph_client(config)
