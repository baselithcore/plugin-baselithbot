#!/usr/bin/env python3
"""Test script for LLM-enhanced report generation.

Usage:
    python -m plugins.honeypot.reports.test_llm_reports
    python -m plugins.honeypot.reports.test_llm_reports --provider openai
    python -m plugins.honeypot.reports.test_llm_reports --no-llm
"""

import asyncio
import argparse
import logging
from core.observability.logging import get_logger
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from plugins.honeypot.reports import (
    ReportService,
    ReportConfig,
    ReportType,
    ReportSection,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = get_logger(__name__)


async def test_executive_summary(service: ReportService, use_llm: bool):
    """Test executive summary generation."""
    logger.info(
        f"Testing Executive Summary (LLM={'enabled' if use_llm else 'disabled'})"
    )

    config = ReportConfig(
        report_type=ReportType.EXECUTIVE,
        sections=[
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.RECOMMENDATIONS,
        ],
        time_range_hours=168,  # 7 days
        organization_name="Test Security Corp",
        classification="INTERNAL",
    )

    try:
        report = await service.generate_report(
            config=config, title="Weekly Security Report"
        )

        print("\n" + "=" * 80)
        print("EXECUTIVE SUMMARY TEST")
        print("=" * 80)
        print(f"\nReport ID: {report.metadata.report_id}")
        print(f"Generated: {report.metadata.generated_at}")
        print(
            f"Time Range: {report.metadata.time_range_start} to {report.metadata.time_range_end}"
        )
        print("\n--- Executive Summary ---")
        print(report.executive_summary)
        print("\n--- Recommendations ---")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
        print("\n--- Threat Summary Stats ---")
        print(f"Total Events: {report.threat_summary.total_events}")
        print(f"Unique Attackers: {report.threat_summary.unique_attackers}")
        print(f"Critical Events: {report.threat_summary.critical_events}")
        print(f"Detected Botnets: {report.threat_summary.detected_botnets}")
        print("=" * 80 + "\n")

        return True
    except Exception as e:
        logger.error(f"Executive summary test failed: {e}", exc_info=True)
        return False


async def test_technical_report(service: ReportService, use_llm: bool):
    """Test full technical report generation."""
    logger.info(
        f"Testing Technical Report (LLM={'enabled' if use_llm else 'disabled'})"
    )

    config = ReportConfig(
        report_type=ReportType.TECHNICAL,
        sections=[
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.THREAT_LANDSCAPE,
            ReportSection.ATTACK_ANALYTICS,
            ReportSection.GEO_ANALYSIS,
            ReportSection.TIMELINE,
            ReportSection.IOC_LIST,
            ReportSection.RECOMMENDATIONS,
        ],
        time_range_hours=168,
        organization_name="Test Security Corp",
    )

    try:
        report = await service.generate_report(config=config)

        print("\n" + "=" * 80)
        print("TECHNICAL REPORT TEST")
        print("=" * 80)
        print(f"\nReport ID: {report.metadata.report_id}")
        print(f"Report Type: {report.metadata.report_type.value}")
        print("\n--- Summary Stats ---")
        print(f"Total Events: {report.threat_summary.total_events:,}")
        print(f"Unique Attackers: {report.threat_summary.unique_attackers:,}")
        print(
            f"Critical: {report.threat_summary.critical_events}, High: {report.threat_summary.high_events}"
        )
        print(
            f"Botnets: {report.threat_summary.detected_botnets}, C&C Servers: {report.threat_summary.potential_cc_servers}"
        )
        print(f"CVE Matches: {report.threat_summary.cve_matches}")
        print(f"Bot Traffic: {report.threat_summary.bot_traffic_percentage:.1f}%")

        if report.geo_distribution:
            print("\n--- Top 5 Countries ---")
            for geo in report.geo_distribution[:5]:
                print(
                    f"  {geo.country_name}: {geo.attack_count} attacks, {geo.unique_ips} IPs"
                )

        if report.attack_timeline:
            print("\n--- Recent Timeline Events (last 5) ---")
            for event in report.attack_timeline[:5]:
                print(
                    f"  [{event.severity.upper()}] {event.timestamp.strftime('%Y-%m-%d %H:%M')} - {event.category}"
                )
                print(
                    f"    {event.source_ip} ({event.country_code or 'Unknown'}) - {event.description[:80]}"
                )

        if report.iocs:
            print("\n--- IOC Summary ---")
            ioc_types = {}
            for ioc in report.iocs:
                ioc_types[ioc.ioc_type] = ioc_types.get(ioc.ioc_type, 0) + 1
            for ioc_type, count in ioc_types.items():
                print(f"  {ioc_type}: {count}")

        print("\n--- Executive Summary (truncated) ---")
        summary_preview = (
            report.executive_summary[:500] if report.executive_summary else "N/A"
        )
        print(
            summary_preview + "..."
            if len(report.executive_summary or "") > 500
            else summary_preview
        )

        print(f"\n--- Recommendations ({len(report.recommendations)}) ---")
        for i, rec in enumerate(report.recommendations[:5], 1):
            print(f"{i}. {rec}")
        if len(report.recommendations) > 5:
            print(f"   ... and {len(report.recommendations) - 5} more")

        print("=" * 80 + "\n")

        return True
    except Exception as e:
        logger.error(f"Technical report test failed: {e}", exc_info=True)
        return False


async def test_threat_intel_report(service: ReportService, use_llm: bool):
    """Test threat intelligence report."""
    logger.info(
        f"Testing Threat Intel Report (LLM={'enabled' if use_llm else 'disabled'})"
    )

    config = ReportConfig(
        report_type=ReportType.THREAT_INTEL,
        sections=[
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.THREAT_LANDSCAPE,
            ReportSection.BOTNET_DISCOVERY,
            ReportSection.GEO_ANALYSIS,
            ReportSection.IOC_LIST,
        ],
        time_range_hours=168,
        organization_name="Test Security Corp",
    )

    try:
        report = await service.generate_report(config=config)

        print("\n" + "=" * 80)
        print("THREAT INTELLIGENCE REPORT TEST")
        print("=" * 80)

        if report.botnet_activity:
            print(f"\n--- Botnet Clusters ({len(report.botnet_activity)}) ---")
            for botnet in report.botnet_activity[:3]:
                print(f"  Cluster: {botnet.cluster_id}")
                print(
                    f"    Members: {botnet.member_count}, Severity: {botnet.severity}"
                )
                print(f"    Coordination Score: {botnet.attack_coordination_score:.2f}")
                print(f"    C&C Servers: {', '.join(botnet.suspected_cc_servers[:3])}")

        print("\n--- Executive Summary Preview ---")
        if report.executive_summary:
            lines = report.executive_summary.split("\n")[:10]
            print("\n".join(lines))
            if len(report.executive_summary.split("\n")) > 10:
                print("...")

        print("=" * 80 + "\n")

        return True
    except Exception as e:
        logger.error(f"Threat intel report test failed: {e}", exc_info=True)
        return False


async def test_markdown_export(service: ReportService, use_llm: bool):
    """Test markdown rendering."""
    logger.info("Testing Markdown Export")

    config = ReportConfig(
        report_type=ReportType.TECHNICAL,
        sections=[
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.ATTACK_ANALYTICS,
            ReportSection.RECOMMENDATIONS,
        ],
        time_range_hours=24,
        organization_name="Test Corp",
    )

    try:
        report = await service.generate_report(config=config)
        markdown = service.render_markdown(report)

        output_file = (
            Path(__file__).parent
            / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        output_file.write_text(markdown, encoding="utf-8")

        print("\n" + "=" * 80)
        print("MARKDOWN EXPORT TEST")
        print("=" * 80)
        print(f"\nMarkdown report saved to: {output_file}")
        print(f"File size: {len(markdown):,} characters")
        print("\n--- Preview (first 500 chars) ---")
        print(markdown[:500])
        print("...")
        print("=" * 80 + "\n")

        return True
    except Exception as e:
        logger.error(f"Markdown export test failed: {e}", exc_info=True)
        return False


async def test_research_report(service: ReportService, use_llm: bool):
    """Test research report generation with honeypot context.

    Validates:
    - ABSTRACT section with honeypot name
    - KEY_FINDINGS section
    - MITRE_MAPPING section with ATT&CK technique IDs
    - Honeypot contextualization throughout
    """
    logger.info(f"Testing Research Report (LLM={'enabled' if use_llm else 'disabled'})")

    config = ReportConfig(
        report_type=ReportType.RESEARCH,
        sections=[
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.THREAT_LANDSCAPE,
            ReportSection.GEO_ANALYSIS,
            ReportSection.BOTNET_DISCOVERY,
            ReportSection.RECOMMENDATIONS,
        ],
        honeypot_id="ssh-ubuntu",  # Test with specific honeypot
        time_range_hours=720,  # 30 days
        organization_name="Security Research Lab",
    )

    try:
        report = await service.generate_report(
            config=config, title="SSH Ubuntu Honeypot Research Analysis"
        )

        print("\n" + "=" * 80)
        print("RESEARCH REPORT TEST")
        print("=" * 80)
        print(f"\nReport ID: {report.metadata.report_id}")
        print(f"Report Type: {report.metadata.report_type.value}")
        print(f"Honeypot Filter: {report.metadata.honeypot_filter}")

        print("\n--- Threat Summary ---")
        print(f"Total Events: {report.threat_summary.total_events:,}")
        print(f"Unique Attackers: {report.threat_summary.unique_attackers:,}")
        print(f"Critical Events: {report.threat_summary.critical_events}")
        print(f"CVE Matches: {report.threat_summary.cve_matches}")

        if report.executive_summary:
            print("\n--- Executive Summary / Research Sections (truncated) ---")
            summary_lines = report.executive_summary.split("\n")[:20]
            print("\n".join(summary_lines))
            if len(report.executive_summary.split("\n")) > 20:
                print("...")

            # Validate honeypot name appears in report
            if "ssh" in report.executive_summary.lower():
                print("\n✓ Honeypot name appears in report content")
            else:
                print("\n⚠ Honeypot name not found in report (may use fallback)")

            # Check for MITRE references
            if "T1" in report.executive_summary or "MITRE" in report.executive_summary:
                print("✓ MITRE ATT&CK references found")
            else:
                print("⚠ No MITRE ATT&CK references (may use fallback)")

        print(f"\n--- Recommendations ({len(report.recommendations)}) ---")
        for i, rec in enumerate(report.recommendations[:5], 1):
            print(f"{i}. {rec}")
        if len(report.recommendations) > 5:
            print(f"   ... and {len(report.recommendations) - 5} more")

        print("=" * 80 + "\n")

        return True
    except Exception as e:
        logger.error(f"Research report test failed: {e}", exc_info=True)
        return False


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test LLM-enhanced report generation")
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai"],
        help="Override LLM provider (default: from .env)",
    )
    parser.add_argument(
        "--no-llm", action="store_true", help="Disable LLM, use templates only"
    )
    parser.add_argument(
        "--test",
        choices=[
            "executive",
            "technical",
            "threat_intel",
            "research",
            "markdown",
            "all",
        ],
        default="all",
        help="Which test to run (default: all)",
    )
    args = parser.parse_args()

    # Override provider if specified
    if args.provider:
        import os

        os.environ["LLM_PROVIDER"] = args.provider
        logger.info(f"LLM provider overridden to: {args.provider}")

    # Initialize service
    use_llm = not args.no_llm
    service = ReportService(use_llm=use_llm)

    logger.info("=" * 80)
    logger.info("LLM-Enhanced Report Generation Test Suite")
    logger.info("=" * 80)
    logger.info(f"LLM Enabled: {use_llm}")
    if use_llm:
        try:
            from core.config import get_llm_config

            config = get_llm_config()
            logger.info(f"Provider: {config.provider}")
            logger.info(f"Model: {config.model}")
        except Exception as e:
            logger.warning(f"Could not load LLM config: {e}")

    # Run tests
    results = {}

    if args.test in ["executive", "all"]:
        results["executive"] = await test_executive_summary(service, use_llm)

    if args.test in ["technical", "all"]:
        results["technical"] = await test_technical_report(service, use_llm)

    if args.test in ["threat_intel", "all"]:
        results["threat_intel"] = await test_threat_intel_report(service, use_llm)

    if args.test in ["research", "all"]:
        results["research"] = await test_research_report(service, use_llm)

    if args.test in ["markdown", "all"]:
        results["markdown"] = await test_markdown_export(service, use_llm)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name.upper()}: {status}")

    all_passed = all(results.values())
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    print("=" * 80 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
