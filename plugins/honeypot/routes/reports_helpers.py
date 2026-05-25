"""Report Route Helpers.

Helper functions and utilities for report generation endpoints.
Extracted from reports.py for modularity.
"""

from typing import List, Optional

from ..reports import (
    ReportSection,
    ReportService,
    ReportType,
)
from ..persistence import HoneypotDAO


# Service instance (singleton pattern)
_service: Optional[ReportService] = None


def get_service() -> ReportService:
    """Get or create report service instance."""
    global _service
    if _service is None:
        dao = HoneypotDAO()
        _service = ReportService(dao=dao)
    return _service


def get_type_description(rt: ReportType) -> str:
    """Get description for report type with research focus.

    Args:
        rt: Report type enum value

    Returns:
        Human-readable description string
    """
    descriptions = {
        ReportType.EXECUTIVE: "High-level research summary with key pattern observations",
        ReportType.TECHNICAL: "Detailed technical analysis of attack patterns and techniques",
        ReportType.COMPLIANCE: "Detection methodology analysis and classification accuracy",
        ReportType.INCIDENT: "Incident timeline research with behavioral analysis",
        ReportType.PENTEST: "Penetration testing patterns and vulnerability research",
        ReportType.THREAT_INTEL: "Threat intelligence research with botnet and C&C analysis",
    }
    return descriptions.get(rt, "")


def get_section_description(rs: ReportSection) -> str:
    """Get description for report section with research focus.

    Args:
        rs: Report section enum value

    Returns:
        Human-readable description string
    """
    descriptions = {
        ReportSection.EXECUTIVE_SUMMARY: "Research overview and key findings",
        ReportSection.THREAT_LANDSCAPE: "Attack pattern research analysis",
        ReportSection.ATTACK_ANALYTICS: "Detailed attack statistics and behavioral patterns",
        ReportSection.GEO_ANALYSIS: "Geographic source distribution analysis",
        ReportSection.BOTNET_DISCOVERY: "Botnet cluster research and coordination patterns",
        ReportSection.PENTEST_RESULTS: "Penetration testing pattern analysis",
        ReportSection.CVE_CORRELATIONS: "CVE exploitation pattern research",
        ReportSection.RECOMMENDATIONS: "Research insights and future directions",
        ReportSection.IOC_LIST: "Indicators of Compromise pattern analysis",
        ReportSection.TIMELINE: "Attack timeline and temporal patterns",
    }
    return descriptions.get(rs, "")


def get_default_sections(rt: ReportType) -> List[ReportSection]:
    """Get default sections for a report type.

    Args:
        rt: Report type enum value

    Returns:
        List of default sections for the report type
    """
    defaults = {
        ReportType.EXECUTIVE: [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.THREAT_LANDSCAPE,
            ReportSection.RECOMMENDATIONS,
        ],
        ReportType.TECHNICAL: [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.ATTACK_ANALYTICS,
            ReportSection.GEO_ANALYSIS,
            ReportSection.TIMELINE,
            ReportSection.IOC_LIST,
            ReportSection.RECOMMENDATIONS,
        ],
        ReportType.COMPLIANCE: [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.ATTACK_ANALYTICS,
            ReportSection.PENTEST_RESULTS,
            ReportSection.RECOMMENDATIONS,
        ],
        ReportType.INCIDENT: [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.TIMELINE,
            ReportSection.ATTACK_ANALYTICS,
            ReportSection.IOC_LIST,
            ReportSection.RECOMMENDATIONS,
        ],
        ReportType.PENTEST: [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.PENTEST_RESULTS,
            ReportSection.CVE_CORRELATIONS,
            ReportSection.RECOMMENDATIONS,
        ],
        ReportType.THREAT_INTEL: [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.THREAT_LANDSCAPE,
            ReportSection.BOTNET_DISCOVERY,
            ReportSection.GEO_ANALYSIS,
            ReportSection.IOC_LIST,
            ReportSection.RECOMMENDATIONS,
        ],
    }
    return defaults.get(
        rt, [ReportSection.EXECUTIVE_SUMMARY, ReportSection.RECOMMENDATIONS]
    )
