"""Captor Manager for Honeypot Plugin.

Implements the HoneyDOC CaptorManager from the Orchestrator module.
Coordinates DataCaptureManager, DataControlManager, and DataAnalysisManager.

Per HoneyDOC Section III-C:
The CaptorManager integrates Captor functionalities to process events and logs.
"""

from core.observability.logging import get_logger
from typing import Any, Dict, Optional

from .classification import TrafficClassifier
from .countermeasures import DynamicDeployer, FlowController
from .data_analysis import DataAnalysisManager
from .data_capture import DataCaptureManager
from .data_control import DataControlManager
from .stealth import StealthManager

logger = get_logger(__name__)


class CaptorManager:
    """Captor Manager per HoneyDOC Orchestrator design.

    Integrates all Captor submodules:
    - DataCaptureManager: Unified data capture
    - DataControlManager: Flow control decisions
    - DataAnalysisManager: Attack analysis coordination
    - TrafficClassifier: Rule-based classification
    - FlowController: Countermeasure execution
    - DynamicDeployer: Runtime honeypot provisioning
    - StealthManager: Stealth-aware operations
    """

    def __init__(self, config: Optional[Any] = None):
        """Initialize CaptorManager.

        Args:
            config: Optional HoneypotConfig
        """
        self.config = config
        self._initialized = False

        # Core captor components
        self._data_capture = DataCaptureManager()
        self._data_control = DataControlManager()
        self._data_analysis = DataAnalysisManager()

        # Extended components
        self._classifier = TrafficClassifier()
        self._flow_controller = FlowController()
        self._dynamic_deployer = DynamicDeployer()
        self._stealth_manager = StealthManager()

        logger.debug("CaptorManager created")

    async def initialize(self) -> bool:
        """Initialize all captor components.

        Returns:
            True if successfully initialized
        """
        if self._initialized:
            return True

        try:
            # Initialize analysis manager (which initializes agents)
            await self._data_analysis.initialize()

            # Load classification rules from config if available
            if self.config and hasattr(self.config, "classification_rules"):
                rules = getattr(self.config, "classification_rules", [])
                if rules:
                    self._classifier.load_rules_from_config(rules)

            self._initialized = True
            logger.info("CaptorManager initialized")
            return True

        except Exception as e:
            logger.error(f"CaptorManager initialization failed: {e}")
            return False

    @property
    def data_capture(self) -> DataCaptureManager:
        """Get DataCaptureManager instance."""
        return self._data_capture

    @property
    def data_control(self) -> DataControlManager:
        """Get DataControlManager instance."""
        return self._data_control

    @property
    def data_analysis(self) -> DataAnalysisManager:
        """Get DataAnalysisManager instance."""
        return self._data_analysis

    @property
    def classifier(self) -> TrafficClassifier:
        """Get TrafficClassifier instance."""
        return self._classifier

    @property
    def flow_controller(self) -> FlowController:
        """Get FlowController instance."""
        return self._flow_controller

    @property
    def dynamic_deployer(self) -> DynamicDeployer:
        """Get DynamicDeployer instance."""
        return self._dynamic_deployer

    @property
    def stealth_manager(self) -> StealthManager:
        """Get StealthManager instance."""
        return self._stealth_manager

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive captor statistics.

        Returns:
            Combined statistics from all components
        """
        return {
            "capture": {
                "total_network_events": self._data_capture.get_capture_stats().total_network_events,
                "total_system_activities": self._data_capture.get_capture_stats().total_system_activities,
            },
            "control": {
                "blocked_count": len(self._data_control.get_blocked_ips()),
                "rules_count": len(self._data_control.get_rules()),
            },
            "analysis": self._data_analysis.get_stats(),
            "classification": {
                "rules_count": len(self._classifier.get_rules()),
                "rule_hits": self._classifier.get_rule_stats(),
            },
            "flow_control": self._flow_controller.get_stats(),
            "deployment": self._dynamic_deployer.get_stats(),
            "stealth": self._stealth_manager.get_stats(),
            "initialized": self._initialized,
        }

    def clear(self) -> None:
        """Clear all captor state."""
        self._data_capture.clear()
        self._data_control.clear()
        self._data_analysis.clear_cache()
        self._classifier.clear()
        self._flow_controller.clear()
        self._dynamic_deployer.clear()
        self._stealth_manager.clear()
        logger.info("CaptorManager cleared")
