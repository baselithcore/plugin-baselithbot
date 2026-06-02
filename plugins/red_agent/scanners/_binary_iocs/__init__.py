"""Strings, entropy and IOC extraction helpers for the binary analyzer.

Pure stdlib. Designed to run on raw bytes without ever executing the
sample. Regex catalogue mirrors the patterns shared across modern
malware-analysis pipelines (CISA STIX guides, MITRE ATT&CK
indicator types, Volexity/Mandiant blogposts).

This package re-exports the same public surface previously exposed by
the ``_binary_iocs`` module so existing import paths keep working.
"""

from __future__ import annotations

from plugins.red_agent.scanners._binary_iocs._classify import (
    classify_ipv4,
    classify_url,
    threat_intel_pivot_links,
)
from plugins.red_agent.scanners._binary_iocs._extract import (
    extract_iocs,
    is_routable_ipv4,
    suspicious_imports,
)
from plugins.red_agent.scanners._binary_iocs._strings import (
    ASCII_RANGE,
    MIN_STRING_LEN,
    extract_strings,
    shannon_entropy,
)

__all__ = [
    "ASCII_RANGE",
    "MIN_STRING_LEN",
    "classify_ipv4",
    "classify_url",
    "extract_iocs",
    "extract_strings",
    "is_routable_ipv4",
    "shannon_entropy",
    "suspicious_imports",
    "threat_intel_pivot_links",
]
