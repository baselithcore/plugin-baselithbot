"""Payload samples mixin for ReportDataAggregator."""

from datetime import datetime
from typing import Dict, List, Optional

from core.observability.logging import get_logger

logger = get_logger(__name__)


class PayloadSamplesMixin:
    """Mixin providing extract_payload_samples method."""

    async def extract_payload_samples(
        self,
        honeypot_id: Optional[str],
        time_start: datetime,
        max_samples: int = 10,
    ) -> List[Dict]:
        """Extract representative payload samples for attack analysis.

        Args:
            honeypot_id: Optional honeypot filter
            time_start: Start of time range
            max_samples: Maximum number of samples to return

        Returns:
            List of payload samples with context

        Security:
            All payloads are sanitized via sanitize_for_llm() to prevent
            prompt injection attacks before being passed to the LLM.
        """
        try:
            # Import sanitization function for security
            from ..security import sanitize_for_llm

            # Get high-severity events with payloads
            events, _ = await self.dao.get_events(
                honeypot_id=honeypot_id,
                page_size=100,
                severity="critical,high,medium",
            )

            payload_samples = []
            seen_patterns = set()  # Deduplicate similar attacks

            for event in events:
                if len(payload_samples) >= max_samples:
                    break

                raw_data = event.raw_data or ""
                category = (
                    event.category.value
                    if hasattr(event.category, "value")
                    else str(event.category) or "unknown"
                )

                # Skip if no meaningful payload
                if not raw_data or len(raw_data.strip()) < 5:
                    continue

                # Create a pattern signature for deduplication
                pattern_sig = f"{category}:{raw_data[:50]}"
                if pattern_sig in seen_patterns:
                    continue

                seen_patterns.add(pattern_sig)

                # SECURITY: Sanitize payload before including in LLM context
                # Truncate to 500 chars first, then sanitize
                sanitized_payload = sanitize_for_llm(
                    raw_data[:500],
                    max_length=500,
                    replacement="[FILTERED_INJECTION]",
                )

                # Extract payload with context
                payload_samples.append(
                    {
                        "category": category,
                        "severity": event.severity.value
                        if hasattr(event.severity, "value")
                        else str(event.severity) or "medium",
                        "payload": sanitized_payload,  # Use sanitized version
                        "source_ip": event.source_ip or "unknown",
                        "country": event.geo.country if event.geo else "Unknown",
                        "timestamp": event.timestamp,
                        "ai_classification": event.ai_classification or "",
                        "protocol": event.protocol.value
                        if hasattr(event.protocol, "value")
                        else str(event.protocol) or "unknown",
                        "honeypot_id": event.honeypot_id or "",
                    }
                )

            return payload_samples
        except Exception as e:
            logger = get_logger(__name__)
            logger.warning(f"Failed to extract payload samples: {e}")
            return []
