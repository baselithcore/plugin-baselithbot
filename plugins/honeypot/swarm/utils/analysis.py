from core.observability.logging import get_logger
from typing import TYPE_CHECKING, Optional, Dict, Any
from uuid import uuid4

from core.swarm.types import Task, TaskPriority
from ...models import AttackEvent, AttackSeverity

if TYPE_CHECKING:
    from ..coordinator import HoneypotSwarmCoordinator

logger = get_logger(__name__)


async def get_honeypot_metadata(
    coordinator: "HoneypotSwarmCoordinator", honeypot_id: str
) -> Dict[str, Any]:
    """Fetch honeypot metadata including CVE associations.

    Args:
        coordinator: The coordinator instance
        honeypot_id: The honeypot identifier

    Returns:
        Dict with honeypot name, description, and tags (including CVE tags)
    """
    try:
        honeypot = await coordinator.get_honeypot(honeypot_id)
        if honeypot:
            return {
                "name": honeypot.name,
                "description": honeypot.description,
                "protocol": honeypot.protocol,
                "tags": honeypot.tags,  # Contains CVE tags like "cve-2024-21762"
            }
    except Exception as e:
        logger.warning(f"Failed to fetch honeypot metadata for {honeypot_id}: {e}")
    return {}


def _build_analysis_context(
    event: AttackEvent, honeypot_meta: Dict[str, Any]
) -> Dict[str, Any]:
    """Build comprehensive context dict for LLM analysis.

    Args:
        event: The attack event
        honeypot_meta: Metadata about the honeypot

    Returns:
        Context dict with all relevant information
    """
    # Extract CVE tags from honeypot metadata
    cve_tags = [tag for tag in honeypot_meta.get("tags", []) if tag.startswith("cve-")]

    return {
        # Honeypot context
        "honeypot_id": event.honeypot_id,
        "honeypot_name": honeypot_meta.get("name", event.honeypot_id),
        "honeypot_description": honeypot_meta.get("description", ""),
        "honeypot_cve_tags": cve_tags,
        # Event classification (already detected)
        "category": event.category.value if event.category else "unknown",
        "severity": event.severity.value if event.severity else "info",
        "detected_patterns": list(event.detected_patterns)
        if event.detected_patterns
        else [],
        # CVE correlation already performed
        "matched_cves": list(event.matched_cves) if event.matched_cves else [],
        "matched_cwes": list(event.matched_cwes) if event.matched_cwes else [],
        # HTTP context (if available)
        "http_method": event.http_method,
        "http_path": event.http_path,
        "http_headers": dict(event.http_headers) if event.http_headers else None,
        "http_body": event.http_body,
        # Bot detection context
        "is_bot": event.is_bot,
        "bot_confidence": event.bot_confidence,
    }


async def submit_analysis_task(
    coordinator: "HoneypotSwarmCoordinator", event: AttackEvent
) -> None:
    """Submit analysis task to colony.

    Args:
        coordinator: The coordinator instance
        event: The attack event
    """
    from ..coordinator import PheromoneTypes

    task = Task(
        id=str(uuid4()),
        parameters={"event_id": event.event_id, "name": "analyze_attack"},
        description=f"Analyze {event.severity.value} attack from {event.source_ip}",
        required_capabilities=["analysis", "pattern"],
        priority=TaskPriority.HIGH
        if event.severity == AttackSeverity.CRITICAL
        else TaskPriority.NORMAL,
    )
    await coordinator._colony.submit_task(task)

    # Perform analysis
    analysis = await coordinator._pattern_analyzer.analyze_payload(
        payload=event.raw_data or "",
        protocol=event.protocol.value,
        source_ip=event.source_ip,
    )

    # CVE correlation
    if analysis.get("category"):
        # Fetch honeypot tags for better correlation
        honeypot_meta = await get_honeypot_metadata(coordinator, event.honeypot_id)
        cve_tags = [
            tag for tag in honeypot_meta.get("tags", []) if tag.startswith("cve-")
        ]

        correlation = await coordinator._cve_correlator.correlate_attack(
            event_id=event.event_id,
            category=analysis["category"],
            patterns=event.detected_patterns,
            source_ip=event.source_ip,
            honeypot_tags=cve_tags,
        )

        if correlation:
            event.matched_cves = correlation.get("matched_cves", [])
            event.matched_cwes = correlation.get("matched_cwes", [])

            # Emit pheromone for CVE match
            coordinator._pheromones.emit(
                PheromoneTypes.CVE_MATCH,
                strength=correlation.get("confidence", 0.5),
                metadata={"cves": event.matched_cves},
            )

    # Persist findings to DB
    try:
        from ...persistence.events import update_event_analysis

        # Construct analysis text similar to analyze_event
        llm_data = analysis.get("llm_analysis") or {}
        analysis_text = (
            llm_data.get("detailed_analysis")
            or llm_data.get("summary")
            or analysis.get("matched_signature")
            or f"Automated analysis: {analysis.get('category')}"
        )

        await update_event_analysis(
            event_id=event.event_id,
            analysis=analysis_text,
            category=analysis.get("category"),
            matched_cves=event.matched_cves,
        )
    except Exception as e:
        logger.error(f"Failed to persist automated analysis for {event.event_id}: {e}")

    coordinator._colony.complete_task(task.id, success=True, result=analysis)


