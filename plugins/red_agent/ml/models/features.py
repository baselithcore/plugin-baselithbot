"""Feature extraction for the Red Agent ML models.

Pure functions: given a :class:`Finding`, return a fixed-length numeric
feature vector. Kept dependency-free (no numpy / sklearn) so the
extractor can run on the inference hot path without paying import
overhead and so it is trivially unit-testable.

The feature schema is **frozen** and versioned via ``FEATURE_VERSION``.
Bump the version when adding/removing features so a stale model on
disk fails fast instead of silently mis-scoring findings.
"""

from __future__ import annotations

from typing import Any

from plugins.red_agent.models import Finding, Severity

FEATURE_VERSION = 1

_SCANNER_INDEX: dict[str, int] = {
    "nmap": 0,
    "nuclei": 1,
    "zap": 2,
    "trivy": 3,
    "sqlmap": 4,
}

_SEVERITY_INDEX: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}

# Stable ordered list of feature names — the model's input layer relies
# on this order. NEVER reorder; only append (and bump FEATURE_VERSION).
FEATURE_NAMES: list[str] = [
    "scanner_idx",
    "severity_idx",
    "cvss_score",
    "has_cvss",
    "has_cwe",
    "has_cve",
    "has_endpoint",
    "endpoint_length",
    "endpoint_path_segments",
    "has_port",
    "port_high",  # 1 if port > 1024
    "title_length",
    "description_length",
    "evidence_keys",
    "evidence_has_matched",
    "evidence_has_extracted",
    "evidence_has_confirmed",
    "scanner_failure",
]


def feature_dim() -> int:
    return len(FEATURE_NAMES)


def extract_features(finding: Finding) -> list[float]:
    """Project a Finding into the fixed feature vector used by M1."""
    scanner_idx = _SCANNER_INDEX.get(finding.scanner, len(_SCANNER_INDEX))
    severity_idx = _SEVERITY_INDEX.get(finding.severity, 0)
    cvss = finding.cvss_score or 0.0

    endpoint = finding.endpoint or ""
    endpoint_len = float(len(endpoint))
    endpoint_segments = float(endpoint.count("/"))

    port = finding.port or 0

    evidence: dict[str, Any] = (
        finding.evidence if isinstance(finding.evidence, dict) else {}
    )
    return [
        float(scanner_idx),
        float(severity_idx),
        float(cvss),
        1.0 if finding.cvss_score is not None else 0.0,
        1.0 if finding.cwe else 0.0,
        1.0 if finding.cve else 0.0,
        1.0 if endpoint else 0.0,
        endpoint_len,
        endpoint_segments,
        1.0 if finding.port else 0.0,
        1.0 if port > 1024 else 0.0,
        float(len(finding.title or "")),
        float(len(finding.description or "")),
        float(len(evidence)),
        1.0 if "matched" in evidence else 0.0,
        1.0 if "extracted_results" in evidence else 0.0,
        1.0 if evidence.get("confirmed") else 0.0,
        1.0 if evidence.get("scanner_failure") else 0.0,
    ]
