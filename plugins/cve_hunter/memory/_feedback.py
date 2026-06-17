"""CVE Hunter Memory — correlation and attack-chain feedback methods."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.observability.logging import get_logger

from .types import CVEMemoryTypes

logger = get_logger(__name__)


async def remember_correlation_feedback(
    memory: Any,
    correlation_id: str,
    outcome: str,
    correlation_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Store feedback for a finding-to-CVE correlation.

    Args:
        memory: AgentMemory instance
        correlation_id: Unique correlation identifier
        outcome: Feedback outcome string
        correlation_type: Type of correlation
        metadata: Additional metadata

    Returns:
        Memory item ID if stored
    """
    if not memory:
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

        item = await memory.remember(
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
    memory: Any,
    chain_id: str,
    outcome: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Store feedback for an attack-chain candidate.

    Args:
        memory: AgentMemory instance
        chain_id: Unique chain identifier
        outcome: Feedback outcome string
        metadata: Additional metadata

    Returns:
        Memory item ID if stored
    """
    if not memory:
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

        item = await memory.remember(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            importance=0.6,
            metadata=meta,
        )
        return str(item.id)
    except Exception as e:
        logger.warning(f"Failed to store attack chain feedback: {e}")
        return None


async def get_correlation_feedbacks(
    memory: Any, limit: int = 100
) -> List[Dict[str, Any]]:
    """Get recent correlation feedback entries.

    Args:
        memory: AgentMemory instance
        limit: Maximum results

    Returns:
        List of correlation feedback dicts
    """
    if not memory:
        return []

    try:
        results = await memory.recall(
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
    memory: Any, limit: int = 100
) -> List[Dict[str, Any]]:
    """Get recent attack-chain feedback entries.

    Args:
        memory: AgentMemory instance
        limit: Maximum results

    Returns:
        List of attack-chain feedback dicts
    """
    if not memory:
        return []

    try:
        results = await memory.recall(
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
