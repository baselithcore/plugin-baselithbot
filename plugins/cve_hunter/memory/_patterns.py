"""CVE Hunter Memory — discovery pattern store methods."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.observability.logging import get_logger

from .types import CVEMemoryTypes

logger = get_logger(__name__)


async def remember_discovery_pattern(
    memory: Any,
    pattern: str,
    confidence: float,
    source: str,
    was_successful: bool,
    context: Optional[str] = None,
) -> Optional[str]:
    """Store a discovery pattern.

    Args:
        memory: AgentMemory instance
        pattern: The vulnerability pattern
        confidence: Confidence score (0.0-1.0)
        source: Where the pattern was found
        was_successful: Whether this led to a valid discovery
        context: Additional context

    Returns:
        Memory item ID if stored
    """
    if not memory:
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

        importance = 0.8 if was_successful else 0.3

        item = await memory.remember(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            importance=importance,
            metadata=meta,
        )
        return str(item.id)
    except Exception as e:
        logger.warning(f"Failed to store discovery pattern: {e}")
        return None


async def get_successful_patterns(memory: Any, limit: int = 20) -> List[Dict[str, Any]]:
    """Get successful discovery patterns for learning.

    Args:
        memory: AgentMemory instance
        limit: Maximum results

    Returns:
        List of successful pattern memories
    """
    if not memory:
        return []

    try:
        results = await memory.recall(
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
    memory: Any, limit: int = 20
) -> List[Dict[str, Any]]:
    """Get false positive patterns to avoid.

    Args:
        memory: AgentMemory instance
        limit: Maximum results

    Returns:
        List of false positive pattern memories
    """
    if not memory:
        return []

    try:
        results = await memory.recall(
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
