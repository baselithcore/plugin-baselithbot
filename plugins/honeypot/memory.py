"""Honeypot Memory Integration.

Provides persistent memory for attack patterns, IP reputation,
and learned response strategies using core.memory.AgentMemory.
"""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = get_logger(__name__)


class HoneypotMemory:
    """Memory manager for Honeypot plugin.

    Stores:
    - Attack patterns in long-term memory
    - Attacker IP reputation
    - Successful deception strategies
    - False positive patterns to avoid
    """

    def __init__(self, agent_memory=None):
        """Initialize honeypot memory.

        Args:
            agent_memory: Optional AgentMemory instance (for DI/testing)
        """
        self._memory = agent_memory
        self._initialized = False

        # In-memory caches (before persistence)
        self._ip_reputation: Dict[str, Dict[str, Any]] = {}
        self._attack_patterns: Dict[str, Dict[str, Any]] = {}
        self._learned_responses: Dict[str, Dict[str, Any]] = {}
        self._cve_correlations: Dict[
            str, Dict[str, Any]
        ] = {}  # Added persistence cache
        self._false_positives: List[str] = []

    async def initialize(self) -> bool:
        """Initialize memory system.

        Returns:
            True if successfully initialized
        """
        if self._initialized:
            return True

        try:
            if self._memory is None:
                from core.memory import get_memory

                self._memory = get_memory()

            # Load persisted data
            await self._load_from_memory()
            self._initialized = True
            logger.info("Honeypot memory initialized")
            return True

        except Exception as e:
            logger.warning(f"Failed to initialize honeypot memory: {e}")
            return False

    async def _load_from_memory(self) -> None:
        """Load persisted data from AgentMemory."""
        if not self._memory:
            return

        try:
            # Load IP reputation
            ip_data = await self._memory.recall(
                query="honeypot_ip_reputation",
                memory_type="long_term",
                limit=100,
            )
            for item in ip_data:
                if "ip" in item.content:
                    self._ip_reputation[item.content["ip"]] = item.content

            # Load attack patterns
            pattern_data = await self._memory.recall(
                query="honeypot_attack_pattern",
                memory_type="long_term",
                limit=500,
            )
            for item in pattern_data:
                if "pattern_id" in item.content:
                    self._attack_patterns[item.content["pattern_id"]] = item.content

            logger.info(
                f"Loaded {len(self._ip_reputation)} IP reputations, "
                f"{len(self._attack_patterns)} attack patterns"
            )

            # Load CVE correlations
            correlation_data = await self._memory.recall(
                query="honeypot_cve_correlation",
                memory_type="long_term",
                limit=100,
            )
            for item in correlation_data:
                if "correlation_id" in item.content:
                    self._cve_correlations[item.content["correlation_id"]] = (
                        item.content
                    )

        except Exception as e:
            logger.warning(f"Error loading from memory: {e}")

    # =========================================================================
    # IP Reputation
    # =========================================================================

    async def update_ip_reputation(
        self,
        ip: str,
        event_count: int = 1,
        severity: str = "info",
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update IP reputation based on attack activity.

        Args:
            ip: Attacker IP address
            event_count: Number of events to add
            severity: Severity of latest attack
            categories: Attack categories observed

        Returns:
            Updated reputation data
        """
        now = datetime.now(timezone.utc)

        if ip not in self._ip_reputation:
            self._ip_reputation[ip] = {
                "ip": ip,
                "first_seen": now.isoformat(),
                "last_seen": now.isoformat(),
                "total_events": 0,
                "severity_counts": {},
                "categories": [],
                "threat_score": 0,
            }

        rep = self._ip_reputation[ip]
        rep["last_seen"] = now.isoformat()
        rep["total_events"] += event_count

        # Update severity counts
        if severity not in rep["severity_counts"]:
            rep["severity_counts"][severity] = 0
        rep["severity_counts"][severity] += event_count

        # Update categories
        if categories:
            for cat in categories:
                if cat not in rep["categories"]:
                    rep["categories"].append(cat)

        # Calculate threat score
        rep["threat_score"] = self._calculate_threat_score(rep)

        # Persist to memory
        await self._store_ip_reputation(ip, rep)

        return rep

    def _calculate_threat_score(self, rep: Dict[str, Any]) -> float:
        """Calculate threat score for an IP.

        Args:
            rep: IP reputation data

        Returns:
            Threat score 0-100
        """
        score = 0.0

        # Weight by severity
        severity_weights = {
            "critical": 25,
            "high": 15,
            "medium": 8,
            "low": 3,
            "info": 1,
        }

        for severity, count in rep.get("severity_counts", {}).items():
            weight = severity_weights.get(severity, 1)
            score += min(count * weight, 50)  # Cap per severity

        # Bonus for variety of attack types
        category_count = len(rep.get("categories", []))
        score += min(category_count * 5, 25)

        return min(score, 100)

    async def _store_ip_reputation(self, ip: str, rep: Dict[str, Any]) -> None:
        """Store IP reputation in memory."""
        if not self._memory:
            return

        try:
            import json
            from core.memory.types import MemoryType

            content = json.dumps(rep)
            await self._memory.add_memory(
                content=content,
                memory_type=MemoryType.LONG_TERM,
                metadata={
                    "type": "honeypot_ip_reputation",
                    "ip": ip,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to store IP reputation: {e}")

    def get_ip_reputation(self, ip: str) -> Optional[Dict[str, Any]]:
        """Get reputation data for an IP.

        Args:
            ip: IP address to look up

        Returns:
            Reputation data or None
        """
        return self._ip_reputation.get(ip)

    def get_high_threat_ips(self, threshold: float = 50) -> List[Dict[str, Any]]:
        """Get IPs with threat score above threshold.

        Args:
            threshold: Minimum threat score

        Returns:
            List of high-threat IP records
        """
        return [
            rep
            for rep in self._ip_reputation.values()
            if rep.get("threat_score", 0) >= threshold
        ]

    # =========================================================================
    # Attack Patterns
    # =========================================================================

    async def store_attack_pattern(
        self,
        pattern: str,
        category: str,
        source_ip: str,
        severity: str,
        context: Optional[str] = None,
    ) -> str:
        """Store a detected attack pattern.

        Args:
            pattern: Pattern string/regex that matched
            category: Attack category
            source_ip: IP that used this pattern
            severity: Attack severity
            context: Additional context

        Returns:
            Pattern ID
        """
        pattern_id = f"pat-{uuid4().hex[:8]}"

        pattern_data = {
            "pattern_id": pattern_id,
            "pattern": pattern,
            "category": category,
            "severity": severity,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "occurrences": 1,
            "source_ips": [source_ip],
            "context": context,
        }

        # Check if similar pattern exists
        existing = self._find_similar_pattern(pattern, category)
        if existing:
            existing["occurrences"] += 1
            if source_ip not in existing["source_ips"]:
                existing["source_ips"].append(source_ip)
            pattern_id = existing["pattern_id"]
            pattern_data = existing
        else:
            self._attack_patterns[pattern_id] = pattern_data

        # Persist
        await self._store_pattern_to_memory(pattern_id, pattern_data)

        return pattern_id

    def _find_similar_pattern(
        self, pattern: str, category: str
    ) -> Optional[Dict[str, Any]]:
        """Find existing similar pattern."""
        for existing in self._attack_patterns.values():
            if existing["pattern"] == pattern and existing["category"] == category:
                return existing
        return None

    async def _store_pattern_to_memory(
        self, pattern_id: str, pattern_data: Dict[str, Any]
    ) -> None:
        """Store pattern in memory."""
        if not self._memory:
            return

        try:
            import json
            from core.memory.types import MemoryType

            content = json.dumps(pattern_data)
            await self._memory.add_memory(
                content=content,
                memory_type=MemoryType.LONG_TERM,
                metadata={
                    "type": "honeypot_attack_pattern",
                    "pattern_id": pattern_id,
                    "category": pattern_data["category"],
                },
            )
        except Exception as e:
            logger.warning(f"Failed to store pattern: {e}")

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about stored patterns."""
        by_category = {}
        by_severity = {}
        total_occurrences = 0

        for pattern in self._attack_patterns.values():
            cat = pattern.get("category", "unknown")
            sev = pattern.get("severity", "info")

            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1
            total_occurrences += pattern.get("occurrences", 1)

        return {
            "total_patterns": len(self._attack_patterns),
            "total_occurrences": total_occurrences,
            "by_category": by_category,
            "by_severity": by_severity,
        }

    # =========================================================================
    # CVE Correlations
    # =========================================================================

    async def store_cve_correlation(self, correlation: Dict[str, Any]) -> None:
        """Store a CVE correlation.

        Args:
            correlation: Correlation data dict
        """
        correlation_id = correlation["correlation_id"]
        self._cve_correlations[correlation_id] = correlation

        if not self._memory:
            return

        try:
            import json
            from core.memory.types import MemoryType

            content = json.dumps(correlation)
            await self._memory.add_memory(
                content=content,
                memory_type=MemoryType.LONG_TERM,
                metadata={
                    "type": "honeypot_cve_correlation",
                    "correlation_id": correlation_id,
                    "category": correlation.get("category"),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to store correlation: {e}")

    def get_cve_correlations(self) -> List[Dict[str, Any]]:
        """Get all stored correlations.

        Returns:
            List of correlations
        """
        return list(self._cve_correlations.values())

    # =========================================================================
    # Response Strategies
    # =========================================================================

    async def store_response_strategy(
        self,
        command: str,
        response: str,
        effectiveness: float,
    ) -> None:
        """Store a successful response strategy.

        Args:
            command: Command that triggered response
            response: Response that was effective
            effectiveness: Effectiveness score 0-1
        """
        strategy_id = f"resp-{uuid4().hex[:8]}"
        self._learned_responses[strategy_id] = {
            "strategy_id": strategy_id,
            "command": command,
            "response": response,
            "effectiveness": effectiveness,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_best_response(self, command: str) -> Optional[str]:
        """Get best response for a command.

        Args:
            command: Command to respond to

        Returns:
            Best response or None
        """
        best = None
        best_score = 0

        for strategy in self._learned_responses.values():
            if strategy["command"] == command:
                if strategy["effectiveness"] > best_score:
                    best = strategy["response"]
                    best_score = strategy["effectiveness"]

        return best

    # =========================================================================
    # False Positives
    # =========================================================================

    async def mark_false_positive(self, pattern: str) -> None:
        """Mark a pattern as false positive.

        Args:
            pattern: Pattern to mark
        """
        if pattern not in self._false_positives:
            self._false_positives.append(pattern)

    def is_false_positive(self, pattern: str) -> bool:
        """Check if pattern is known false positive.

        Args:
            pattern: Pattern to check

        Returns:
            True if known false positive
        """
        return pattern in self._false_positives


async def initialize_memory() -> HoneypotMemory:
    """Initialize and return HoneypotMemory instance.

    Returns:
        Initialized HoneypotMemory
    """
    memory = HoneypotMemory()
    await memory.initialize()
    return memory
