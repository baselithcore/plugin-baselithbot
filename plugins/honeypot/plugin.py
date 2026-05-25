"""Honeypot Plugin.

Main plugin entry point implementing AgentPlugin and RouterPlugin.
Fully integrated with core framework: EventBus, Memory, Swarm, Learning.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter

from core.plugins import AgentPlugin, PluginMetadata, RouterPlugin
from core.observability.logging import get_logger

from .config import HoneypotConfig, get_honeypot_config, update_honeypot_config
from .router import create_router
from .geo import GeoIPService
from .notifications.manager import NotificationManager

logger = get_logger(__name__)


class HoneypotPlugin(AgentPlugin, RouterPlugin):
    """Honeypot Plugin - AI-powered honeypot for attack detection.

    Provides SSH and HTTP honeypot services with LLM-powered responses
    for realistic attacker engagement. Integrates with CVE Hunter
    for attack-to-vulnerability correlation.

    Framework Integrations:
    - EventBus: Cross-plugin communication with CVE Hunter
    - AgentMemory: Persistent attack patterns and IP reputation
    - Colony: Swarm-based agent orchestration
    - PheromoneSystem: Attack hotspot signaling
    - LLMService: Realistic response generation
    - Learning: Feedback-driven improvement
    """

    def __init__(self):
        """Initialize Honeypot plugin."""
        super().__init__()
        self.config: HoneypotConfig = get_honeypot_config()
        self.geo_locator = GeoIPService()
        self.notification_manager = NotificationManager()
        self._tasks: List[asyncio.Task] = []
        self._coordinator = None
        self._learning = None
        self._cve_service = None  # CVE lookup service
        self._initialized = False

    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="honeypot",
            version="1.0.0",  # Phase 2: Enhanced metadata
            description="AI-powered honeypot for attack detection and CVE correlation",
            author="White-Label Team",
            # Legacy dependencies (Phase 1)
            dependencies=[],  # cve_hunter is optional
            # Phase 2: Enhanced dependency management
            python_dependencies=[
                "asyncssh>=2.13.0",  # SSH honeypot
                "aiohttp>=3.8.0",  # HTTP client for callbacks
                "PyYAML>=6.0",  # YAML support for profiles
            ],
            plugin_dependencies={
                # Optional: CVE Hunter for vulnerability correlation
                # If present, must be compatible with 1.x
                # "cve_hunter": "^1.0.0",
            },
            # Core version compatibility
            min_core_version="2.0.0",
            max_core_version="3.0.0",
            # Resources (Phase 1)
            required_resources=[
                "postgres",
                "memory",
            ],  # Postgres for persistence, Memory for attack patterns
            optional_resources=[
                "llm",
                "graph",
            ],  # LLM for AI responses, Graph for CVE correlation
            # Additional metadata (Phase 2)
            homepage="https://github.com/your-org/multi-agent-system",
            license="MIT",
            tags=["security", "honeypot", "threat-intelligence", "ai"],
        )

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin.

        Args:
            config: Plugin configuration from plugins.yaml
        """
        # Update the global singleton with YAML config values.
        # This ensures all code using get_honeypot_config() sees these values.
        self.config = update_honeypot_config(config)

        self._initialized = True
        logger.info(
            f"Plugin '{self.metadata.name}' v{self.metadata.version} initialized"
        )

        # Initialize Persistence Layer (Database & Schema)
        from .persistence import HoneypotDAO

        try:
            await HoneypotDAO.ensure_schema()
            logger.info("   💾 Persistence: Connected (Schema Validated)")

            # Run database optimizations for scale
            await HoneypotDAO.optimize_for_scale()
            logger.info("   ⚡ Database: Optimized for scale (indexes, archiving)")
        except Exception as e:
            logger.warning(f"   ⚠️ Persistence: Initialization failed: {e}")

        # Initialize Notification Manager
        try:
            self.notification_manager.initialize()
            logger.info("   🔔 Notifications: Initialized")
        except Exception as e:
            logger.warning(f"   ⚠️ Notifications: Initialization failed: {e}")

        # Use swarm coordinator for full integration
        from .swarm.coordinator import HoneypotSwarmCoordinator

        # Create and start swarm coordinator
        self._coordinator = HoneypotSwarmCoordinator(config=self.config)

        # Register coordinator in DI ServiceRegistry
        from core.di import ServiceRegistry

        ServiceRegistry.register(HoneypotSwarmCoordinator, self._coordinator)
        logger.info("   🔌 Coordinator: Registered in ServiceRegistry")

        # Set tenant context for background tasks
        from core.context import set_tenant_context

        default_tenant = self.config.default_tenant_id or "default"
        set_tenant_context(default_tenant)
        logger.info(f"   🏢 Tenant Context: Set to '{default_tenant}'")

        await self._coordinator.start()

        # Initialize learning system
        from .learning import HoneypotLearning

        self._learning = HoneypotLearning(config=self.config)
        await self._learning.initialize()

        # Initialize CVE Service for dynamic vulnerability intelligence
        if self.config.enable_dynamic_cve_lookup:
            try:
                from .services.cve_service import CVEService

                # Get Redis client for caching (if available)
                redis_client = None
                try:
                    from core.cache import get_redis_client

                    redis_client = await get_redis_client()
                except Exception:
                    pass  # Redis optional, uses in-memory fallback

                self._cve_service = CVEService(
                    config=self.config, redis_client=redis_client
                )

                # Inject into correlator
                if hasattr(self._coordinator, "_cve_correlator"):
                    self._coordinator._cve_correlator.set_cve_service(self._cve_service)

                logger.info("   🔍 CVE Service: Initialized (NVD API ready)")
            except Exception as e:
                logger.warning(f"   ⚠️ CVE Service: Initialization failed: {e}")
                logger.warning("      Correlator will use static patterns only")

        self._initialized = True
        logger.info("✅ Honeypot plugin initialized (Full Framework Integration)")
        logger.info("   🔗 EventBus: Connected")
        logger.info(
            "   🧠 Memory: Enabled"
            if self.config.enable_memory
            else "   🧠 Memory: Disabled"
        )
        logger.info("   🐝 Swarm Colony: Active")
        if self.config.enable_ssh_honeypot:
            logger.info(f"   📡 SSH Honeypot: port {self.config.ssh_port}")
        if self.config.enable_http_honeypot:
            logger.info(f"   🌐 HTTP Honeypot: port {self.config.http_port}")

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info("👋 Honeypot plugin shutting down...")

        if self._coordinator:
            await self._coordinator.stop()

        if self.notification_manager:
            self.notification_manager.stop()

        # Shutdown event batcher (flush pending events before DB close)
        from .persistence import shutdown_batcher

        await shutdown_batcher()

        # Shutdown analytics DB connection
        from .persistence import HoneypotDAO

        await HoneypotDAO.close_pool()

        self._initialized = False
        await super().shutdown()

    def create_agent(self, service: Any, **kwargs):
        """Create Honeypot agent (returns the coordinator).

        Args:
            service: Service dependency

        Returns:
            HoneypotSwarmCoordinator instance
        """
        return self._coordinator

    def create_router(self) -> APIRouter:
        """Create API router for Honeypot.

        Returns:
            FastAPI APIRouter
        """
        return create_router()

    def get_learning(self):
        """Get learning system instance."""
        return self._learning

    def get_intent_patterns(self) -> List[Dict[str, Any]]:
        """Register intent patterns for honeypot queries."""
        return [
            {
                "name": "honeypot_status",
                "patterns": [
                    "honeypot",
                    "attack",
                    "attacker",
                    "intrusion",
                    "threat",
                ],
                "handler": "handle_honeypot_query",
                "priority": 50,
            },
            {
                "name": "honeypot_correlation",
                "patterns": [
                    "correlate attack",
                    "cve match",
                    "vulnerability mapping",
                ],
                "handler": "handle_correlation_query",
                "priority": 60,
            },
        ]

    def get_static_assets_path(self) -> Path:
        """Return the absolute path to static assets."""
        return Path(__file__).parent / "static"

    def get_scripts(self) -> List[str]:
        """Return list of scripts to inject."""
        return ["honeypot_dashboard.js"]

    def get_stylesheets(self) -> List[str]:
        """Return list of stylesheets to inject."""
        return ["honeypot_styles.css"]

    def get_ui_tabs(self) -> List[Dict[str, str]]:
        """Return list of UI tabs exposed by Honeypot plugin."""
        return [
            {"id": "monitor", "label": "Monitor"},
            {"id": "globe", "label": "Globe"},
            {"id": "analytics", "label": "Analytics"},
            {"id": "threats", "label": "Threats"},
            {"id": "pentest", "label": "Pentest"},
            {"id": "discovery", "label": "Discovery"},
            {"id": "reports", "label": "Reports"},
        ]

    @property
    def is_ready(self) -> bool:
        """Check if plugin is ready."""
        return self._initialized and self._coordinator is not None
