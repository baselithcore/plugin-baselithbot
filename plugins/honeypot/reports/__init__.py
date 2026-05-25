"""Report Generation Module.

Provides cybersecurity report generation from honeypot data.
Supports PDF and Markdown output formats with optional LLM enhancement.
"""

from .models import (
    ReportConfig,
    ReportFormat,
    ReportSection,
    ReportType,
    SecurityReport,
    ThreatSummary,
)
from .service import ReportService
from .llm import ModularReportLLMService

__all__ = [
    "ReportService",
    "ModularReportLLMService",
    "ReportConfig",
    "ReportFormat",
    "ReportSection",
    "ReportType",
    "SecurityReport",
    "ThreatSummary",
]
