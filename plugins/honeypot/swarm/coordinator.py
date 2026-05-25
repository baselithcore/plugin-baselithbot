"""Honeypot Swarm Coordinator.

Coordinates honeypot agents using core.swarm.Colony for
auction-based task allocation and pheromone signaling.

This module implements the HoneyDOC Orchestrator role, coordinating:
- Decoy (handlers): Honeypot infrastructure (LIH/MIH/HIH)
- Captor (captor module): Data capture, control, and analysis

The Orchestrator consists of (per HoneyDOC Section III-C):
- DecoyManager: Manages honeypot handlers and registry
- CaptorManager: Integrates captor module components

Mixin modules for modularity:
- lifecycle: start/stop, integrations, agent registration
- handlers: custom handler loading, dynamic listeners
- attack_processor: event processing, session tracking
- response_generator: LLM-powered responses
- stats: statistics, queries, honeypot registry
"""

from core.observability.logging import get_logger
from collections import deque
from typing import Dict, List, Optional

from core.swarm import Colony, PheromoneSystem
from core.swarm.types import AgentProfile

from ..agents import HoneypotCVECorrelator, LLMResponder, PatternAnalyzer
from ..captor import CaptorManager
from ..config import HoneypotConfig, get_honeypot_config
from ..engine.base import BaseHandler
from ..engine.http_handler import HTTPHandler
from ..engine.ssh_handler import SSHHandler
from ..events import HoneypotEventHandler
from ..honeypot_loader import HoneypotRegistry
from ..memory import HoneypotMemory
from ..models import (
    DiscoveryLog,
    HoneypotAgentStatus,
    HoneypotSession,
    HoneypotStats,
)
from .attack_processor import AttackProcessorMixin
from .handlers import HandlerMixin
from .lifecycle import LifecycleMixin
from .response_generator import ResponseGeneratorMixin
from .stats import StatsMixin

logger = get_logger(__name__)


# Pheromone types for swarm signaling
class PheromoneTypes:
    """Pheromone signal types for honeypot swarm."""

    ATTACK_HOTSPOT = "honeypot.attack_hotspot"  # High activity from IP
    PATTERN_FOUND = "honeypot.pattern_found"  # New attack pattern
    CVE_MATCH = "honeypot.cve_match"  # Successful CVE correlation
    DECEPTION_SUCCESS = "honeypot.deception_success"  # Attacker engaged


class HoneypotSwarmCoordinator(
    LifecycleMixin,
    HandlerMixin,
    AttackProcessorMixin,
    ResponseGeneratorMixin,
    StatsMixin,
):
    """Swarm coordinator for honeypot agents.

    Manages honeypot agents using auction-based task allocation
    and pheromone coordination.

    This class uses mixin composition for modularity:
    - LifecycleMixin: start(), stop(), initialization
    - HandlerMixin: handler loading and management
    - AttackProcessorMixin: attack event processing
    - ResponseGeneratorMixin: LLM response generation
    - StatsMixin: statistics and query methods

    HoneyDOC Architecture:
    - Orchestrator role with DecoyManager and CaptorManager
    - CaptorManager integrates data capture, control, and analysis
    """

    def __init__(
        self,
        config: Optional[HoneypotConfig] = None,
        colony: Optional[Colony] = None,
        pheromones: Optional[PheromoneSystem] = None,
        memory: Optional[HoneypotMemory] = None,
    ):
        """Initialize swarm coordinator.

        Args:
            config: Honeypot configuration
            colony: Optional Colony instance
            pheromones: Optional PheromoneSystem
            memory: Optional HoneypotMemory
        """
        self.config = config or get_honeypot_config()

        # Core swarm components
        self._colony = colony or Colony()
        self._pheromones = pheromones or PheromoneSystem()

        # Memory and event handling
        self._memory = memory
        self._event_handler: Optional[HoneypotEventHandler] = None
        self._event_bus = None

        # HoneyDOC CaptorManager - integrates all captor components
        self._captor_manager = CaptorManager(config=self.config)

        # Specialized agents (legacy - now coordinated via CaptorManager)
        self._llm_responder = LLMResponder(config=self.config)
        self._pattern_analyzer = PatternAnalyzer(config=self.config)
        self._cve_correlator = HoneypotCVECorrelator(config=self.config)

        # State tracking
        self._is_running = False
        self._agent_profiles: Dict[str, AgentProfile] = {}
        self._agent_statuses: Dict[str, HoneypotAgentStatus] = {}

        # Event storage
        self._events: deque = deque(
            maxlen=100000
        )  # Increased from 10K for high-volume loads
        self._seen_ips: set = set()
        self._sessions: Dict[str, HoneypotSession] = {}
        self._discovery_logs: List[DiscoveryLog] = []

        # Statistics
        self._stats = HoneypotStats()
        # Per-honeypot stats tracking
        self._honeypot_stats: Dict[str, HoneypotStats] = {}

        # Network Handlers (legacy - for backwards compatibility)
        self._ssh_handler: Optional[SSHHandler] = None
        self._http_handler: Optional[HTTPHandler] = None

        # YAML-based honeypot registry and handlers
        self._registry: Optional[HoneypotRegistry] = None
        self._handlers_by_honeypot: Dict[str, BaseHandler] = {}

    @property
    def captor(self) -> CaptorManager:
        """Get CaptorManager instance for HoneyDOC Captor operations."""
        return self._captor_manager

    def _check_flow_allowed(self, ip: str, session_id: str = "") -> bool:
        """Check if traffic is allowed by Captor Flow Controller.

        Args:
            ip: Source IP
            session_id: Session ID (optional)

        Returns:
            True if traffic is allowed (not blocked/contained).
        """
        # Check IP block
        if self._captor_manager.flow_controller.is_blocked(ip, "ip"):
            return False

        # Check Session block
        if session_id and self._captor_manager.flow_controller.is_blocked(
            session_id, "session"
        ):
            return False

        return True

    async def reset_memory(self) -> None:
        """Reset in-memory state (events, sessions, stats)."""
        # Clear collections
        self._events.clear()
        self._seen_ips.clear()
        self._sessions.clear()
        self._discovery_logs.clear()

        # Reset stats
        self._stats = HoneypotStats()
        self._honeypot_stats.clear()

        logger.info("♻️ Swarm Coordinator memory reset complete")
