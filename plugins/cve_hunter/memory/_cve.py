"""CVE Hunter Memory — CVE knowledge store methods."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.observability.logging import get_logger

from .types import CVEMemoryTypes

logger = get_logger(__name__)


async def remember_cve(
    memory: Any,
    cve_id: str,
    description: str,
    severity: str,
    cvss_score: float,
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
    severity_to_importance_fn: Any = None,
) -> Optional[str]:
    """Store a CVE record in memory.

    Args:
        memory: AgentMemory instance
        cve_id: CVE identifier
        description: CVE description
        severity: Severity level
        cvss_score: CVSS score
        source: Source of the CVE data
        metadata: Additional metadata
        severity_to_importance_fn: Callable mapping severity → float

    Returns:
        Memory item ID if stored, None otherwise
    """
    if not memory:
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

    importance = 0.5
    if severity_to_importance_fn:
        importance = severity_to_importance_fn(severity)

    try:
        from core.memory.types import MemoryType

        item = await memory.remember(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            importance=importance,
            metadata=meta,
        )
        return str(item.id)
    except Exception as e:
        logger.warning(f"Failed to store CVE memory: {e}")
        return None


async def recall_related_cves(
    memory: Any,
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Recall CVEs related to a query.

    Args:
        memory: AgentMemory instance
        query: Search query
        limit: Maximum results to return

    Returns:
        List of related CVE memories with metadata
    """
    if not memory:
        return []

    try:
        results = await memory.recall(query=query, limit=limit)

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


async def has_seen_cve(memory: Any, cve_id: str) -> bool:
    """Check if a CVE has been seen before.

    Args:
        memory: AgentMemory instance
        cve_id: CVE identifier

    Returns:
        True if CVE is in memory
    """
    if not memory:
        return False

    try:
        results = await memory.recall(query=cve_id, limit=5)
    except Exception as e:
        logger.warning(
            "has_seen_cve recall failed",
            extra={"cve_id": cve_id, "error": str(e)},
        )
        return False

    for entry in results:
        item = entry[0] if isinstance(entry, tuple) else entry
        meta = getattr(item, "metadata", {}) or {}
        if meta.get("cve_id") == cve_id:
            return True
    return False


async def remember_analysis(
    memory: Any,
    cve_id: str,
    analysis_summary: str,
    exploitability_score: Optional[float] = None,
    recommendations: Optional[List[str]] = None,
) -> Optional[str]:
    """Store CVE analysis results.

    Args:
        memory: AgentMemory instance
        cve_id: CVE identifier
        analysis_summary: AI-generated analysis summary
        exploitability_score: Optional exploitability score
        recommendations: Optional list of recommendations

    Returns:
        Memory item ID if stored
    """
    if not memory:
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

        item = await memory.remember(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            importance=0.7,
            metadata=meta,
        )
        return str(item.id)
    except Exception as e:
        logger.warning(f"Failed to store analysis memory: {e}")
        return None
