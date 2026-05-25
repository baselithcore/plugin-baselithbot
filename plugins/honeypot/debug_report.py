import asyncio
import logging
import os
import sys
from core.observability.logging import get_logger
from unittest.mock import AsyncMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

# Add project root to path
sys.path.append(os.getcwd())

try:
    from plugins.honeypot.reports.service import ReportService
    from plugins.honeypot.reports.models import (
        ReportConfig,
        ReportType,
        ReportSection,
        ThreatSummary,
    )
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)


async def main():
    print("Initializing Service...")
    try:
        # Initialize service with explicit LLM enabled
        # We pass dao=None, it will lazy load.
        service = ReportService(dao=None, use_llm=True)
        print("Service initialized.")

        # Mock the aggregator to bypass DB calls
        # We need to access the aggregator property first to create it
        agg = service.aggregator
        # Now mock the methods
        agg.build_threat_summary = AsyncMock(return_value=ThreatSummary())
        # Mock _gather_section_data on the service itself since it calls aggregator methods
        # Actually generate_report calls self.aggregator.build_threat_summary
        # And self._gather_section_data

        # We want _gather_section_data to return empty lists
        service._gather_section_data = AsyncMock(return_value=([], [], [], [], [], []))

        # Also mock get_registry to avoid issues if registry is empty
        # In service.py: registry = get_registry()
        # We can't easily mock the global function import inside the method without patching
        # But if get_registry() works (it should), we are fine.

        config = ReportConfig(
            report_type=ReportType.TECHNICAL,
            time_range_hours=168,
            honeypot_id="react2shell",
            sections=[
                ReportSection.EXECUTIVE_SUMMARY
            ],  # Request Executive Summary to trigger LLM
        )

        print("Generating Report (forcing LLM path)...")
        report = await service.generate_report(config=config)
        print("Success! Report generated.")
        if report.executive_summary:
            print("Executive Summary generated.")
        else:
            print("Executive Summary is empty.")

    except Exception:
        print("\n!!! EXCEPTION CAUGHT !!!")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
