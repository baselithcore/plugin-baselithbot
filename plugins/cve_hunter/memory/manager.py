"""CVE Hunter Memory Manager.

CVE-specific memory management using core/memory/AgentMemory.
Provides semantic storage and recall for vulnerability knowledge.

Implementation is split across private sub-modules:
  _cve.py      — CVE knowledge (remember_cve, recall_related_cves, has_seen_cve,
                  remember_analysis)
  _patterns.py — Discovery patterns (remember_discovery_pattern,
                  get_successful_patterns, get_false_positive_patterns)
  _feedback.py — Correlation/attack-chain feedback
"""

from core.observability.logging import get_logger
from typing import Any, Dict, List, Optional

try:
    from ..config import CVEHunterConfig, get_cve_hunter_config
except (ImportError, ValueError):
    from config import CVEHunterConfig, get_cve_hunter_config  # type: ignore[no-redef]

from . import _cve, _patterns, _feedback

logger = get_logger(__name__)


class CVEHunterMemory:
    """Memory manager for CVE Hunter knowledge.

    Wraps core/memory/AgentMemory with CVE-specific functionality:
    - Store and recall CVE records semantically
    - Track discovery patterns (successful and false positives)
    - Maintain correlation knowledge
    - Compress old memories automatically

    Example:
        ```python
        memory = CVEHunterMemory()
        await memory.remember_cve(cve_record)
        related = await memory.recall_related_cves("buffer overflow")
        ```
    """

    def __init__(
        self,
        config: Optional[CVEHunterConfig] = None,
        agent_memory: Optional[Any] = None,
    ):
        """Initialize CVE Hunter memory.

        Args:
            config: CVE Hunter configuration
            agent_memory: Optional AgentMemory instance (for DI/testing)
        """
        self.config = config or get_cve_hunter_config()
        self._memory = agent_memory
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the memory system."""
        if self._initialized:
            return

        if not self.config.enable_memory:
            logger.info("CVE Hunter memory disabled by configuration")
            return

        if self._memory is None:
            try:
                from core.memory import AgentMemory
                from core.memory.providers import InMemoryProvider

                provider = InMemoryProvider()
                self._memory = AgentMemory(
                    provider=provider,
                    working_memory_limit=self.config.memory_working_limit,
                )
                logger.info("CVE Hunter memory initialized with InMemoryProvider")
            except ImportError as e:
                logger.warning(f"Could not initialize memory system: {e}")
                return

        self._initialized = True

    # =========================================================================
    # CVE Knowledge
    # =========================================================================

    async def remember_cve(
        self,
        cve_id: str,
        description: str,
        severity: str,
        cvss_score: float,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store a CVE record in memory."""
        return await _cve.remember_cve(
            self._memory,
            cve_id=cve_id,
            description=description,
            severity=severity,
            cvss_score=cvss_score,
            source=source,
            metadata=metadata,
            severity_to_importance_fn=self._severity_to_importance,
        )

    async def recall_related_cves(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Recall CVEs related to a query."""
        return await _cve.recall_related_cves(self._memory, query=query, limit=limit)

    async def has_seen_cve(self, cve_id: str) -> bool:
        """Check if a CVE has been seen before."""
        return await _cve.has_seen_cve(self._memory, cve_id=cve_id)

    async def remember_analysis(
        self,
        cve_id: str,
        analysis_summary: str,
        exploitability_score: Optional[float] = None,
        recommendations: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Store CVE analysis results."""
        return await _cve.remember_analysis(
            self._memory,
            cve_id=cve_id,
            analysis_summary=analysis_summary,
            exploitability_score=exploitability_score,
            recommendations=recommendations,
        )

    # =========================================================================
    # Discovery Pattern Knowledge
    # =========================================================================

    async def remember_discovery_pattern(
        self,
        pattern: str,
        confidence: float,
        source: str,
        was_successful: bool,
        context: Optional[str] = None,
    ) -> Optional[str]:
        """Store a discovery pattern."""
        return await _patterns.remember_discovery_pattern(
            self._memory,
            pattern=pattern,
            confidence=confidence,
            source=source,
            was_successful=was_successful,
            context=context,
        )

    async def get_successful_patterns(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get successful discovery patterns for learning."""
        return await _patterns.get_successful_patterns(self._memory, limit=limit)

    async def get_false_positive_patterns(
        self, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get false positive patterns to avoid."""
        return await _patterns.get_false_positive_patterns(self._memory, limit=limit)

    # =========================================================================
    # Correlation Feedback
    # =========================================================================

    async def remember_correlation_feedback(
        self,
        correlation_id: str,
        outcome: str,
        correlation_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store feedback for a finding-to-CVE correlation."""
        return await _feedback.remember_correlation_feedback(
            self._memory,
            correlation_id=correlation_id,
            outcome=outcome,
            correlation_type=correlation_type,
            metadata=metadata,
        )

    async def remember_attack_chain_feedback(
        self,
        chain_id: str,
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store feedback for an attack-chain candidate."""
        return await _feedback.remember_attack_chain_feedback(
            self._memory,
            chain_id=chain_id,
            outcome=outcome,
            metadata=metadata,
        )

    async def get_correlation_feedbacks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent correlation feedback entries."""
        return await _feedback.get_correlation_feedbacks(self._memory, limit=limit)

    async def get_attack_chain_feedbacks(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent attack-chain feedback entries."""
        return await _feedback.get_attack_chain_feedbacks(self._memory, limit=limit)

    # =========================================================================
    # Memory Management
    # =========================================================================

    async def compress_old_memories(self) -> Dict[str, Any]:
        """Compress old memories to save space.

        Returns:
            Compression statistics
        """
        if not self._memory:
            return {"status": "disabled"}

        try:
            result = await self._memory.compress_old_memories(
                days_threshold=self.config.memory_ttl_days,
                strategy="summarization",
            )
            return {
                "status": "completed",
                "compressed": (getattr(result, "compressed_count", 0) if result else 0),
            }
        except Exception as e:
            logger.warning(f"Memory compression failed: {e}")
            return {"status": "failed", "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        if not self._memory:
            return {"status": "disabled"}

        try:
            return self._memory.get_memory_stats()
        except Exception:
            return {"status": "error"}

    def get_context(self, max_tokens: int = 2000) -> str:
        """Get formatted context from working memory.

        Args:
            max_tokens: Approximate max characters

        Returns:
            Formatted context string for LLM prompts
        """
        if not self._memory:
            return ""

        try:
            return self._memory.get_context(max_tokens=max_tokens)
        except Exception:
            return ""

    # =========================================================================
    # Helpers
    # =========================================================================

    def _severity_to_importance(self, severity: str) -> float:
        """Convert severity to importance score (0.0-1.0)."""
        mapping = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3,
            "none": 0.1,
        }
        return mapping.get(severity.lower(), 0.5)


# =============================================================================
# Module-level Instance
# =============================================================================

_memory_instance: Optional[CVEHunterMemory] = None


def get_cve_hunter_memory() -> CVEHunterMemory:
    """Get CVE Hunter memory singleton."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = CVEHunterMemory()
    return _memory_instance


async def initialize_memory() -> CVEHunterMemory:
    """Initialize and return CVE Hunter memory."""
    memory = get_cve_hunter_memory()
    await memory.initialize()
    return memory
