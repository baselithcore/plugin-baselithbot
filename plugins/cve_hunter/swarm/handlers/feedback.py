"""Feedback Handler for CVE Hunter Swarm."""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


try:
    from ...agents.discovery import CVEDiscoveryAgent
    from ...memory import CVEHunterMemory
except ImportError:
    from plugins.cve_hunter.agents.discovery import CVEDiscoveryAgent
    from plugins.cve_hunter.memory import CVEHunterMemory

logger = get_logger(__name__)


class FeedbackHandler:
    """Handles feedback recording and processing for CVE Hunter."""

    def __init__(
        self,
        memory: Optional[CVEHunterMemory],
        discovery_agent: CVEDiscoveryAgent,
    ):
        """Initialize feedback handler.

        Args:
            memory: Memory system instance
            discovery_agent: Discovery agent instance for pattern learning
        """
        self._memory = memory
        self._discovery = discovery_agent

        # Local state caches
        self.finding_correlation_feedback: Dict[str, Dict[str, str]] = {}
        self.attack_chain_feedback: Dict[str, Dict[str, str]] = {}
        self.cve_correlation_feedback: Dict[str, Dict[str, str]] = {}
        self.feedback_log: List[Dict[str, Any]] = []

    async def load_from_memory(self) -> None:
        """Hydrate feedback caches from memory."""
        if not self._memory:
            return

        try:
            correlation_feedbacks = await self._memory.get_correlation_feedbacks()
            for item in correlation_feedbacks:
                correlation_id = item.get("correlation_id")
                outcome = item.get("outcome")
                correlation_type = item.get("correlation_type")
                timestamp = item.get("timestamp")
                if not correlation_id or not outcome:
                    continue
                entry = {"outcome": outcome, "timestamp": timestamp or ""}

                if correlation_type == "finding_cve":
                    self.finding_correlation_feedback[correlation_id] = entry
                    self._append_log(
                        {
                            "type": "finding_cve",
                            "id": correlation_id,
                            "outcome": outcome,
                            "timestamp": timestamp or "",
                            "label": "Finding-CVE correlation",
                        }
                    )
                elif correlation_type == "cve_correlation":
                    self.cve_correlation_feedback[correlation_id] = entry
                    self._append_log(
                        {
                            "type": "cve_correlation",
                            "id": correlation_id,
                            "outcome": outcome,
                            "timestamp": timestamp or "",
                            "label": "CVE correlation",
                        }
                    )

            chain_feedbacks = await self._memory.get_attack_chain_feedbacks()
            for item in chain_feedbacks:
                chain_id = item.get("chain_id")
                outcome = item.get("outcome")
                timestamp = item.get("timestamp")
                if chain_id and outcome:
                    self.attack_chain_feedback[chain_id] = {
                        "outcome": outcome,
                        "timestamp": timestamp or "",
                    }
                    self._append_log(
                        {
                            "type": "attack_chain",
                            "id": chain_id,
                            "outcome": outcome,
                            "timestamp": timestamp or "",
                            "label": "Attack chain candidate",
                        }
                    )
        except Exception as e:
            logger.debug(f"Failed to load feedback from memory: {e}")

    def get_outcome(
        self, feedback_dict: Dict[str, Dict[str, str]], item_id: str
    ) -> str:
        """Get feedback outcome for an item."""
        if item_id not in feedback_dict:
            return "pending"
        return feedback_dict[item_id].get("outcome", "pending")

    def get_audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent feedback audit events."""
        if limit <= 0:
            return []
        return list(reversed(self.feedback_log[-limit:]))

    def _append_log(self, entry: Dict[str, Any]) -> None:
        """Append to feedback audit log."""
        self.feedback_log.append(entry)
        if len(self.feedback_log) > 1000:
            self.feedback_log.pop(0)

    async def record_sast_feedback(
        self,
        finding: Any,  # SASTFinding
        outcome: str,
        source: str = "user",
    ) -> Tuple[bool, str]:
        """Record feedback for a SAST finding.

        Returns:
            Tuple of (success, log_message)
        """
        normalized = outcome.strip().lower()
        was_successful = normalized == "confirmed"
        finding.feedback = normalized

        # Use protected method reference - assumed safe within plugin package
        await self._discovery._record_discovery_pattern(
            pattern=finding.pattern,
            confidence=finding.confidence,
            source=f"sast:{source}",
            was_successful=was_successful,
            context=finding.context,
        )

        self._append_log(
            {
                "type": "sast",
                "id": finding.finding_id,
                "outcome": normalized,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "label": finding.pattern,
                "detail": finding.file_path,
            }
        )

        return True, f"SAST: Feedback recorded for {finding.finding_id} ({normalized})."

    async def record_dast_feedback(
        self,
        finding: Any,  # DASTFinding
        outcome: str,
        source: str = "user",
    ) -> Tuple[bool, str]:
        """Record feedback for a DAST finding."""
        normalized = outcome.strip().lower()
        was_successful = normalized == "confirmed"
        finding.feedback = normalized

        await self._discovery._record_discovery_pattern(
            pattern=finding.pattern,
            confidence=finding.confidence,
            source=f"dast:{source}",
            was_successful=was_successful,
            context=finding.context,
        )

        self._append_log(
            {
                "type": "dast",
                "id": finding.finding_id,
                "outcome": normalized,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "label": finding.pattern,
                "detail": finding.url,
            }
        )

        return True, f"DAST: Feedback recorded for {finding.finding_id} ({normalized})."

    async def record_discovery_feedback(
        self,
        finding: Dict[str, Any],
        finding_id: str,
        outcome: str,
        source: str = "user",
    ) -> Tuple[bool, str]:
        """Record feedback for a raw discovery finding."""
        normalized = outcome.strip().lower()
        was_successful = normalized == "confirmed"

        pattern = finding.get("pattern", "unknown")
        source_value = finding.get("source", "unknown")
        context = finding.get("context")

        await self._discovery._record_discovery_pattern(
            pattern=pattern,
            confidence=float(finding.get("confidence", 0.0)),
            source=f"discovery:{source}",
            was_successful=was_successful,
            context=context,
        )

        self._append_log(
            {
                "type": "discovery",
                "id": finding_id,
                "outcome": normalized,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "label": pattern,
                "detail": source_value,
            }
        )

        return True, f"DISCOVERY: Feedback recorded for {finding_id} ({normalized})."

    async def record_finding_correlation_feedback(
        self, correlation_id: str, outcome: str, source: str = "user"
    ) -> Tuple[bool, str]:
        """Record feedback for a finding-to-CVE correlation."""
        normalized = outcome.strip().lower()
        if normalized not in {"confirmed", "false_positive"}:
            return False, ""

        timestamp = datetime.now(timezone.utc).isoformat()
        self.finding_correlation_feedback[correlation_id] = {
            "outcome": normalized,
            "timestamp": timestamp,
        }

        self._append_log(
            {
                "type": "finding_cve",
                "id": correlation_id,
                "outcome": normalized,
                "timestamp": timestamp,
                "label": "Finding-CVE correlation",
            }
        )

        if self._memory:
            await self._memory.remember_correlation_feedback(
                correlation_id=correlation_id,
                outcome=normalized,
                correlation_type="finding_cve",
                metadata={"source": source},
            )

        return (
            True,
            f"CORRELATOR: Feedback recorded for {correlation_id} ({normalized}).",
        )

    async def record_attack_chain_feedback(
        self, chain_id: str, outcome: str, source: str = "user"
    ) -> Tuple[bool, str]:
        """Record feedback for an attack-chain candidate."""
        normalized = outcome.strip().lower()
        if normalized not in {"confirmed", "false_positive"}:
            return False, ""

        timestamp = datetime.now(timezone.utc).isoformat()
        self.attack_chain_feedback[chain_id] = {
            "outcome": normalized,
            "timestamp": timestamp,
        }

        self._append_log(
            {
                "type": "attack_chain",
                "id": chain_id,
                "outcome": normalized,
                "timestamp": timestamp,
                "label": "Attack chain candidate",
            }
        )

        if self._memory:
            await self._memory.remember_attack_chain_feedback(
                chain_id=chain_id,
                outcome=normalized,
                metadata={"source": source},
            )

        return (
            True,
            f"CORRELATOR: Feedback recorded for chain {chain_id} ({normalized}).",
        )

    async def record_cve_correlation_feedback(
        self, correlation_id: str, outcome: str, source: str = "user"
    ) -> Tuple[bool, str]:
        """Record feedback for a CVE correlation."""
        normalized = outcome.strip().lower()
        if normalized not in {"confirmed", "false_positive"}:
            return False, ""

        timestamp = datetime.now(timezone.utc).isoformat()
        self.cve_correlation_feedback[correlation_id] = {
            "outcome": normalized,
            "timestamp": timestamp,
        }

        self._append_log(
            {
                "type": "cve_correlation",
                "id": correlation_id,
                "outcome": normalized,
                "timestamp": timestamp,
                "label": "CVE correlation",
            }
        )

        if self._memory:
            await self._memory.remember_correlation_feedback(
                correlation_id=correlation_id,
                outcome=normalized,
                correlation_type="cve_correlation",
                metadata={"source": source},
            )

        return (
            True,
            f"CORRELATOR: Feedback recorded for CVE correlation {correlation_id} ({normalized}).",
        )
