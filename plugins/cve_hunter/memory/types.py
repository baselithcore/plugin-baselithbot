"""CVE Hunter Memory Types.

This module contains memory type constants for CVE Hunter.
"""


class CVEMemoryTypes:
    """CVE Hunter memory type constants."""

    # CVE knowledge
    CVE_RECORD = "cve_record"
    CVE_ANALYSIS = "cve_analysis"

    # Discovery patterns
    DISCOVERY_PATTERN = "discovery_pattern"
    DISCOVERY_SUCCESS = "discovery_success"
    DISCOVERY_FALSE_POSITIVE = "discovery_false_positive"

    # Correlation knowledge
    CORRELATION = "correlation"
    ATTACK_PATTERN = "attack_pattern"
    CORRELATION_FEEDBACK = "correlation_feedback"
    ATTACK_CHAIN_FEEDBACK = "attack_chain_feedback"

    # Scan history
    SCAN_RESULT = "scan_result"
    SOURCE_STATUS = "source_status"
