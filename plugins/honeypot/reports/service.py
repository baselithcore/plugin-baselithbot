"""Report Generation Service.

Generates comprehensive cybersecurity reports from honeypot data.
Now modularized into Aggregator, Generator, Renderer,  LLM service,
Orchestration, and Section Generators.
"""

from core.observability.logging import get_logger
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .aggregator import ReportDataAggregator
from .generator import ReportTextGenerator
from .llm import ModularReportLLMService
from .models import (
    ReportConfig,
    ReportMetadata,
    ReportSection,
    ReportType,
    SecurityReport,
)
from .orchestration import gather_enrichment_data, gather_section_data
from .renderer import ReportRenderer
from .section_generators import (
    generate_executive_summary_section,
    generate_recommendations_section,
    generate_research_sections,
)

logger = get_logger(__name__)


class ReportService:
    """Service for generating security reports from honeypot data.

    Supports both template-based and LLM-enhanced report generation.
    """

    def __init__(self, dao=None, use_llm: bool = True):
        """Initialize report service.

        Args:
            dao: HoneypotDAO instance for data access
            use_llm: Whether to use LLM for enhanced report generation (default: True)
                     Can be overridden by HONEYPOT_REPORTS_USE_LLM env var
        """
        import os

        self._dao = dao
        self._aggregator: Optional[ReportDataAggregator] = None
        self._generator = ReportTextGenerator()
        self._renderer = ReportRenderer()

        # Allow environment variable to override use_llm
        env_use_llm = os.getenv("HONEYPOT_REPORTS_USE_LLM", "").lower()
        if env_use_llm in ("false", "0", "no"):
            self._use_llm = False
            logger.info(
                "LLM disabled via HONEYPOT_REPORTS_USE_LLM environment variable"
            )
        else:
            self._use_llm = use_llm

        self._llm_service: Optional[ModularReportLLMService] = None

        # Log LLM status
        if self._use_llm:
            logger.info(
                "ReportService initialized with LLM-enhanced generation enabled"
            )
        else:
            logger.info("ReportService initialized with template-based generation only")

    @property
    def dao(self):
        """Lazy-load DAO if not provided."""
        if self._dao is None:
            from ..persistence import HoneypotDAO

            self._dao = HoneypotDAO()
        return self._dao

    @property
    def aggregator(self) -> ReportDataAggregator:
        """Lazy-load aggregator."""
        if self._aggregator is None:
            self._aggregator = ReportDataAggregator(self.dao)
        return self._aggregator

    @property
    def llm_service(self) -> Optional[ModularReportLLMService]:
        """Lazy-load LLM service if enabled."""
        if self._use_llm and self._llm_service is None:
            try:
                self._llm_service = ModularReportLLMService()
                logger.info("Modular LLM service initialized successfully")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize LLM service: {e}. Falling back to templates."
                )
                self._use_llm = False
        return self._llm_service

    async def generate_report(
        self,
        config: ReportConfig,
        title: Optional[str] = None,
    ) -> SecurityReport:
        """Generate a security report based on configuration.

        Args:
            config: Report configuration
            title: Optional custom title

        Returns:
            SecurityReport with all requested sections populated
        """
        report_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc)
        time_range_start = now - timedelta(hours=config.time_range_hours)

        # Build metadata
        metadata = ReportMetadata(
            report_id=report_id,
            generated_at=now,
            report_type=config.report_type,
            classification=config.classification,
            time_range_start=time_range_start,
            time_range_end=now,
            honeypot_filter=config.honeypot_id,
            organization=config.organization_name,
        )

        # Prepare honeypot context if a specific honeypot is selected
        honeypot_context = None
        payload_samples = []
        if config.honeypot_id:
            # Get enhanced honeypot context
            honeypot_context = await self.aggregator.get_enhanced_honeypot_context(
                config.honeypot_id
            )

            # Extract payload samples for detailed analysis
            payload_samples = await self.aggregator.extract_payload_samples(
                honeypot_id=config.honeypot_id,
                time_start=time_range_start,
                max_samples=10,
            )

            # Auto-generate title if missing
            if not title and honeypot_context:
                title = f"{honeypot_context['name']} Threat Analysis Report"

        # Gather data based on requested sections
        threat_summary = await self.aggregator.build_threat_summary(
            config.honeypot_id, time_range_start
        )

        report = SecurityReport(
            metadata=metadata,
            threat_summary=threat_summary,
        )

        # Gather data for all sections in PARALLEL (major performance optimization)
        (
            timeline,
            geo_distribution,
            botnet_activity,
            pentest_results,
            vulnerabilities,
            iocs,
        ) = await gather_section_data(self.aggregator, config, time_range_start)

        # Gather enrichment data in parallel
        (
            discovery_enrichment,
            correlations,
            misp_status,
            threat_intel_summary,
            payload_excerpts,
            credential_analysis,
            sequential_analysis,  # NEW
        ) = await gather_enrichment_data(self.aggregator, config)

        # Assign results to report
        if ReportSection.TIMELINE in config.sections:
            report.attack_timeline = timeline
        if ReportSection.GEO_ANALYSIS in config.sections:
            report.geo_distribution = geo_distribution
        if ReportSection.BOTNET_DISCOVERY in config.sections:
            report.botnet_activity = botnet_activity
        if ReportSection.PENTEST_RESULTS in config.sections:
            report.pentest_results = pentest_results
            report.vulnerabilities = vulnerabilities
        if ReportSection.IOC_LIST in config.sections:
            report.iocs = iocs

        # Assign enrichment data (always included when available)
        report.discovery_enrichment = discovery_enrichment
        report.correlations = correlations
        report.misp_status = misp_status
        report.threat_intel_summary = threat_intel_summary
        report.payload_excerpts = payload_excerpts
        report.credential_analysis = credential_analysis

        # Process Sequential Analysis (with LLM Narrative Generation)
        if sequential_analysis and self._use_llm and self.llm_service:
            from .llm.generators import ResearchReportGenerator

            # Use existing LLM service
            research_gen = ResearchReportGenerator(self.llm_service)

            # Generate narratives for each session in parallel
            narrative_tasks = []
            for session in sequential_analysis:
                narrative_tasks.append(research_gen.generate_attack_narrative(session))

            narratives = await asyncio.gather(*narrative_tasks, return_exceptions=True)

            for i, narrative in enumerate(narratives):
                if isinstance(narrative, str):
                    sequential_analysis[i].narrative = narrative

        report.sequential_analysis = sequential_analysis

        # Generate text sections with LLM or templates
        if ReportSection.EXECUTIVE_SUMMARY in config.sections:
            report.executive_summary = await generate_executive_summary_section(
                self.llm_service,
                self._generator,
                self._use_llm,
                threat_summary,
                config,
                title,
                timeline,
                geo_distribution,
                honeypot_context,
                payload_samples,
            )

        if (
            ReportSection.THREAT_LANDSCAPE in config.sections
            and self._use_llm
            and self.llm_service
        ):
            # Generate LLM-enhanced threat landscape analysis
            try:
                threat_analysis = await self.llm_service.generate_threat_analysis(
                    threat_summary,
                    report.attack_timeline or [],
                    report.geo_distribution or [],
                    report.botnet_activity or [],
                )
                # Add to executive summary or raw data
                if report.executive_summary:
                    report.executive_summary += f"\\n\\n{threat_analysis}"
                else:
                    report.executive_summary = threat_analysis
            except Exception as e:
                logger.warning(f"LLM threat analysis failed: {e}")

        if ReportSection.RECOMMENDATIONS in config.sections:
            report.recommendations = await generate_recommendations_section(
                self.llm_service,
                self._generator,
                self._use_llm,
                threat_summary,
                report,
            )

        # RESEARCH REPORT SECTIONS (Enterprise-Grade Threat Intelligence)
        if (
            config.report_type == ReportType.RESEARCH
            and self._use_llm
            and self.llm_service
        ):
            await generate_research_sections(
                report=report,
                config=config,
                threat_summary=threat_summary,
                timeline=timeline,
                geo_distribution=geo_distribution,
                honeypot_context=honeypot_context,
            )

        return report

    def render_markdown(self, report: SecurityReport) -> str:
        """Render report as Markdown document."""
        return self._renderer.render_markdown(report)
