"""CVE Reporter Agent.

Agent responsible for generating structured reports in multiple formats.
Supports JSON, Markdown, and HTML output with customizable templates.
"""

from core.observability.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.di import ServiceRegistry
from core.interfaces import LLMServiceProtocol

try:
    from ..config import CVEHunterConfig, get_cve_hunter_config
    from ..models import CVERecord, CVESeverity, VulnerabilityAlert
except ImportError:
    from config import CVEHunterConfig, get_cve_hunter_config  # type: ignore[no-redef]
    from models import CVERecord, CVESeverity, VulnerabilityAlert  # type: ignore[no-redef]


logger = get_logger(__name__)


# =============================================================================
# Report Models
# =============================================================================


class ReportFormat(str, Enum):
    """Supported report formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"


@dataclass
class ReportSection:
    """A section within a report."""

    title: str
    content: str
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CVEReport:
    """Generated CVE report."""

    report_id: str
    title: str
    format: ReportFormat
    sections: List[ReportSection]
    summary: str
    generated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "report_id": self.report_id,
            "title": self.title,
            "format": self.format.value,
            "sections": [
                {"title": s.title, "content": s.content} for s in self.sections
            ],
            "summary": self.summary,
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata,
        }

    def render(self) -> str:
        """Render report as string."""
        if self.format == ReportFormat.MARKDOWN:
            return self._render_markdown()
        elif self.format == ReportFormat.HTML:
            return self._render_html()
        elif self.format == ReportFormat.JSON:
            import json

            return json.dumps(self.to_dict(), indent=2)
        else:
            return self._render_text()

    def _render_markdown(self) -> str:
        """Render as Markdown."""
        lines = [f"# {self.title}", "", self.summary, ""]
        for section in sorted(self.sections, key=lambda s: -s.priority):
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
        lines.append(f"---\n*Generated: {self.generated_at.isoformat()}*")
        return "\n".join(lines)

    def _render_html(self) -> str:
        """Render as HTML."""
        sections_html = ""
        for section in sorted(self.sections, key=lambda s: -s.priority):
            sections_html += (
                f"<section><h2>{section.title}</h2>{section.content}</section>"
            )
        return f"""<!DOCTYPE html>
