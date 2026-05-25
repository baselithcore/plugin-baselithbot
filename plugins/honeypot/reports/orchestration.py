"""Report Data Orchestration.

Coordinates parallel data gathering for report generation.
Extracted from service.py for modularity (Phase 1 refactoring).
"""

import asyncio
from core.observability.logging import get_logger
from datetime import datetime
from typing import Tuple

from .aggregator import ReportDataAggregator
from .models import (
    ReportConfig,
    ReportSection,
)

logger = get_logger(__name__)


async def gather_section_data(
    aggregator: ReportDataAggregator,
    config: ReportConfig,
    time_start: datetime,
) -> Tuple[list, list, list, list, list, list]:
    """Gather all section data in PARALLEL for performance.

    Uses asyncio.gather() to run independent aggregation tasks concurrently,
    reducing total latency from sequential sum to the slowest individual task.

    Args:
        aggregator: ReportDataAggregator instance
        config: Report configuration with sections list
        time_start: Start of time range for data

    Returns:
        Tuple of (timeline, geo_distribution, botnet_activity,
                 pentest_results, vulnerabilities, iocs)
    """
    # Define tasks based on requested sections
    sections = config.sections

    timeline_task = (
        aggregator.build_attack_timeline(config.honeypot_id, time_start)
        if ReportSection.TIMELINE in sections
        else _async_none()
    )

    geo_task = (
        aggregator.build_geo_distribution(config.honeypot_id, time_start)
        if ReportSection.GEO_ANALYSIS in sections
        else _async_none()
    )

    botnet_task = (
        aggregator.build_botnet_summary(config.honeypot_id)
        if ReportSection.BOTNET_DISCOVERY in sections
        else _async_none()
    )

    pentest_task = (
        aggregator.build_pentest_summary()
        if ReportSection.PENTEST_RESULTS in sections
        else _async_none()
    )

    vuln_task = (
        aggregator.build_vulnerability_list()
        if ReportSection.PENTEST_RESULTS in sections
        else _async_none()
    )

    ioc_task = (
        aggregator.build_ioc_list(config.honeypot_id, time_start)
        if ReportSection.IOC_LIST in sections
        else _async_none()
    )

    # Run all tasks in parallel
    results = await asyncio.gather(
        timeline_task,
        geo_task,
        botnet_task,
        pentest_task,
        vuln_task,
        ioc_task,
        return_exceptions=True,
    )

    # Handle exceptions gracefully, returning empty lists
    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Section data fetch {i} failed: {result}")
            processed.append([])
        else:
            processed.append(result if result is not None else [])

    return tuple(processed)  # type: ignore


async def gather_enrichment_data(
    aggregator: ReportDataAggregator,
    config: ReportConfig,
) -> Tuple:
    """Gather all enrichment data in parallel.

    Fetches discovery analysis metadata, correlations, MISP status,
    threat intel summary, payload excerpts, and credential analysis.

    Args:
        aggregator: ReportDataAggregator instance
        config: Report configuration

    Returns:
        Tuple of (discovery_enrichment, correlations, misp_status,
                 threat_intel_summary, payload_excerpts, credential_analysis, sequential_analysis)
    """
    # All enrichment tasks run in parallel
    results = await asyncio.gather(
        aggregator.build_discovery_enrichment(config.honeypot_id),
        aggregator.build_correlations(config.honeypot_id),
        aggregator.build_misp_status(),
        aggregator.build_threat_intel_summary(config.honeypot_id),
        aggregator.build_payload_excerpts(config.honeypot_id, max_excerpts=10),
        aggregator.build_credential_analysis(config.honeypot_id),
        # NEW: Sequential Analysis
        aggregator.build_sequential_analysis(
            config.honeypot_id, datetime.now(), limit=5
        )
        if ReportSection.SEQUENTIAL_ANALYSIS in config.sections
        else _async_none(),
        return_exceptions=True,
    )

    # Process results, handling exceptions
    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Enrichment data fetch {i} failed: {result}")
            # Return appropriate empty default based on index
            if i in (
                1,
                4,
                6,
            ):  # correlations, payload_excerpts, sequential_analysis (lists)
                processed.append([])
            else:  # Others are Optional or have defaults
                processed.append(None)
        else:
            processed.append(result)

    return tuple(processed)


async def _async_none() -> None:
    """Return None as an async operation (for sections not requested)."""
    return None
