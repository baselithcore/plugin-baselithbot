"""Sigma rule YAML emitter.

Renders a finding's :class:`detection_guidance` annotation as a valid
Sigma rule (https://github.com/SigmaHQ/sigma-spec). The output is a
*draft* — selection patterns are derived from the guidance text, not
from a pre-computed Sigma logic — so SOC teams can pick it up,
finalize the field/value pairs against their own log shape, and ship
to a SIEM.

Standalone, pure: no I/O, no DB. Returns ``None`` when the finding
lacks ``detection_guidance``.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid5, NAMESPACE_URL

import yaml

from plugins.red_agent.models import Finding, Severity


_SIGMA_LEVEL: dict[Severity, str] = {
    Severity.INFO: "informational",
    Severity.LOW: "low",
    Severity.MEDIUM: "medium",
    Severity.HIGH: "high",
    Severity.CRITICAL: "critical",
}

_KEYWORD_RE = re.compile(r"`([^`]{2,80})`")


# Per-scanner logsource templates. Override the CWE-derived logsource
# when the scanner family fingerprints a more specific telemetry lane
# (e.g. ``nmap`` is reliably netflow / zeek, ``gitleaks`` is file write
# events). Missing scanners fall back to the CWE-derived logsource.
_SCANNER_LOGSOURCE: dict[str, dict[str, str]] = {
    "nuclei": {"product": "webserver", "category": "webserver"},
    "zap": {"product": "webserver", "category": "webserver"},
    "sqlmap": {"product": "webserver", "category": "webserver"},
    "secure_headers": {"product": "webserver", "category": "webserver"},
    "schemathesis": {"product": "webserver", "category": "webserver"},
    "nmap": {"product": "zeek", "category": "network_connection"},
    "sslyze": {"product": "zeek", "category": "network_connection"},
    "gitleaks": {"product": "linux", "category": "file_event"},
    "trivy": {"product": "linux", "category": "process_creation"},
    "syft": {"product": "linux", "category": "process_creation"},
    "grype": {"product": "linux", "category": "process_creation"},
    "semgrep": {"product": "linux", "category": "file_event"},
    "checkov": {"product": "aws", "category": "cloudtrail"},
    "prowler": {"product": "aws", "category": "cloudtrail"},
    "kube_bench": {"product": "kubernetes", "category": "audit"},
    "llm_recon": {"product": "webserver", "category": "webserver"},
    "llm_prompt_injection": {
        "product": "llm_application",
        "category": "chat_completion",
    },
    "llm_tool_abuse": {"product": "llm_application", "category": "chat_completion"},
    "llm_data_leakage": {"product": "llm_application", "category": "chat_completion"},
    "llm_output_handling": {
        "product": "llm_application",
        "category": "chat_completion",
    },
}


def to_sigma_dict(
    finding: Finding,
    *,
    keyword_override: list[str] | None = None,
    extra_tags: list[str] | None = None,
) -> dict[str, Any] | None:
    """Build the Sigma rule as a Python dict (pre-YAML).

    ``keyword_override`` replaces the auto-extracted Sigma ``keywords``
    selector, so SOC engineers can curate the matching tokens inline
    before shipping. ``extra_tags`` appends operator-supplied tags
    (e.g. team or campaign labels) on top of the auto-derived set.
    """
    evidence = finding.evidence if isinstance(finding.evidence, dict) else {}
    guidance = evidence.get("detection_guidance")
    if not isinstance(guidance, dict):
        return None
    logsource = guidance.get("logsource") or {}
    detection_text = str(guidance.get("detection") or "")
    mitigations = list(guidance.get("mitigations") or [])

    rule_id = uuid5(NAMESPACE_URL, f"baselithcore.red_agent/{finding.id}")
    keywords = (
        _normalize_keywords(keyword_override)
        if keyword_override is not None
        else _extract_keywords(detection_text)
    )
    selection: dict[str, Any] = (
        {"keywords": keywords} if keywords else {"keywords": ["__placeholder__"]}
    )

    # Scanner-family logsource template wins over the CWE-derived one
    # when present. Reason: the scanner fingerprints the actual data
    # lane (e.g. ``nmap`` → zeek/netflow), which is more reliable than
    # the generic CWE category mapping.
    scanner_logsource = _SCANNER_LOGSOURCE.get(finding.scanner)
    if scanner_logsource is not None:
        logsource = {**scanner_logsource}

    tags: list[str] = []
    if finding.scanner:
        tags.append(f"baselithcore.scanner.{finding.scanner.lower()}")
    for technique in evidence.get("attack_techniques") or []:
        if isinstance(technique, dict):
            tid = str(technique.get("id") or "").strip().lower()
            if tid:
                tags.append(f"attack.{tid}")
    if finding.cwe:
        tags.append(f"cwe.{finding.cwe.lower()}")
    if finding.cve:
        tags.append(finding.cve.lower())
    if extra_tags:
        for tag in extra_tags:
            cleaned = tag.strip().lower()
            if cleaned:
                tags.append(cleaned)

    references: list[str] = []
    if finding.cve:
        references.append(f"https://nvd.nist.gov/vuln/detail/{finding.cve}")
    references.append(
        "https://owasp.org/www-project-top-ten/"
        if not finding.cwe
        else f"https://cwe.mitre.org/data/definitions/{finding.cwe.replace('CWE-', '')}.html"
    )

    rule: dict[str, Any] = {
        "title": f"BaselithCore — {finding.title}",
        "id": str(rule_id),
        "status": "experimental",
        "description": detection_text or finding.description or finding.title,
        "references": references,
        "author": "BaselithCore Red Agent",
        "date": finding.discovered_at.strftime("%Y/%m/%d"),
        "logsource": {k: v for k, v in logsource.items() if v},
        "detection": {
            "selection": selection,
            "condition": "selection",
        },
        "level": _SIGMA_LEVEL[finding.severity],
    }
    if mitigations:
        # Sigma doesn't have a canonical mitigations field; surface them
        # as falsepositives + a custom ``baselithcore`` block that is
        # stripped by sigma-cli when present but visible to humans.
        rule["falsepositives"] = [
            "Confirm against expected operational traffic before alerting"
        ]
        rule["baselithcore"] = {"mitigations": mitigations}
    if tags:
        rule["tags"] = sorted(set(tags))
    return rule


def to_sigma_yaml(
    finding: Finding,
    *,
    keyword_override: list[str] | None = None,
    extra_tags: list[str] | None = None,
) -> str | None:
    """Render the Sigma rule as YAML, or return ``None`` if no guidance."""
    rule = to_sigma_dict(
        finding, keyword_override=keyword_override, extra_tags=extra_tags
    )
    if rule is None:
        return None
    return yaml.safe_dump(rule, sort_keys=False, allow_unicode=True)


def _normalize_keywords(values: list[str]) -> list[str]:
    """De-dupe and trim user-supplied keywords; drop blanks."""
    seen: list[str] = []
    for v in values:
        cleaned = v.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def _extract_keywords(text: str) -> list[str]:
    """Pull backtick-quoted tokens out of guidance text as Sigma keywords.

    Sigma's ``keywords`` selector matches if any token appears in any
    field. Prefer backticked tokens (UNION SELECT, ``..%2f``) since
    those are the operator's hand-curated indicators; fall back to a
    capped slice of the raw text when nothing's quoted.
    """
    quoted = _KEYWORD_RE.findall(text)
    if quoted:
        seen: list[str] = []
        for token in quoted:
            t = token.strip()
            if t and t not in seen:
                seen.append(t)
        return seen
    # Conservative fallback so the rule remains valid YAML.
    truncated = text.strip().split(".", 1)[0][:120]
    return [truncated] if truncated else []