<html><head><title>{self.title}</title>
<style>body{{font-family:system-ui;max-width:900px;margin:0 auto;padding:20px}}
h1{{color:#c00}}h2{{border-bottom:1px solid #ddd}}
.critical{{color:#c00}}.high{{color:#e67300}}.medium{{color:#cc0}}.low{{color:#090}}</style>
</head><body><h1>{self.title}</h1><p>{self.summary}</p>{sections_html}
<footer>Generated: {self.generated_at.isoformat()}</footer></body></html>"""

    def _render_text(self) -> str:
        """Render as plain text."""
        lines = [self.title, "=" * len(self.title), "", self.summary, ""]
        for section in sorted(self.sections, key=lambda s: -s.priority):
            lines.append(section.title)
            lines.append("-" * len(section.title))
            lines.append(section.content)
            lines.append("")
        return "\n".join(lines)


# =============================================================================
# Reporter Agent
# =============================================================================


class CVEReporterAgent:
    """Agent for generating CVE reports.

    Generates structured reports in multiple formats with
    customizable sections and LLM-enhanced summaries.

    Example:
        ```python
        reporter = CVEReporterAgent()
        report = await reporter.generate_report(
            cves, format=ReportFormat.MARKDOWN
        )
        print(report.render())
        ```
    """

    name = "cve-reporter"

    def __init__(
        self,
        config: Optional[CVEHunterConfig] = None,
        llm_service: Optional[LLMServiceProtocol] = None,
    ):
        """Initialize reporter agent.

        Args:
            config: CVE Hunter configuration
            llm_service: LLM service for summary generation
        """
        self.config = config or get_cve_hunter_config()
        self._llm_service = llm_service

    async def _get_llm(self) -> LLMServiceProtocol:
        """Get LLM service from DI container."""
        if self._llm_service is None:
            self._llm_service = ServiceRegistry.get(LLMServiceProtocol)
        return self._llm_service

    # =========================================================================
    # Report Generation
    # =========================================================================

    async def generate_report(
        self,
        cves: List[CVERecord],
        title: Optional[str] = None,
        format: ReportFormat = ReportFormat.MARKDOWN,
        include_summary: bool = True,
        alerts: Optional[List[VulnerabilityAlert]] = None,
    ) -> CVEReport:
        """Generate a comprehensive CVE report.

        Args:
            cves: List of CVEs to include
            title: Report title
            format: Output format
            include_summary: Whether to generate LLM summary
            alerts: Optional alerts to include

        Returns:
            Generated report
        """
        from uuid import uuid4

        report_id = str(uuid4())
        title = (
            title or f"CVE Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        )

        sections = []

        # Executive summary
        if include_summary and cves:
            summary_section = await self._generate_executive_summary(cves)
            sections.append(summary_section)

        # Statistics section
        stats_section = self._generate_statistics_section(cves)
        sections.append(stats_section)

        # Critical CVEs section
        critical_cves = [c for c in cves if c.severity == CVESeverity.CRITICAL]
        if critical_cves:
            sections.append(
                self._generate_cve_section(
                    "Critical Vulnerabilities", critical_cves, priority=100
                )
            )

        # High CVEs section
        high_cves = [c for c in cves if c.severity == CVESeverity.HIGH]
        if high_cves:
            sections.append(
                self._generate_cve_section(
                    "High Severity Vulnerabilities", high_cves, priority=80
                )
            )

        # Alerts section
        if alerts:
            sections.append(self._generate_alerts_section(alerts))

        # All CVEs table
        sections.append(self._generate_cve_table(cves))

        summary = f"Report covering {len(cves)} CVEs"
        if critical_cves:
            summary += f" ({len(critical_cves)} critical)"

        return CVEReport(
            report_id=report_id,
            title=title,
            format=format,
            sections=sections,
            summary=summary,
            generated_at=datetime.now(timezone.utc),
            metadata={"cve_count": len(cves)},
        )

    async def generate_alert_report(
        self,
        alerts: List[VulnerabilityAlert],
        format: ReportFormat = ReportFormat.MARKDOWN,
    ) -> CVEReport:
        """Generate alert-focused report.

        Args:
            alerts: Alerts to report
            format: Output format

        Returns:
            Generated report
        """
        from uuid import uuid4

        sections = [self._generate_alerts_section(alerts)]

        return CVEReport(
            report_id=str(uuid4()),
            title=f"Security Alerts - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            format=format,
            sections=sections,
            summary=f"{len(alerts)} active security alerts",
            generated_at=datetime.now(timezone.utc),
        )

    # =========================================================================
    # Section Generators
    # =========================================================================

    async def _generate_executive_summary(self, cves: List[CVERecord]) -> ReportSection:
        """Generate LLM-powered executive summary."""
        try:
            llm = await self._get_llm()

            cve_list = "\n".join(
                [
                    f"- {c.cve_id}: {c.severity.value.upper()} ({c.cvss_score}) - {c.description[:100]}"
                    for c in cves[:20]
                ]
            )

            prompt = f"""Write a brief executive summary for this security report.
Highlight the most critical issues and recommended actions.

CVEs found: {len(cves)}
Critical: {sum(1 for c in cves if c.severity == CVESeverity.CRITICAL)}
High: {sum(1 for c in cves if c.severity == CVESeverity.HIGH)}

Top CVEs:
{cve_list}

Keep the summary under 200 words, professional tone."""

            summary = await llm.generate_response(prompt=prompt)

            return ReportSection(
                title="Executive Summary",
                content=summary,
                priority=200,
            )

        except Exception as e:
            logger.warning(f"Failed to generate executive summary: {e}")
            return ReportSection(
                title="Executive Summary",
                content=f"This report covers {len(cves)} vulnerabilities requiring attention.",
                priority=200,
            )

    def _generate_statistics_section(self, cves: List[CVERecord]) -> ReportSection:
        """Generate statistics section."""
        stats = {
            "total": len(cves),
            "critical": sum(1 for c in cves if c.severity == CVESeverity.CRITICAL),
            "high": sum(1 for c in cves if c.severity == CVESeverity.HIGH),
            "medium": sum(1 for c in cves if c.severity == CVESeverity.MEDIUM),
            "low": sum(1 for c in cves if c.severity == CVESeverity.LOW),
            "with_exploit": sum(1 for c in cves if c.exploit_available),
            "patched": sum(1 for c in cves if c.patch_available),
        }

        content = f"""| Metric | Count |
|--------|-------|
| Total CVEs | {stats["total"]} |
| Critical | {stats["critical"]} |
| High | {stats["high"]} |
| Medium | {stats["medium"]} |
| Low | {stats["low"]} |
| Exploits Available | {stats["with_exploit"]} |
| Patches Available | {stats["patched"]} |"""

        return ReportSection(
            title="Statistics",
            content=content,
            priority=150,
            metadata=stats,
        )

    def _generate_cve_section(
        self, title: str, cves: List[CVERecord], priority: int = 50
    ) -> ReportSection:
        """Generate section for CVE list."""
        items = []
        for cve in cves[:10]:  # Limit to top 10
            items.append(f"""### {cve.cve_id}
- **Severity**: {cve.severity.value.upper()} ({cve.cvss_score})
- **Description**: {cve.description[:200]}...
- **Exploit Available**: {"Yes" if cve.exploit_available else "No"}
- **Patch Available**: {"Yes" if cve.patch_available else "No"}
""")

        return ReportSection(
            title=title,
            content="\n".join(items),
            priority=priority,
        )

    def _generate_alerts_section(
        self, alerts: List[VulnerabilityAlert]
    ) -> ReportSection:
        """Generate alerts section."""
        items = []
        for alert in alerts:
            items.append(
                f"- **{alert.cve.cve_id}**: {alert.alert_type} (Priority: {alert.priority})"
            )

        return ReportSection(
            title="Active Alerts",
            content="\n".join(items) if items else "No active alerts.",
            priority=120,
        )

    def _generate_cve_table(self, cves: List[CVERecord]) -> ReportSection:
        """Generate CVE summary table."""
        rows = [
            "| CVE ID | Severity | CVSS | Exploit | Patch |",
            "|--------|----------|------|---------|-------|",
        ]

        for cve in cves[:50]:  # Limit to 50
            rows.append(
                f"| {cve.cve_id} | {cve.severity.value} | {cve.cvss_score} | "
                f"{'✓' if cve.exploit_available else '✗'} | {'✓' if cve.patch_available else '✗'} |"
            )

        return ReportSection(
            title="CVE Summary Table",
            content="\n".join(rows),
            priority=30,
        )
