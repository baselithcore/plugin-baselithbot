"""ZerodayMixin — _suggest_from_zeroday method for HoneypotSuggestionEngine."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from core.observability.logging import get_logger

from ..zeroday_detector.models import ZeroDayCandidate
from .models import (
    HoneypotSuggestion,
    SuggestionType,
)
from .strategies import (
    calculate_priority,
    determine_protocol_from_vector,
    estimate_catch_rate,
    generate_detection_patterns,
    generate_rationale,
    generate_tags,
)
from .filters import (
    calculate_investigation_value,
    calculate_sophistication_level,
    generate_investigation_rationale,
    generate_descriptive_title,
    is_generic_pattern,
)

logger = get_logger(__name__)


class ZerodayMixin:
    """Mixin providing _suggest_from_zeroday for HoneypotSuggestionEngine."""

    def _suggest_from_zeroday(
        self, candidate: ZeroDayCandidate
    ) -> Optional[HoneypotSuggestion]:
        """Create suggestion from a zero-day candidate.

        Args:
            candidate: Zero-day candidate from detector

        Returns:
            HoneypotSuggestion if criteria met, None otherwise
        """
        # Check thresholds
        if candidate.novelty_score < self.MIN_NOVELTY_SCORE:  # type: ignore[attr-defined]
            return None
        if candidate.confidence < self.MIN_CONFIDENCE:  # type: ignore[attr-defined]
            return None
        if candidate.occurrence_count < self.MIN_OCCURRENCES:  # type: ignore[attr-defined]
            return None

        # Skip if pattern already seen
        if candidate.payload_hash in self._seen_fingerprints:  # type: ignore[attr-defined]
            return None
        self._seen_fingerprints.add(candidate.payload_hash)  # type: ignore[attr-defined]

        # Skip if too similar to existing honeypot
        if self._is_covered_by_existing(  # type: ignore[attr-defined]
            candidate.attack_vector, candidate.target_services
        ):
            return None

        # Determine protocol and port
        protocol, port = determine_protocol_from_vector(
            candidate.attack_vector, candidate.payload_preview
        )

        # Calculate priority
        priority = calculate_priority(
            candidate.novelty_score,
            candidate.confidence,
            candidate.occurrence_count,
        )

        # Generate detection patterns
        detection_patterns = generate_detection_patterns(
            candidate.payload_preview,
            candidate.attack_vector,
            candidate.indicators,
        )

        # Generate tags
        tags = generate_tags(
            candidate.attack_vector,
            candidate.indicators,
            [candidate.payload_hash],
        )

        # Generate descriptive title (avoid generic "Unknown Detector")
        title = generate_descriptive_title(
            candidate.attack_vector,
            candidate.target_services,
            detection_patterns,
            candidate.occurrence_count,
            len(candidate.source_ips),
        )

        # Skip if title would be too generic
        if is_generic_pattern(candidate.attack_vector, title):
            return None

        # Generate description
        description = (
            f"Honeypot designed to capture {candidate.attack_vector.replace('_', ' ')} attacks "
            f"similar to a novel pattern observed {candidate.occurrence_count} times from "
            f"{len(candidate.source_ips)} unique sources."
        )

        # Generate rationale
        rationale = generate_rationale(
            SuggestionType.ZERODAY_PATTERN,
            candidate.attack_vector,
            candidate.occurrence_count,
            len(candidate.source_ips),
            candidate.novelty_score,
        )

        # Estimate catch rate
        catch_rate = estimate_catch_rate(
            candidate.occurrence_count,
            len(candidate.source_ips),
            candidate.novelty_score,
        )

        # Calculate new metrics
        relevance_score = calculate_investigation_value(
            candidate.novelty_score,
            candidate.confidence,
            candidate.occurrence_count,
            len(candidate.source_ips),
            candidate.attack_vector,
            candidate.indicators,
        )

        sophistication_level = calculate_sophistication_level(
            candidate.attack_vector,
            candidate.indicators,
            detection_patterns,
        )

        investigation_rationale = generate_investigation_rationale(
            SuggestionType.ZERODAY_PATTERN.value,
            candidate.attack_vector,
            candidate.occurrence_count,
            len(candidate.source_ips),
            candidate.novelty_score,
            sophistication_level,
        )

        try:
            return HoneypotSuggestion(
                id=str(uuid.uuid4()),
                suggestion_type=SuggestionType.ZERODAY_PATTERN,
                confidence=candidate.confidence,
                priority=priority,
                title=title,
                description=description,
                rationale=rationale,
                suggested_protocol=protocol,
                suggested_port=port,
                detection_patterns=detection_patterns,
                tags=tags,
                source_anomaly_ids=[f"zeroday_{candidate.id[:8]}"],
                source_patterns=[candidate.payload_hash],
                source_ips=list(candidate.source_ips)[:10],
                estimated_catch_rate=catch_rate,
                occurrence_count=candidate.occurrence_count,
                relevance_score=relevance_score,
                sophistication_level=sophistication_level,
                investigation_rationale=investigation_rationale,
                created_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(
                f"Failed to create HoneypotSuggestion from zeroday: {e}, "
                f"confidence={candidate.confidence}, port={port}, protocol={protocol}"
            )
            return None
