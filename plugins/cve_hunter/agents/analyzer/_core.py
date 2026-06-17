"""CVE Analyzer Agent — core class definition.

Contains: class declaration, __init__, lazy loaders (_get_llm, _get_corrector,
_get_experience), and the primary analysis methods (analyze_cve, summarize_batch).
"""

import asyncio
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.observability.logging import get_logger
from core.di import ServiceRegistry
from core.interfaces import LLMServiceProtocol

try:
    from ...config import CVEHunterConfig, get_cve_hunter_config
    from ...models import CVERecord
except ImportError:
    from config import CVEHunterConfig, get_cve_hunter_config  # type: ignore[no-redef]
    from models import CVERecord  # type: ignore[no-redef]

from ._helpers import (
    build_analysis_prompt,
    get_system_prompt,
    calculate_priority_score,
    correlate_cves,
    record_experience,
    emit_analysis_event,
)
from ._analysis import AnalysisMethods

if TYPE_CHECKING:
    from core.reasoning.self_correction import SelfCorrector
    from core.learning import ExperienceReplay

logger = get_logger(__name__)


class CVEAnalyzerAgent(AnalysisMethods):
    """Agent for AI-powered CVE analysis.

    Uses LLM to generate summaries, assess impact, and
    identify related vulnerabilities.

    Example:
        ```python
        agent = CVEAnalyzerAgent()
        analysis = await agent.analyze_cve(cve_record)
        print(analysis["summary"])
        ```
    """

    name = "cve-analyzer"

    def __init__(
        self,
        config: Optional[CVEHunterConfig] = None,
        llm_service: Optional[LLMServiceProtocol] = None,
        self_corrector: Optional["SelfCorrector"] = None,
        experience_replay: Optional["ExperienceReplay"] = None,
    ):
        """Initialize analyzer agent.

        Args:
            config: CVE Hunter configuration
            llm_service: LLM service for AI analysis (injected or from DI)
            self_corrector: Optional SelfCorrector for analysis validation
            experience_replay: Optional ExperienceReplay for learning
        """
        self.config = config or get_cve_hunter_config()
        self._llm_service = llm_service
        self._corrector = self_corrector
        self._experience = experience_replay
        self._corrector_initialized = False
        self._experience_initialized = False

    async def _get_llm(self) -> LLMServiceProtocol:
        """Get LLM service from DI container."""
        if self._llm_service is None:
            service_or_factory = ServiceRegistry.get(LLMServiceProtocol)

            if asyncio.iscoroutinefunction(service_or_factory) or (
                callable(service_or_factory)
                and not isinstance(service_or_factory, type)
            ):
                if asyncio.iscoroutinefunction(service_or_factory):
                    self._llm_service = await service_or_factory()
                else:
                    result = service_or_factory()
                    if asyncio.iscoroutine(result):
                        self._llm_service = await result
                    else:
                        self._llm_service = result
            else:
                self._llm_service = service_or_factory

        return self._llm_service

    def _get_corrector(self) -> Optional["SelfCorrector"]:
        """Lazy-load SelfCorrector."""
        if self._corrector is None and not self._corrector_initialized:
            self._corrector_initialized = True
            if self.config.enable_self_correction:
                try:
                    from core.reasoning.self_correction import SelfCorrector

                    self._corrector = SelfCorrector(
                        max_corrections=self.config.max_correction_iterations
                    )
                    logger.debug("SelfCorrector initialized for CVE analysis")
                except ImportError:
                    logger.debug("SelfCorrector not available")
        return self._corrector

    def _get_experience(self) -> Optional["ExperienceReplay"]:
        """Lazy-load ExperienceReplay."""
        if self._experience is None and not self._experience_initialized:
            self._experience_initialized = True
            if self.config.enable_learning:
                try:
                    from core.learning import ExperienceReplay

                    self._experience = ExperienceReplay(
                        capacity=self.config.experience_buffer_size,
                        prioritized=True,
                        priority_alpha=self.config.learning_priority_alpha,
                    )
                    logger.debug("ExperienceReplay initialized for CVE analysis")
                except ImportError:
                    logger.debug("ExperienceReplay not available")
        return self._experience

    async def analyze_cve(self, cve: CVERecord) -> Dict[str, Any]:
        """Analyze a single CVE with AI.

        Uses SelfCorrector to validate and improve the analysis.
        Records experience for continuous learning.

        Args:
            cve: CVE record to analyze

        Returns:
            Analysis dict with summary, impact, recommendations
        """
        llm = await self._get_llm()

        prompt = build_analysis_prompt(cve)
        full_prompt = f"{get_system_prompt()}\n\n{prompt}"

        analysis_result: Dict[str, Any] = {
            "cve_id": cve.cve_id,
            "severity": cve.severity.value,
            "cvss_score": cve.cvss_score,
            "analyzed": False,
        }

        try:
            response = await llm.generate_response(prompt=full_prompt)

            corrector = self._get_corrector()
            if corrector and response:
                try:
                    correction_result = await corrector.correct(
                        response=response,
                        context=f"CVE: {cve.cve_id}, Severity: {cve.severity.value}",
                    )
                    response = correction_result.corrected
                    analysis_result["corrections_made"] = (
                        correction_result.corrections_made
                    )
                    logger.debug(
                        f"Analysis corrected {correction_result.corrections_made} times"
                    )
                except Exception as e:
                    logger.debug(f"Self-correction failed: {e}")

            analysis_result["ai_summary"] = response
            analysis_result["analyzed"] = True

            experience = self._get_experience()
            if experience:
                record_experience(
                    experience=experience,
                    cve_id=cve.cve_id,
                    action="analyze",
                    success=True,
                    severity=cve.severity.value,
                )

            await emit_analysis_event(cve, analysis_result)

            return analysis_result

        except Exception as e:
            logger.error(f"Analysis failed for {cve.cve_id}: {e}")

            experience = self._get_experience()
            if experience:
                record_experience(
                    experience=experience,
                    cve_id=cve.cve_id,
                    action="analyze",
                    success=False,
                    severity=cve.severity.value,
                )

            analysis_result["ai_summary"] = None
            analysis_result["error"] = str(e)
            return analysis_result

    async def summarize_batch(
        self,
        cves: List[CVERecord],
        max_items: int = 10,
    ) -> str:
        """Generate summary of multiple CVEs.

        Args:
            cves: List of CVE records
            max_items: Maximum items to include

        Returns:
            Summary text
        """
        llm = await self._get_llm()

        sorted_cves = sorted(cves, key=lambda c: c.cvss_score, reverse=True)[:max_items]

        cve_list = "\n".join(
            f"- {c.cve_id}: {c.severity.value.upper()} (CVSS {c.cvss_score}) - "
            f"{c.description[:100]}..."
            for c in sorted_cves
        )

        prompt = f"""Provide a brief security briefing summary of these {len(sorted_cves)} vulnerabilities:

{cve_list}

Include:
1. Most critical items requiring immediate attention
2. Common themes or affected systems
3. Overall risk assessment
"""

        full_prompt = (
            f"You are a security analyst providing vulnerability briefings.\n\n{prompt}"
        )

        try:
            response = await llm.generate_response(prompt=full_prompt)
            return response
        except Exception as e:
            logger.error(f"Batch summary failed: {e}")
            return f"Summary generation failed: {e}"

    def calculate_priority_score(self, cve: CVERecord) -> int:
        """Calculate priority score for a CVE (1-5, 1 is highest).

        Args:
            cve: CVE record

        Returns:
            Priority score
        """
        return calculate_priority_score(cve)

    async def correlate_cves(self, cves: List[CVERecord]) -> List[List[str]]:
        """Find related CVEs in a list.

        Args:
            cves: List of CVE records

        Returns:
            List of related CVE ID groups
        """
        return correlate_cves(cves)
