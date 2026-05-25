"""Data Analysis Manager for Honeypot Plugin.

Implements analysis orchestration per HoneyDOC Section III-B3.
Integrates pattern analysis, CVE correlation, and LLM-based analysis.

Purpose (from paper):
- Analyze collected data to reveal attack technique and motivation
- Integrate third-party analysis services
- Support comprehensive forensics by experts or automated programs
"""

from core.observability.logging import get_logger
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..models import AttackCategory, AttackEvent, AttackSeverity

logger = get_logger(__name__)


class AnalysisType(str, Enum):
    """Types of analysis available."""

    PATTERN = "pattern"  # Signature-based pattern matching
    LLM = "llm"  # LLM-based deep analysis
    CVE = "cve"  # CVE/CWE correlation
    CTI = "cti"  # Cyber Threat Intelligence (future)


@dataclass
class AnalysisResult:
    """Result of attack analysis."""

    event_id: str
    analysis_types: List[AnalysisType]
    category: AttackCategory
    severity: AttackSeverity
    confidence: float
    patterns_detected: List[str]
    matched_cwes: List[str]
    matched_cves: List[str]
    llm_summary: Optional[str]
    recommendations: List[str]
    analyzed_at: datetime


class DataAnalysisManager:
    """Analysis orchestrator following HoneyDOC Captor design.

    Coordinates multiple analysis backends:
    - PatternAnalyzer for signature-based detection
    - CVECorrelator for vulnerability mapping
    - LLMResponder for intent analysis
    """

    def __init__(self):
        """Initialize analysis manager."""
        self._pattern_analyzer = None
        self._cve_correlator = None
        self._llm_responder = None
        self._initialized = False

        # Analysis cache to avoid redundant processing
        self._analysis_cache: Dict[str, AnalysisResult] = {}
        self._cache_max_size = 1000

        logger.info("DataAnalysisManager initialized")

    async def initialize(self) -> bool:
        """Initialize analysis backends.

        Returns:
            True if at least one backend initialized
        """
        if self._initialized:
            return True

        initialized_any = False

        try:
            from ..agents.pattern_analyzer import PatternAnalyzer

            self._pattern_analyzer = PatternAnalyzer()
            if await self._pattern_analyzer.initialize():
                initialized_any = True
                logger.info("PatternAnalyzer initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize PatternAnalyzer: {e}")

        try:
            from ..agents.correlator import HoneypotCVECorrelator

            self._cve_correlator = HoneypotCVECorrelator()
            await self._cve_correlator.initialize()
            initialized_any = True
            logger.info("CVECorrelator initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize CVECorrelator: {e}")

        try:
            from ..agents.responder import LLMResponder

            self._llm_responder = LLMResponder()
            if await self._llm_responder.initialize():
                initialized_any = True
                logger.info("LLMResponder initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize LLMResponder: {e}")

        self._initialized = initialized_any
        return initialized_any

    async def analyze_event(
        self,
        event: AttackEvent,
        payload: Optional[str] = None,
        analysis_types: Optional[List[AnalysisType]] = None,
        honeypot_tags: Optional[List[str]] = None,
    ) -> AnalysisResult:
        """Analyze an attack event.

        Args:
            event: Attack event to analyze
            payload: Optional raw payload for deep analysis
            analysis_types: Specific analysis types to run (default: all)
            honeypot_tags: Optional tags from honeypot config

        Returns:
            Comprehensive analysis result
        """
        # Check cache
        if event.event_id in self._analysis_cache:
            return self._analysis_cache[event.event_id]

        if analysis_types is None:
            analysis_types = [AnalysisType.PATTERN, AnalysisType.CVE, AnalysisType.LLM]

        patterns_detected: List[str] = list(event.patterns_detected)
        matched_cwes: List[str] = list(event.matched_cwes)
        matched_cves: List[str] = list(event.matched_cves)
        llm_summary: Optional[str] = None
        recommendations: List[str] = []

        # Pattern analysis
        if AnalysisType.PATTERN in analysis_types and self._pattern_analyzer:
            try:
                analysis_payload = payload or event.raw_payload or ""
                result = await self._pattern_analyzer.analyze_payload(
                    payload=analysis_payload,
                    protocol=event.protocol.value,
                    source_ip=event.source_ip,
                )
                if result.get("matched_signature"):
                    patterns_detected.append(result["matched_signature"])
            except Exception as e:
                logger.warning(f"Pattern analysis failed: {e}")

        # CVE correlation
        if AnalysisType.CVE in analysis_types and self._cve_correlator:
            try:
                correlation = await self._async_correlate(
                    event_id=event.event_id,
                    category=event.category.value,
                    patterns=patterns_detected,
                    source_ip=event.source_ip,
                    honeypot_tags=honeypot_tags,
                )
                if correlation:
                    matched_cwes.extend(correlation.get("cwes", []))
                    matched_cves.extend(correlation.get("cves", []))
            except Exception as e:
                logger.warning(f"CVE correlation failed: {e}")

        # LLM analysis
        if AnalysisType.LLM in analysis_types and self._llm_responder:
            try:
                analysis_payload = payload or event.raw_payload or ""
                if analysis_payload:
                    intent_result = await self._llm_responder.analyze_attack_intent(
                        payload=analysis_payload,
                        protocol=event.protocol.value,
                    )
                    llm_summary = intent_result.get("summary")
                    if intent_result.get("recommendations"):
                        recommendations.extend(intent_result["recommendations"])
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}")

        # Build result
        result = AnalysisResult(
            event_id=event.event_id,
            analysis_types=analysis_types,
            category=event.category,
            severity=event.severity,
            confidence=self._calculate_confidence(
                patterns_detected, matched_cwes, llm_summary
            ),
            patterns_detected=list(set(patterns_detected)),
            matched_cwes=list(set(matched_cwes)),
            matched_cves=list(set(matched_cves)),
            llm_summary=llm_summary,
            recommendations=recommendations,
            analyzed_at=datetime.now(timezone.utc),
        )

        # Cache result
        self._cache_result(event.event_id, result)

        return result

    async def _async_correlate(
        self,
        event_id: str,
        category: str,
        patterns: List[str],
        source_ip: str,
        honeypot_tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run CVE correlation async wrapper."""
        if not self._cve_correlator:
            return None

        try:
            result = await self._cve_correlator.correlate_attack(
                event_id=event_id,
                category=category,
                patterns=patterns,
                source_ip=source_ip,
                honeypot_tags=honeypot_tags,
            )
            return result
        except Exception as e:
            logger.warning(f"Correlation error: {e}")
            return None

    def _calculate_confidence(
        self,
        patterns: List[str],
        cwes: List[str],
        llm_summary: Optional[str],
    ) -> float:
        """Calculate overall analysis confidence.

        Args:
            patterns: Detected patterns
            cwes: Matched CWEs
            llm_summary: LLM analysis summary

        Returns:
            Confidence score 0.0-1.0
        """
        score = 0.3  # Base confidence

        # Pattern matches increase confidence
        if patterns:
            score += min(0.3, len(patterns) * 0.1)

        # CWE matches increase confidence
        if cwes:
            score += min(0.2, len(cwes) * 0.1)

        # LLM analysis increases confidence
        if llm_summary:
            score += 0.2

        return min(1.0, score)

    def _cache_result(self, event_id: str, result: AnalysisResult) -> None:
        """Cache analysis result.

        Args:
            event_id: Event identifier
            result: Analysis result to cache
        """
        self._analysis_cache[event_id] = result

        # Enforce cache size limit
        if len(self._analysis_cache) > self._cache_max_size:
            # Remove oldest entries
            oldest_keys = list(self._analysis_cache.keys())[
                : len(self._analysis_cache) - self._cache_max_size
            ]
            for key in oldest_keys:
                del self._analysis_cache[key]

    def get_cached_analysis(self, event_id: str) -> Optional[AnalysisResult]:
        """Get cached analysis result.

        Args:
            event_id: Event identifier

        Returns:
            Cached result or None
        """
        return self._analysis_cache.get(event_id)

    def clear_cache(self) -> None:
        """Clear analysis cache."""
        self._analysis_cache.clear()
        logger.info("Analysis cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get analysis statistics.

        Returns:
            Analysis statistics
        """
        return {
            "cache_size": len(self._analysis_cache),
            "pattern_analyzer_available": self._pattern_analyzer is not None,
            "cve_correlator_available": self._cve_correlator is not None,
            "llm_responder_available": self._llm_responder is not None,
            "initialized": self._initialized,
        }
