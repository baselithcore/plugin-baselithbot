"""Output filtering configurations and logic."""

from core.observability.logging import get_logger
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = get_logger(__name__)


@dataclass
class OutputFilterConfig:
    """Configuration for output filtering."""

    # Regex patterns to filter from output
    regex_patterns: List[str] = field(default_factory=list)

    # Replacement string for filtered content
    replacement: str = "[FILTERED]"

    # Maximum output length
    max_length: int = 2000

    # Enable semantic filtering
    enable_semantic: bool = False

    # Semantic filter threshold (0.0-1.0)
    semantic_threshold: float = 0.7


class OutputFilter:
    """Filters LLM output to prevent information leakage.

    Uses both regex patterns and semantic analysis to detect
    and filter potentially dangerous output.
    """

    # Default patterns to filter (sensitive data indicators)
    DEFAULT_PATTERNS: List[str] = [
        # API keys and secrets
        r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[\w\-]{16,}",
        r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{4,}",
        r"(?i)bearer\s+[\w\-\.]+",
        # System prompt leakage indicators
        r"(?i)my\s+(system\s+)?prompt\s+(is|says|tells)",
        r"(?i)i\s+(was|am)\s+(told|instructed|programmed)\s+to",
        r"(?i)my\s+instructions?\s+(are|say|tell)",
        r"(?i)\[SYSTEM[_\s]?(INSTRUCTION|PROMPT|DIRECTIVE)\]",
        # Internal paths
        r"/home/\w+/\.",
        r"/etc/(passwd|shadow|sudoers)",
        r"/var/log/",
        r"C:\\\\(Users|Windows|Program Files)",
        # Configuration leakage
        r"(?i)(database|db)[_\s]?(url|host|connection)",
        r"(?i)(redis|mongo|postgres|mysql)://",
        r"(?i)connection[_\s]?string",
    ]

    # Semantic filter phrases (things the LLM should never say)
    SEMANTIC_BLOCKLIST: List[str] = [
        "I am a honeypot",
        "I am designed to trap",
        "You are being monitored",
        "This is a security test",
        "My system prompt says",
        "I was instructed to",
        "According to my instructions",
        "My programming requires me to",
    ]

    def __init__(self, config: Optional[OutputFilterConfig] = None) -> None:
        """Initialize output filter.

        Args:
            config: Filter configuration
        """
        self.config = config or OutputFilterConfig()

        # Compile patterns
        all_patterns = self.DEFAULT_PATTERNS + self.config.regex_patterns
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) for p in all_patterns
        ]

        # Prepare semantic blocklist (lowercase for comparison)
        self._semantic_blocklist = [s.lower() for s in self.SEMANTIC_BLOCKLIST]

    def filter(self, output: str) -> Tuple[str, Dict[str, Any]]:
        """Filter LLM output for sensitive content.

        Args:
            output: Raw LLM output

        Returns:
            Tuple of (filtered_output, filter_stats)
        """
        if not output:
            return "", {"filtered": False, "matches": []}

        filtered = output
        stats: Dict[str, Any] = {
            "filtered": False,
            "regex_matches": [],
            "semantic_matches": [],
            "truncated": False,
        }

        # 1. Regex filtering
        for pattern in self._compiled_patterns:
            matches = pattern.findall(filtered)
            if matches:
                stats["regex_matches"].extend(matches[:3])  # Limit logged matches
                filtered = pattern.sub(self.config.replacement, filtered)
                stats["filtered"] = True

        # 2. Semantic filtering (simple substring check for now)
        output_lower = filtered.lower()
        for phrase in self._semantic_blocklist:
            if phrase in output_lower:
                stats["semantic_matches"].append(phrase)
                # Replace the phrase case-insensitively
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                filtered = pattern.sub(self.config.replacement, filtered)
                stats["filtered"] = True

        # 3. Length limit
        if len(filtered) > self.config.max_length:
            filtered = filtered[: self.config.max_length] + "..."
            stats["truncated"] = True

        # Log if filtering occurred
        if stats["filtered"]:
            logger.info(
                f"Output filtered: regex_matches={len(stats['regex_matches'])}, "
                f"semantic_matches={len(stats['semantic_matches'])}"
            )

        return filtered, stats