async def analyze_event(
    coordinator: "HoneypotSwarmCoordinator", event_id: str
) -> Optional[Dict[str, Any]]:
    """Analyze attack event on demand using AI with full context.

    This enhanced version collects comprehensive context including:
    - Honeypot metadata (name, description, CVE tags)
    - Already detected patterns and CVE correlations
    - HTTP details (method, path, headers, body)
    - Bot detection signals

    Args:
        coordinator: The coordinator instance
        event_id: Event ID to analyze

    Returns:
        Analysis result dict or None if event not found
    """
    logger.info(f"Starting context-enriched analysis for event {event_id}")

    # Find event in memory buffer
    # Find event (memory or DB)
    event = await coordinator.get_event_full(event_id)
    if not event:
        logger.warning(f"Event {event_id} not found for analysis")
        return None

    # Fetch honeypot metadata for context
    honeypot_meta = await get_honeypot_metadata(coordinator, event.honeypot_id)
    logger.debug(f"Honeypot metadata for {event.honeypot_id}: {honeypot_meta}")

    # Build comprehensive context
    context = _build_analysis_context(event, honeypot_meta)
    logger.debug(f"Built analysis context: {list(context.keys())}")

    # Build payload string - prefer raw_data, then command, then HTTP path
    payload = event.raw_data or event.command or ""

    # For HTTP events, construct a more complete payload representation
    if event.protocol.value == "http":
        http_parts = []
        if event.http_method and event.http_path:
            http_parts.append(f"{event.http_method} {event.http_path}")
        if event.http_headers:
            for key, value in event.http_headers.items():
                http_parts.append(f"{key}: {value}")
        if event.http_body:
            http_parts.append("")  # Empty line before body
            http_parts.append(event.http_body)
        if http_parts:
            payload = "\n".join(http_parts)

    # Perform analysis with full context
    analysis_result = await coordinator._pattern_analyzer.analyze_payload(
        payload=payload,
        protocol=event.protocol.value,
        source_ip=event.source_ip,
        force_llm=True,  # Force LLM for on-demand analysis
        context=context,  # Pass full context for enriched analysis
    )

    # Extract LLM analysis if available
    llm_data = analysis_result.get("llm_analysis") or {}

    # Construct response
    analysis_text = (
        llm_data.get("detailed_analysis")
        or llm_data.get("summary")
        or analysis_result.get("matched_signature")
        or "No detailed analysis available."
    )

    result = {
        "event_id": event_id,
        "analysis": analysis_text,
        "recommendations": llm_data.get("techniques")
        or [analysis_result.get("category", "unknown")],
        # Include context info in response for transparency
        "context_used": {
            "honeypot": honeypot_meta.get("name", event.honeypot_id),
            "matched_cves": context.get("matched_cves", []),
            "detected_patterns": context.get("detected_patterns", []),
        },
    }

    # Persist analysis
    try:
        from ...persistence.events import update_event_analysis

        await update_event_analysis(
            event_id=event_id,
            analysis=analysis_text,
            category=analysis_result.get("category"),
        )
        logger.info(f"Persisted analysis for event {event_id}")
    except Exception as e:
        logger.error(f"Failed to persist analysis for {event_id}: {e}")

    return result
