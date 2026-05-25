"""Modular LLM Report Generation Service.

Refactored service using separate generator modules for maintainability.
"""

from core.observability.logging import get_logger
from typing import Optional, List, TYPE_CHECKING

from core.services.llm.service import LLMService

from ..models import (
    ThreatSummary,
    ReportConfig,
    AttackTimelineEntry,
    GeoDistribution,
    BotnetSummary,
    VulnerabilityItem,
    IOCEntry,
)

from .generators import ExecutiveSummaryGenerator, ThreatAnalysisGenerator

if TYPE_CHECKING:
    from .generators import RecommendationsGenerator, IOCAnalyzer

logger = get_logger(__name__)


class ModularReportLLMService:
    """Modular LLM-powered report generation service.

    Uses separate generator modules for each report section,
    improving maintainability and testability.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialize modular LLM report service.

        Args:
            llm_service: Optional LLMService instance
        """
        self._llm_service = llm_service
        self._executive_generator: Optional[ExecutiveSummaryGenerator] = None
        self._threat_generator: Optional[ThreatAnalysisGenerator] = None

    async def _get_llm(self) -> LLMService:
        """Lazy-load LLM service.

        Supports multiple env var patterns for compatibility:
        - HONEYPOT_REPORT_LLM_PROVIDER/MODEL (new standard)
        - LLM_REPORTS_PROVIDER/MODEL/API_KEY (legacy)
        Falls back to default LLM config if none specified.
        """
        if self._llm_service is None:
            import os
            from core.config.services import LLMConfig

            # Check for report-specific LLM configuration (multiple patterns)
            report_provider = os.getenv("HONEYPOT_REPORT_LLM_PROVIDER") or os.getenv(
                "LLM_REPORTS_PROVIDER"
            )
            report_model = os.getenv("HONEYPOT_REPORT_LLM_MODEL") or os.getenv(
                "LLM_REPORTS_MODEL"
            )
            report_api_key = os.getenv("HONEYPOT_REPORT_LLM_API_KEY") or os.getenv(
                "LLM_REPORTS_API_KEY"
            )

            if report_provider and report_model:
                # Use report-specific configuration
                logger.info(
                    f"Using report-specific LLM: {report_provider}/{report_model}"
                )

                # Create custom LLM config with report-specific settings
                custom_config = LLMConfig(
                    provider=report_provider,
                    model=report_model,
                    api_key=report_api_key or os.getenv("OPENAI_API_KEY"),
                )
                self._llm_service = LLMService(config=custom_config)
            else:
                # Use default LLM configuration
                self._llm_service = LLMService()
                logger.info(
                    "LLM service created for report generation (using default config)"
                )
        return self._llm_service

    async def _get_executive_generator(self) -> ExecutiveSummaryGenerator:
        """Lazy-load executive summary generator."""
        if self._executive_generator is None:
            llm = await self._get_llm()
            self._executive_generator = ExecutiveSummaryGenerator(llm)
        return self._executive_generator

    async def _get_threat_generator(self) -> ThreatAnalysisGenerator:
        """Lazy-load threat analysis generator."""
        if self._threat_generator is None:
            llm = await self._get_llm()
            self._threat_generator = ThreatAnalysisGenerator(llm)
        return self._threat_generator

    async def _get_recommendations_generator(self) -> "RecommendationsGenerator":
        """Lazy-load recommendations generator."""
        if not hasattr(self, "_recommendations_generator"):
            self._recommendations_generator = None
        if self._recommendations_generator is None:
            from .generators import RecommendationsGenerator

            llm = await self._get_llm()
            self._recommendations_generator = RecommendationsGenerator(llm)
        return self._recommendations_generator

    async def _get_ioc_analyzer(self) -> "IOCAnalyzer":
        """Lazy-load IOC analyzer."""
        if not hasattr(self, "_ioc_analyzer"):
            self._ioc_analyzer = None
        if self._ioc_analyzer is None:
            from .generators import IOCAnalyzer

            llm = await self._get_llm()
            self._ioc_analyzer = IOCAnalyzer(llm)
        return self._ioc_analyzer

    async def generate_executive_summary(
        self,
        threat_summary: ThreatSummary,
        config: ReportConfig,
        title: Optional[str] = None,
        timeline: Optional[List[AttackTimelineEntry]] = None,
        geo_data: Optional[List[GeoDistribution]] = None,
        honeypot_context: Optional[dict] = None,
        payload_samples: Optional[list] = None,
    ) -> str:
        """Generate executive summary.

        Args:
            threat_summary: Aggregated threat statistics
            config: Report configuration
            title: Optional custom title
            timeline: Optional attack timeline data
            geo_data: Optional geographic distribution data
            honeypot_context: Optional honeypot metadata
            payload_samples: Optional payload samples for attack analysis

        Returns:
            Executive summary in markdown format
        """
        generator = await self._get_executive_generator()
        return await generator.generate(
            threat_summary,
            config,
            title,
            timeline,
            geo_data,
            honeypot_context,
            payload_samples,
        )

    async def generate_threat_analysis(
        self,
        threat_summary: ThreatSummary,
        timeline: List[AttackTimelineEntry],
        geo_data: List[GeoDistribution],
        botnet_data: List[BotnetSummary],
    ) -> str:
        """Generate threat landscape analysis.

        Args:
            threat_summary: Aggregated threat statistics
            timeline: Attack timeline entries
            geo_data: Geographic distribution
            botnet_data: Botnet activity summaries

        Returns:
            Threat analysis in markdown format
        """
        generator = await self._get_threat_generator()
        return await generator.generate(threat_summary, timeline, geo_data, botnet_data)

    async def generate_recommendations(
        self,
        threat_summary: ThreatSummary,
        vulnerabilities: List[VulnerabilityItem],
        botnet_data: List[BotnetSummary],
    ) -> List[str]:
        """Generate security recommendations.

        Args:
            threat_summary: Aggregated threat statistics
            vulnerabilities: List of vulnerabilities
            botnet_data: Botnet summaries

        Returns:
            List of recommendation strings
        """
        generator = await self._get_recommendations_generator()
        return await generator.generate(threat_summary, vulnerabilities, botnet_data)

    async def generate_ioc_analysis(
        self,
        iocs: List[IOCEntry],
        threat_summary: ThreatSummary,
    ) -> str:
        """Generate IOC analysis.

        Args:
            iocs: List of IOC entries
            threat_summary: Threat statistics

        Returns:
            IOC analysis in markdown format
        """
        analyzer = await self._get_ioc_analyzer()
        return await analyzer.generate(iocs, threat_summary)
