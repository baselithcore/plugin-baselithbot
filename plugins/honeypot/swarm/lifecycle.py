"""Lifecycle management mixin for HoneypotSwarmCoordinator.

Handles start/stop coordination, integrations initialization,
agent registration, and honeypot definition loading.
"""

import asyncio
from core.observability.logging import get_logger
from typing import TYPE_CHECKING

from ..engine.ssh_handler import ASYNCSSH_AVAILABLE

if TYPE_CHECKING:
    from .coordinator import HoneypotSwarmCoordinator

logger = get_logger(__name__)


class LifecycleMixin:
    """Mixin providing lifecycle management capabilities."""

    async def start(self: "HoneypotSwarmCoordinator") -> None:
        """Start the honeypot swarm coordinator."""
        if self._is_running:
            return

        logger.info("Starting Honeypot Swarm Coordinator...")
        self._is_running = True

        # Initialize core integrations
        await self._initialize_integrations()

        # Register agents with colony
        await self._register_agents()

        # Emit service started event
        await self._emit_service_event("started")

        logger.info("Honeypot Swarm Coordinator started")

    async def _initialize_integrations(self: "HoneypotSwarmCoordinator") -> None:
        """Initialize framework integrations."""
        from ..engine.http_handler import HTTPHandler
        from ..engine.ssh_handler import SSHHandler
        from ..events import HoneypotEventHandler, get_event_bus
        from ..memory import initialize_memory
        from ..persistence import HoneypotDAO

        # --- Batch 1: Parallel Initialization of Independent Components ---

        async def init_memory_task():
            if self.config.enable_memory and self._memory is None:
                try:
                    self._memory = await initialize_memory()
                    logger.info("Honeypot memory initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize memory: {e}")

        async def init_dao_task():
            try:
                await HoneypotDAO.ensure_schema()
                logger.info("Analytics database schema initialized")

                # Hydrate in-memory data from DB for persistence across restarts
                from ..utils import normalize_ip_display
                from ..models import AttackSeverity, DiscoveryLog
                from datetime import datetime, timezone

                try:
                    recent_events = await HoneypotDAO.get_recent_events(limit=5000)
                    for event in recent_events:
                        self._events.append(event)
                        # Track seen IPs
                        self._seen_ips.add(event.source_ip)

                    if recent_events:
                        logger.info(f"Hydrated {len(recent_events)} events from DB")

                        # Generate discovery logs from hydrated events
                        logger.info(
                            f"Hydrating discovery logs from {len(self._events)} events"
                        )
                        try:
                            for event in self._events:
                                if len(self._discovery_logs) >= 500:
                                    break

                                display_ip = normalize_ip_display(event.source_ip)
                                msg = f"[{event.protocol.value.upper()}] Attack from {display_ip}: {event.category.value} ({event.severity.value})"
                                is_alert = event.severity in (
                                    AttackSeverity.HIGH,
                                    AttackSeverity.CRITICAL,
                                )

                                log = DiscoveryLog(
                                    message=msg,
                                    timestamp=event.timestamp
                                    or datetime.now(timezone.utc),
                                    is_alert=is_alert,
                                    is_error=False,
                                    severity=event.severity.value,
                                    agent_type="system",
                                )
                                self._discovery_logs.append(log)
                            logger.info(
                                f"Successfully hydrated {len(self._discovery_logs)} discovery logs"
                            )
                        except Exception as e:
                            logger.error(f"Error during discovery log hydration: {e}")

                    # Hydrate sessions (exclude stale zombies > 1 hour)
                    recent_sessions, _ = await HoneypotDAO.get_sessions(page_size=500)
                    now_utc = datetime.now(timezone.utc)

                    for session in recent_sessions:
                        # Skip stale "active" sessions (zombies)
                        if session.ended_at is None:
                            # Normalize timestamps
                            start_time = session.started_at
                            if start_time and start_time.tzinfo is None:
                                start_time = start_time.replace(tzinfo=timezone.utc)

                            if (now_utc - start_time).total_seconds() > 3600:
                                continue

                        self._sessions[session.session_id] = session

                    if recent_sessions:
                        logger.info(f"Hydrated {len(recent_sessions)} sessions from DB")

                except Exception as hydrate_err:
                    logger.warning(f"Failed to hydrate data from DB: {hydrate_err}")

            except Exception as e:
                logger.error(f"Failed to initialize analytics schema: {e}")

        async def init_captor_task():
            await self._captor_manager.initialize()
            # Load classification rules from config (HoneyDOC Sensibility)
            if self.config.enable_sensibility and self.config.classification_rules:
                self._captor_manager.classifier.load_rules_from_config(
                    self.config.classification_rules
                )
                logger.info(
                    f"Loaded {len(self.config.classification_rules)} "
                    "HoneyDOC classification rules"
                )
            logger.info("CaptorManager initialized")

        # Execute parallel tasks
        await asyncio.gather(
            init_memory_task(),
            init_dao_task(),
            self._llm_responder.initialize(),
            self._pattern_analyzer.initialize(),
            init_captor_task(),
        )

        # --- Batch 2: Sequential/Dependent Initialization ---

        # Initialize EventBus (Synchronous setup)
        if self.config.enable_event_bus:
            self._event_bus = get_event_bus()
            if self._event_bus:
                self._event_handler = HoneypotEventHandler(self._event_bus)
                self._event_handler.subscribe()
                logger.info("EventBus integration initialized")

        # CVE Correlator (Depends on Memory)
        if self._memory:
            self._cve_correlator.set_memory(self._memory)
        await self._cve_correlator.initialize()

        # Load YAML-based honeypot definitions
        await self._load_honeypot_definitions()

        # Start Network Listeners (legacy handlers from config)
        if self.config.enable_http_honeypot:
            self._http_handler = HTTPHandler(self.config)
            self._http_handler.set_event_callback(
                lambda event: self._process_attack_with_honeypot(event, "legacy-http")
            )
            # HoneyDOC: set flow check callback
            self._http_handler.set_flow_check_callback(self._check_flow_allowed)
            try:
                await self._http_handler.start()
                logger.info(f"HTTP honeypot started on port {self.config.http_port}")
            except Exception as e:
                logger.error(f"Failed to start HTTP honeypot: {e}")

        if self.config.enable_ssh_honeypot:
            if ASYNCSSH_AVAILABLE:
                self._ssh_handler = SSHHandler(self.config)
                self._ssh_handler.set_event_callback(
                    lambda event: self._process_attack_with_honeypot(
                        event, "legacy-ssh"
                    )
                )
                # HoneyDOC: set flow check callback
                self._ssh_handler.set_flow_check_callback(self._check_flow_allowed)
                try:
                    await self._ssh_handler.start()
                    logger.info(f"SSH honeypot started on port {self.config.ssh_port}")
                except Exception as e:
                    logger.error(f"Failed to start SSH honeypot: {e}")
            else:
                logger.warning("SSH honeypot disabled: asyncssh not installed")

    async def _load_honeypot_definitions(self: "HoneypotSwarmCoordinator") -> None:
        """Load honeypot definitions from YAML files."""
        from ..honeypot_loader import HoneypotRegistry, initialize_registry
        from ..models import HoneypotStats

        try:
            self._registry = await initialize_registry()

            # Check for config overrides
            for definition in self._registry.list_all():
                # Enforce allowlist if configured
                if self.config.enforce_active_honeypots_only:
                    if definition.id not in self.config.active_honeypots:
                        definition.enabled = False
                        logger.debug(
                            f"Honeypot '{definition.id}' disabled by strictly enforced allowlist"
                        )

                # Apply overrides
                if definition.id in self.config.active_honeypots:
                    override = self.config.active_honeypots[definition.id]
                    if "enabled" in override:
                        definition.enabled = override["enabled"]
                        logger.info(
                            f"Honeypot '{definition.id}' enabled status "
                            f"overridden to {definition.enabled} by config"
                        )

            loaded = self._registry.count
            enabled = self._registry.enabled_count

            if loaded > 0:
                logger.info(
                    f"Loaded {loaded} honeypot definitions "
                    f"({enabled} enabled) from YAML"
                )
                summary = self._registry.get_summary()
                for proto, count in summary.items():
                    logger.debug(f"  - {proto}: {count} honeypot(s)")

                # Initialize per-honeypot stats
                for definition in self._registry.list_all():
                    self._honeypot_stats[definition.id] = HoneypotStats()
            else:
                logger.info("No YAML honeypot definitions found, using legacy config")

            # Log any loading errors
            for filename, error in self._registry.load_errors.items():
                logger.warning(f"Failed to load {filename}: {error}")

            # Start listeners for loaded honeypots
            await self._start_dynamic_listeners()

        except Exception as e:
            logger.error(f"Failed to load honeypot definitions: {e}")
            self._registry = HoneypotRegistry()

    async def _register_agents(self: "HoneypotSwarmCoordinator") -> None:
        """Register honeypot agents with the colony."""
        from core.swarm.types import AgentProfile, AgentStatus, Capability

        from ..models import HoneypotAgentStatus, HoneypotProtocol

        agents = [
            ("ssh-handler", "ssh", ["ssh", "capture", "response", "shell"]),
            ("http-handler", "http", ["http", "capture", "web", "forms"]),
            ("pattern-analyzer", "analyzer", ["analysis", "pattern", "ml", "llm"]),
            ("cve-correlator", "correlator", ["correlation", "cve", "mapping"]),
        ]

        for agent_id, agent_type, cap_names in agents:
            capabilities = [Capability(name=cap) for cap in cap_names]

            profile = AgentProfile(
                id=agent_id,
                name=f"Honeypot {agent_type.title()}",
                capabilities=capabilities,
                status=AgentStatus.IDLE,
            )
            self._agent_profiles[agent_id] = profile
            self._colony.register_agent(profile)

            self._agent_statuses[agent_id] = HoneypotAgentStatus(
                agent_id=agent_id,
                protocol=(
                    HoneypotProtocol.SSH
                    if agent_type == "ssh"
                    else HoneypotProtocol.HTTP
                    if agent_type == "http"
                    else HoneypotProtocol.SSH
                ),
            )

        logger.info(f"Registered {len(agents)} agents with colony")

    async def stop(self: "HoneypotSwarmCoordinator") -> None:
        """Stop the honeypot swarm coordinator."""
        import asyncio

        if not self._is_running:
            return

        logger.info("Stopping Honeypot Swarm Coordinator...")
        self._is_running = False

        # Unsubscribe from events
        if self._event_handler:
            self._event_handler.unsubscribe()

        # Unregister agents from colony
        for agent_id in self._agent_profiles:
            self._colony.unregister_agent(agent_id)

        # Emit service stopped event
        await self._emit_service_event("stopped")

        # Stop network handlers in parallel
        stop_tasks = []

        # Legacy handlers
        if self._http_handler:
            stop_tasks.append(self._http_handler.stop())
        if self._ssh_handler:
            stop_tasks.append(self._ssh_handler.stop())

        # Dynamic handlers
        for handler in self._handlers_by_honeypot.values():
            stop_tasks.append(handler.stop())

        if stop_tasks:
            try:
                # Add 5 second timeout for graceful shutdown
                await asyncio.wait_for(
                    asyncio.gather(*stop_tasks, return_exceptions=True), timeout=5.0
                )
                logger.info(f"Stopped {len(stop_tasks)} honeypot handlers")
            except asyncio.TimeoutError:
                logger.warning(f"Shutdown timed out for {len(stop_tasks)} handlers")
            except Exception as e:
                logger.error(f"Error during handler shutdown: {e}")

        # Clear internal state
        self._handlers_by_honeypot.clear()

        logger.info("Honeypot Swarm Coordinator stopped")

    async def _emit_service_event(
        self: "HoneypotSwarmCoordinator", status: str
    ) -> None:
        """Emit service lifecycle event."""
        from ..events import HoneypotEvents, ServiceEventData, emit_honeypot_event

        await emit_honeypot_event(
            HoneypotEvents.SERVICE_STARTED
            if status == "started"
            else HoneypotEvents.SERVICE_STOPPED,
            ServiceEventData(
                service_name="honeypot-coordinator",
                protocol="multi",
                port=0,
                status=status,
            ).to_dict(),
        )
