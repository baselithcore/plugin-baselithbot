"""Bot Detection Service for Honeypot.

Analyzes behavioral signals to distinguish between human attackers
and automated bots/scripts using timing analysis, session patterns,
payload characteristics, and static fingerprints.
"""

from core.observability.logging import get_logger
import math
import statistics
import time
import re
from collections import defaultdict
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from ._bot_patterns import (
    BOT_USER_AGENTS,
    AUTOMATED_SCAN_PATTERNS,
    HIGH_BOT_THRESHOLD,
    LOW_BOT_THRESHOLD,
    MAX_TIMING_HISTORY,
)
from ._bot_models import BotDetectionSignals, BotDetectionResult

logger = get_logger(__name__)


class BotDetector:
    """
    Analyzes request patterns to detect automated bots vs human attackers.

    Uses multi-signal analysis combining static fingerprints and behavioral metrics.
    Optimized to detect both one-shot scanners (via static signals) and
    persistent bots (via behavioral signals).
    """

    # Weight for each signal in final score
    WEIGHTS = {
        # Static Signals (Total: 40%) - Available on first request
        "user_agent_score": 0.25,
        "payload_pattern_score": 0.15,
        # Behavioral/Temporal Signals (Total: 60%)
        "payload_entropy": 0.08,  # Available on first request
        "timing_variance": 0.18,  # Needs >= 3 requests
        "inter_request_interval": 0.14,  # Needs >= 2 requests
        "request_rate": 0.10,  # Needs >= 2 requests
        "pattern_repetition": 0.10,  # Needs >= 2 requests
    }

    def __init__(self):
        # Per-IP timing history: {ip: [timestamp_ms, ...]}
        self._ip_timestamps: Dict[str, List[float]] = defaultdict(list)
        # Per-IP session start: {ip: timestamp_ms}
        self._ip_session_start: Dict[str, float] = {}
        # Per-IP payload hashes: {ip: [hash, ...]}
        self._ip_payload_hashes: Dict[str, List[int]] = defaultdict(list)
        # Per-IP inter-request intervals: {ip: [interval_ms, ...]}
        self._ip_intervals: Dict[str, List[float]] = defaultdict(list)

    def record_request(self, source_ip: str, payload: str = "") -> None:
        """
        Record a request from an IP for timing analysis.

        Args:
            source_ip: Source IP address
            payload: Request payload/command
        """
        now_ms = time.time() * 1000

        # Initialize session if new IP
        if source_ip not in self._ip_session_start:
            self._ip_session_start[source_ip] = now_ms

        # Record timestamp
        timestamps = self._ip_timestamps[source_ip]
        if timestamps:
            # Calculate interval from last request
            interval_ms = now_ms - timestamps[-1]
            self._ip_intervals[source_ip].append(interval_ms)
            # Keep only recent intervals
            if len(self._ip_intervals[source_ip]) > MAX_TIMING_HISTORY:
                self._ip_intervals[source_ip] = self._ip_intervals[source_ip][
                    -MAX_TIMING_HISTORY:
                ]

        timestamps.append(now_ms)
        # Keep only recent timestamps
        if len(timestamps) > MAX_TIMING_HISTORY:
            self._ip_timestamps[source_ip] = timestamps[-MAX_TIMING_HISTORY:]

        # Record payload hash
        if payload:
            payload_hash = hash(payload)
            self._ip_payload_hashes[source_ip].append(payload_hash)
            if len(self._ip_payload_hashes[source_ip]) > MAX_TIMING_HISTORY:
                self._ip_payload_hashes[source_ip] = self._ip_payload_hashes[source_ip][
                    -MAX_TIMING_HISTORY:
                ]

    def analyze(
        self,
        source_ip: str,
        payload: str = "",
        user_agent: str = "",
        ja4_fingerprint: Optional[str] = None,
    ) -> BotDetectionResult:
        """
        Analyze if the source IP is a bot or human.

        Args:
            source_ip: Source IP to analyze
            payload: Current payload for entropy and pattern analysis
            user_agent: User-Agent header (optional)
            ja4_fingerprint: JA4+ fingerprint string (optional)

        Returns:
            BotDetectionResult with classification and confidence
        """
        signals = self._compute_signals(source_ip, payload, user_agent, ja4_fingerprint)

        # If we have absolutely no signals (should rarely happen given entropy/static), return unknown
        if not any(v is not None for v in asdict(signals).values()):
            return BotDetectionResult(
                is_bot=False,
                confidence=0.0,
                signals=signals,
                classification="unknown",
                reason="Insufficient data for analysis",
            )

        # Calculate bot probability for each signal
        scores: Dict[str, float] = {}
        reasons: List[str] = []

        # --- STATIC SIGNALS ANALYZER ---

        # 1. User-Agent Analysis
        if signals.user_agent_score is not None:
            scores["user_agent_score"] = signals.user_agent_score
            if signals.user_agent_score > 0.9:
                reasons.append("Bot-like User-Agent detected")
            elif signals.user_agent_score < 0.2:
                reasons.append("Browser-like User-Agent")

        # 2. Payload Pattern Analysis
        if signals.payload_pattern_score is not None:
            scores["payload_pattern_score"] = signals.payload_pattern_score
            if signals.payload_pattern_score > 0.8:
                reasons.append("Automated scanner pattern in payload")

        # --- BEHAVIORAL/TEMPORAL SIGNALS ANALYZER ---

        # 3. Timing Variance Analysis
        if signals.timing_variance is not None:
            if signals.timing_variance < 50:
                scores["timing_variance"] = 1.0
                reasons.append("Very consistent timing (bot-like)")
            elif signals.timing_variance < 200:
                scores["timing_variance"] = 0.8
            elif signals.timing_variance < 500:
                scores["timing_variance"] = 0.5
            elif signals.timing_variance < 1000:
                scores["timing_variance"] = 0.2
            else:
                scores["timing_variance"] = 0.0
                reasons.append("High timing variance (human-like)")

        # 4. Inter-Request Interval Analysis
        if signals.inter_request_interval_ms is not None:
            if signals.inter_request_interval_ms < 50:
                scores["inter_request_interval"] = 1.0
                reasons.append(
                    f"Ultra-fast requests ({signals.inter_request_interval_ms:.0f}ms)"
                )
            elif signals.inter_request_interval_ms < 200:
                scores["inter_request_interval"] = 0.85
                reasons.append("Very fast request rate")
            elif signals.inter_request_interval_ms < 500:
                scores["inter_request_interval"] = 0.6
            elif signals.inter_request_interval_ms < 2000:
                scores["inter_request_interval"] = 0.3
            else:
                scores["inter_request_interval"] = 0.1

        # 5. Request Rate Analysis
        if signals.request_rate_per_minute is not None:
            if signals.request_rate_per_minute > 120:
                scores["request_rate"] = 1.0
                reasons.append(
                    f"Extremely high rate ({signals.request_rate_per_minute:.1f}/min)"
                )
            elif signals.request_rate_per_minute > 60:
                scores["request_rate"] = 0.85
                reasons.append("High request rate")
            elif signals.request_rate_per_minute > 30:
                scores["request_rate"] = 0.6
            elif signals.request_rate_per_minute > 10:
                scores["request_rate"] = 0.3
            else:
                scores["request_rate"] = 0.1

        # 6. Payload Entropy Analysis
        if signals.payload_entropy is not None:
            if signals.payload_entropy < 1.0:
                scores["payload_entropy"] = 0.8
                reasons.append("Low payload entropy (repetitive)")
            elif signals.payload_entropy < 2.0:
                scores["payload_entropy"] = 0.5
            elif signals.payload_entropy < 3.0:
                scores["payload_entropy"] = 0.3
            else:
                scores["payload_entropy"] = 0.1

        # 7. Pattern Repetition Analysis
        if signals.pattern_repetition_score is not None:
            if signals.pattern_repetition_score > 0.8:
                scores["pattern_repetition"] = 1.0
                reasons.append("High pattern repetition")
            elif signals.pattern_repetition_score > 0.5:
                scores["pattern_repetition"] = 0.7
            elif signals.pattern_repetition_score > 0.2:
                scores["pattern_repetition"] = 0.4
            else:
                scores["pattern_repetition"] = 0.1

        # Calculate weighted average confidence
        total_weight = 0.0
        weighted_sum = 0.0

        for signal_name, weight in self.WEIGHTS.items():
            if signal_name in scores:
                weighted_sum += scores[signal_name] * weight
                total_weight += weight

        # If total calculated weight is too low (e.g., only static signals),
        # we might normalize or treat carefully. But our static signals have 40% weight total
        # which is significant.

        confidence = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Adjust confidence for known bot user agents to be very decisive
        if scores.get("user_agent_score", 0) > 0.95:
            # If it explicitly identifies effectively as a bot via User-Agent, boost confidence
            confidence = max(confidence, 0.85)
            if "Known Bot User-Agent" not in reasons:
                reasons.insert(0, "Known Bot User-Agent")

        # Determine classification
        is_bot = confidence >= 0.5  # Simple boolean threshold

        if confidence >= HIGH_BOT_THRESHOLD:
            classification = "bot"
        elif confidence <= LOW_BOT_THRESHOLD:
            classification = "human"
        elif confidence > 0.5:
            classification = "likely_bot"
        else:
            classification = "likely_human"

        # Build reason string
        if not reasons:
            reason = "Normal behavior patterns"
        else:
            # Deduplicate reasons while preserving order
            seen = set()
            unique_reasons = []
            for r in reasons:
                if r not in seen:
                    unique_reasons.append(r)
                    seen.add(r)
            reason = "; ".join(unique_reasons[:3])  # Top 3 reasons

        return BotDetectionResult(
            is_bot=is_bot,
            confidence=round(confidence, 3),
            signals=signals,
            classification=classification,
            reason=reason,
        )

    def _compute_signals(
        self,
        source_ip: str,
        payload: str,
        user_agent: str,
        ja4_fingerprint: Optional[str] = None,
    ) -> BotDetectionSignals:
        """Compute all detection signals for an IP."""
        signals = BotDetectionSignals()
        signals.ja4_fingerprint = ja4_fingerprint

        now_ms = time.time() * 1000
        timestamps = self._ip_timestamps.get(source_ip, [])
        intervals = self._ip_intervals.get(source_ip, [])
        payload_hashes = self._ip_payload_hashes.get(source_ip, [])
        session_start = self._ip_session_start.get(source_ip)

        # --- STATIC SIGNALS ---

        # User-Agent Score
        if user_agent is not None:
            signals.user_agent_score = self._analyze_user_agent(user_agent)

        # Payload Pattern Score (only if payload is not empty)
        if payload:
            signals.payload_pattern_score = self._analyze_payload_patterns(payload)
            signals.payload_entropy = self._calculate_entropy(payload)

        # --- BEHAVIORAL SIGNALS ---

        # Session duration
        if session_start:
            signals.session_duration_ms = now_ms - session_start

        # Inter-request interval (average of recent)
        if intervals:
            signals.inter_request_interval_ms = statistics.mean(intervals)

        # Timing variance
        if len(intervals) >= 2:
            signals.timing_variance = statistics.stdev(intervals)

        # Request rate per minute
        if len(timestamps) >= 2 and timestamps[-1] > timestamps[0]:
            duration_minutes = (timestamps[-1] - timestamps[0]) / 60000.0
            if duration_minutes > 0:
                signals.request_rate_per_minute = (
                    len(timestamps) - 1
                ) / duration_minutes

        # Pattern repetition score
        if len(payload_hashes) >= 2:
            unique_hashes = len(set(payload_hashes))
            total_hashes = len(payload_hashes)
            signals.pattern_repetition_score = 1.0 - (unique_hashes / total_hashes)

        return signals

    def _analyze_user_agent(self, user_agent: str) -> float:
        """
        Analyze User-Agent string.
        Returns score: 0.0 (Human) to 1.0 (Bot).
        """
        if not user_agent or user_agent.lower() in ("unknown", "none"):
            return 0.8  # No UA is suspicious

        # Check against known bot patterns
        for pattern in BOT_USER_AGENTS:
            if re.search(pattern, user_agent):
                return 1.0

        return 0.1  # likely browser/human if not matched

    def _analyze_payload_patterns(self, payload: str) -> float:
        """
        Analyze payload for automated scan patterns.
        Returns score: 0.0 (Safe) to 1.0 (Automated).
        """
        if not payload:
            return 0.0

        for pattern in AUTOMATED_SCAN_PATTERNS:
            if re.search(pattern, payload, re.IGNORECASE):
                return 1.0

        return 0.0

    @staticmethod
    def _calculate_entropy(data: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not data:
            return 0.0

        # Count character frequencies
        freq: Dict[str, int] = {}
        for char in data:
            freq[char] = freq.get(char, 0) + 1

        # Calculate entropy
        length = len(data)
        entropy = 0.0
        for count in freq.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy

    def clear_ip_data(self, source_ip: str) -> None:
        """Clear all tracking data for an IP (e.g., session ended)."""
        self._ip_timestamps.pop(source_ip, None)
        self._ip_session_start.pop(source_ip, None)
        self._ip_payload_hashes.pop(source_ip, None)
        self._ip_intervals.pop(source_ip, None)

    def get_stats(self) -> Dict[str, Any]:
        """Get current detector statistics."""
        return {
            "tracked_ips": len(self._ip_timestamps),
            "total_requests": sum(len(ts) for ts in self._ip_timestamps.values()),
        }


# Global singleton instance
_detector: Optional[BotDetector] = None


def get_bot_detector() -> BotDetector:
    """Get the global BotDetector instance."""
    global _detector
    if _detector is None:
        _detector = BotDetector()
    return _detector
