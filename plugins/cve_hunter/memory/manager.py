"""CVE Hunter Memory Manager.

CVE-specific memory management using core/memory/AgentMemory.
Provides semantic storage and recall for vulnerability knowledge.
"""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from ..config import CVEHunterConfig, get_cve_hunter_config
except (ImportError, ValueError):
    from config import CVEHunterConfig, get_cve_hunter_config  # type: ignore[no-redef]

from .types import CVEMemoryTypes

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

                # Create memory with in-memory provider
                # In production, could use Redis or vector store provider
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
        """Store a CVE record in memory.

        Args:
            cve_id: CVE identifier (e.g., CVE-2024-1234)
            description: CVE description
            severity: Severity level (critical, high, medium, low)
            cvss_score: CVSS score
            source: Source of the CVE data
            metadata: Additional metadata

        Returns:
            Memory item ID if stored, None otherwise
        """
        if not self._memory:
            return None

        content = f"CVE {cve_id}: {description}"
        meta = {
            "type": CVEMemoryTypes.CVE_RECORD,
            "cve_id": cve_id,
            "severity": severity,
            "cvss_score": cvss_score,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }

        try:
            from core.memory.types import MemoryType

            item = await self._memory.remember(
                content=content,
                memory_type=MemoryType.LONG_TERM,
                importance=self._severity_to_importance(severity),
                metadata=meta,
            )
            return str(item.id)
        except Exception as e:
            logger.warning(f"Failed to store CVE memory: {e}")
            return None

    async def recall_related_cves(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Recall CVEs related to a query.

        Uses semantic search if embeddings are available,
        falls back to keyword matching otherwise.

        Args:
            query: Search query (e.g., "buffer overflow", "remote code execution")
            limit: Maximum results to return

        Returns:
            List of related CVE memories with metadata
        """
        if not self._memory:
            return []

        try:
            results = await self._memory.recall(
                query=query,
                limit=limit,
            )

            cve_memories = []
            for item in results:
                meta = getattr(item, "metadata", {}) or {}
                if meta.get("type") != CVEMemoryTypes.CVE_RECORD:
                    continue
                cve_memories.append(
                    {
                        "memory_id": str(item.id),
                        "cve_id": meta.get("cve_id"),
                        "content": item.content,
                        "severity": meta.get("severity"),
                        "cvss_score": meta.get("cvss_score"),
                        "relevance_score": getattr(item, "score", 0.0),
                    }
                )

            return cve_memories
        except Exception as e:
            logger.warning(f"Failed to recall CVE memories: {e}")
            return []

    async def has_seen_cve(self, cve_id: str) -> bool:
        """Check if a CVE has been seen before.

        Args:
            cve_id: CVE identifier

        Returns:
            True if CVE is in memory
        """
        if not self._memory:
            return False

        try:
            results = await self._memory.recall(query=cve_id, limit=5)
        except Exception as e:
            logger.warning(
                "has_seen_cve recall failed", extra={"cve_id": cve_id, "error": str(e)}
            )
            return False

        for entry in results:
            item = entry[0] if isinstance(entry, tuple) else entry
            meta = getattr(item, "metadata", {}) or {}
            if meta.get("cve_id") == cve_id:
                return True
        return False

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
        """Store a discovery pattern.

        Args:
            pattern: The vulnerability pattern (e.g., "buffer overflow")
            confidence: Confidence score (0.0-1.0)
            source: Where the pattern was found
            was_successful: Whether this led to a valid discovery
            context: Additional context

        Returns:
            Memory item ID if stored
        """
        if not self._memory:
            return None

        memory_type = (
            CVEMemoryTypes.DISCOVERY_SUCCESS
            if was_successful
            else CVEMemoryTypes.DISCOVERY_FALSE_POSITIVE
        )

        content = f"Discovery pattern: {pattern} from {source}"
        if context:
            content += f" - Context: {context[:200]}"

        meta = {
            "type": memory_type,
            "pattern": pattern,
            "confidence": confidence,
            "source": source,
            "was_successful": was_successful,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            from core.memory.types import MemoryType

            # Successful discoveries are more important
            importance = 0.8 if was_successful else 0.3

            item = await self._memory.remember(
                content=content,
                memory_type=MemoryType.LONG_TERM,
                importance=importance,
                metadata=meta,
            )
            return str(item.id)
        except Exception as e:
            logger.warning(f"Failed to store discovery pattern: {e}")
            return None

    async def get_successful_patterns(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get successful discovery patterns for learning.

        Returns:
            List of successful pattern memories
        """
        if not self._memory:
            return []

        try:
            results = await self._memory.recall(
                query="discovery pattern successful",
                limit=limit * 2,
            )

            patterns = []
            for item in results:
                meta = getattr(item, "metadata", {}) or {}
                if not meta.get("was_successful"):
                    continue
                patterns.append(
                    {
                        "pattern": meta.get("pattern"),
                        "confidence": meta.get("confidence"),
                        "source": meta.get("source"),
                    }
                )
                if len(patterns) >= limit:
                    break

            return patterns
        except Exception:
            return []

    async def get_false_positive_patterns(
        self, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get false positive patterns to avoid.

        Returns:
            List of false positive pattern memories
        """
        if not self._memory:
            return []

        try:
            results = await self._memory.recall(
                query="discovery pattern false positive",
                limit=limit * 2,
            )

            patterns = []
            for item in results:
                meta = getattr(item, "metadata", {}) or {}
                if meta.get("was_successful"):
                    continue
                patterns.append(
                    {
                        "pattern": meta.get("pattern"),
                        "source": meta.get("source"),
                    }
                )
                if len(patterns) >= limit:
                    break

            return patterns
        except Exception:
            return []

    # =========================================================================
    # Analysis Knowledge
    # =========================================================================

    async def remember_analysis(
        self,
        cve_id: str,
        analysis_summary: str,
        exploitability_score: Optional[float] = None,
        recommendations: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Store CVE analysis results.

        Args:
            cve_id: CVE identifier
            analysis_summary: AI-generated analysis summary
            exploitability_score: Optional exploitability score
            recommendations: Optional list of recommendations

        Returns:
            Memory item ID if stored
        """
        if not self._memory:
            return None

        content = f"Analysis of {cve_id}: {analysis_summary}"

        meta = {
            "type": CVEMemoryTypes.CVE_ANALYSIS,
            "cve_id": cve_id,
            "exploitability_score": exploitability_score,
            "recommendations": recommendations or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            from core.memory.types import MemoryType

            item = await self._memory.remember(
                content=content,
                memory_type=MemoryType.LONG_TERM,
                importance=0.7,
                metadata=meta,
            )
            return str(item.id)
        except Exception as e:
            logger.warning(f"Failed to store analysis memory: {e}")
            return None

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
        if not self._memory:
            return None

        content = f"Correlation feedback {correlation_id}: {outcome}"
        meta = {
            "type": CVEMemoryTypes.CORRELATION_FEEDBACK,
            "correlation_id": correlation_id,
            "outcome": outcome,
            "correlation_type": correlation_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }

        try:
            from core.memory.types import MemoryType

            item = await self._memory.remember(
                content=content,
                memory_type=MemoryType.LONG_TERM,
                importance=0.6,
                metadata=meta,
            )
            return str(item.id)
        except Exception as e:
            logger.warning(f"Failed to store correlation feedback: {e}")
            return None

    async def remember_attack_chain_feedback(
        self,
        chain_id: str,
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store feedback for an attack-chain candidate."""
        if not self._memory:
            return None

        content = f"Attack chain feedback {chain_id}: {outcome}"
        meta = {
            "type": CVEMemoryTypes.ATTACK_CHAIN_FEEDBACK,
            "chain_id": chain_id,
            "outcome": outcome,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }

        try:
            from core.memory.types import MemoryType

            item = await self._memory.remember(
                content=content,
                memory_type=MemoryType.LONG_TERM,
                importance=0.6,
                metadata=meta,
            )
            return str(item.id)
        except Exception as e:
            logger.warning(f"Failed to store attack chain feedback: {e}")
            return None

    async def get_correlation_feedbacks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent correlation feedback entries."""
        if not self._memory:
            return []

        try:
            results = await self._memory.recall(
                query="correlation feedback",
                limit=limit * 2,
            )
        except Exception:
            return []

        feedbacks: List[Dict[str, Any]] = []
        for entry in results:
            item = entry[0] if isinstance(entry, tuple) else entry
            meta = getattr(item, "metadata", {})
            if meta.get("type") != CVEMemoryTypes.CORRELATION_FEEDBACK:
                continue
            feedbacks.append(
                {
                    "correlation_id": meta.get("correlation_id"),
                    "outcome": meta.get("outcome"),
                    "correlation_type": meta.get("correlation_type"),
                    "timestamp": meta.get("timestamp"),
                }
            )
            if len(feedbacks) >= limit:
                break

        return feedbacks

    async def get_attack_chain_feedbacks(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent attack-chain feedback entries."""
        if not self._memory:
            return []

        try:
            results = await self._memory.recall(
                query="attack chain feedback",
                limit=limit * 2,
            )
        except Exception:
            return []

        feedbacks: List[Dict[str, Any]] = []
        for entry in results:
            item = entry[0] if isinstance(entry, tuple) else entry
            meta = getattr(item, "metadata", {})
            if meta.get("type") != CVEMemoryTypes.ATTACK_CHAIN_FEEDBACK:
                continue
            feedbacks.append(
                {
                    "chain_id": meta.get("chain_id"),
                    "outcome": meta.get("outcome"),
                    "timestamp": meta.get("timestamp"),
                }
            )
            if len(feedbacks) >= limit:
                break

        return feedbacks

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
                "compressed": getattr(result, "compressed_count", 0) if result else 0,
            }
        except Exception as e:
            logger.warning(f"Memory compression failed: {e}")
            return {"status": "failed", "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics.

        Returns:
            Memory stats dict
        """
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
        """Convert severity to importance score.

        Args:
            severity: Severity string

        Returns:
            Importance score (0.0-1.0)
        """
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
    """Get CVE Hunter memory singleton.

    Returns:
        CVEHunterMemory instance
    """
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = CVEHunterMemory()
    return _memory_instance


async def initialize_memory() -> CVEHunterMemory:
    """Initialize and return CVE Hunter memory.

    Returns:
        Initialized CVEHunterMemory instance
    """
    memory = get_cve_hunter_memory()
    await memory.initialize()
    return memory
