"""CVE Hunter Plugin.

Main plugin entry point implementing AgentPlugin and RouterPlugin.
"""

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter

from core.plugins import AgentPlugin, PluginMetadata, RouterPlugin
from core.observability.logging import get_logger
from core.di import ServiceRegistry
from core.context import set_tenant_context

from .config import CVEHunterConfig, get_cve_hunter_config, update_cve_hunter_config
from .router import create_router
from .swarm import CVEHunterSwarm

logger = get_logger(__name__)


class CVEHunterPlugin(AgentPlugin, RouterPlugin):
    """CVE Hunter Plugin - Autonomous CVE scanning and discovery.

    Provides a swarm of AI agents that scan CVE databases,
    analyze vulnerabilities, and detect potential zero-days.
    """

    def __init__(self):
        """Initialize CVE Hunter plugin."""
        super().__init__()
        self._cve_config: CVEHunterConfig = get_cve_hunter_config()
        self._swarm: CVEHunterSwarm | None = None

    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata from manifest."""
        return super().metadata

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin.

        Args:
            config: Plugin configuration from plugins.yaml
        """
        await super().initialize(config)

        # Merge YAML/dict overrides on top of env-var defaults so that
        # values from the environment are never silently discarded.
        try:
            self._cve_config = update_cve_hunter_config(config)
        except Exception as e:
            logger.warning(
                "Failed to apply plugin config overrides; falling back to defaults",
                extra={"error": str(e)},
            )
            self._cve_config = get_cve_hunter_config()

        # Initialize tenant context if multi-tenancy is configured
        if self._cve_config.tenant_id:
            set_tenant_context(self._cve_config.tenant_id)
            logger.info(
                "Tenant context initialized",
                extra={
                    "tenant_id": self._cve_config.tenant_id,
                    "isolation_mode": self._cve_config.isolation_mode,
                    "namespace": self._cve_config.namespace,
                },
            )

        # Create and start swarm
        self._swarm = CVEHunterSwarm(config=self._cve_config)

        # Register swarm in DI container for dependency injection
        ServiceRegistry.register(CVEHunterSwarm, self._swarm)

        await self._swarm.start()

        logger.info("CVE Hunter plugin initialized — swarm active")

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info("👋 CVE Hunter plugin shutting down...")

        if self._swarm:
            await self._swarm.stop()

        self._initialized = False
        await super().shutdown()

    def create_agent(self, service: Any, **kwargs) -> CVEHunterSwarm:
        """Create CVE Hunter agent (returns the swarm coordinator).

        Args:
            service: Service dependency

        Returns:
            CVEHunterSwarm instance
        """
        if self._swarm is None:
            self._swarm = CVEHunterSwarm(config=self._cve_config)
        return self._swarm

    def create_router(self) -> APIRouter:
        """Create API router for CVE Hunter.

        Returns:
            FastAPI APIRouter
        """
        return create_router()

    def get_intent_patterns(self) -> List[Dict[str, Any]]:
        """Register intent patterns for CVE queries."""
        return [
            {
                "name": "cve_query",
                "patterns": [
                    "cve",
                    "vulnerability",
                    "vulnerabilities",
                    "security advisory",
                    "exploit",
                    "patch",
                ],
                "handler": "handle_cve_query",
                "priority": 50,
            },
            {
                "name": "cve_scan",
                "patterns": [
                    "scan for cve",
                    "cve scan",
                    "vulnerability scan",
                    "security scan",
                ],
                "handler": "handle_cve_scan",
                "priority": 60,
            },
        ]

    def get_static_assets_path(self) -> Path:
        """Return the absolute path to static assets."""
        return Path(__file__).parent / "static"

    def get_scripts(self) -> List[str]:
        """JS files to inject into the frontend dashboard.

        Returns:
            List of filenames relative to the static assets directory.
        """
        return ["cve_hunter_dashboard.js"]

    def get_stylesheets(self) -> List[str]:
        """CSS files to inject into the frontend dashboard.

        Returns:
            List of filenames relative to the static assets directory.
        """
        return ["cve_hunter_styles.css"]

    def get_ui_tabs(self) -> List[Dict[str, str]]:
        """Return UI tabs for the dashboard."""
        return [
            {"id": "feed", "label": "Vulnerability Feed"},
            {"id": "monitor", "label": "System Monitor"},
            {"id": "discovery", "label": "Zero-Day Discovery"},
            {"id": "analytics", "label": "Threat Analytics"},
        ]

    @property
    def is_ready(self) -> bool:
        """Check if plugin is ready."""
        return self._initialized and self._swarm is not None
