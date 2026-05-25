"""SARIF 2.1.0 exporter for Red Agent findings."""

from __future__ import annotations

from typing import Any

from plugins.red_agent.models import Finding, ScanResult, Severity

_SARIF_LEVEL: dict[Severity, str] = {
    Severity.INFO: "note",
    Severity.LOW: "note",
    Severity.MEDIUM: "warning",
    Severity.HIGH: "error",
    Severity.CRITICAL: "error",
}


def to_sarif(scan: ScanResult) -> dict[str, Any]:
    """Convert a ScanResult into a SARIF 2.1.0 document."""
    runs = []
    by_scanner: dict[str, list[Finding]] = {}
    for f in scan.findings:
        by_scanner.setdefault(f.scanner, []).append(f)

    for scanner, findings in by_scanner.items():
        rules: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        rule_index: dict[str, int] = {}
        for f in findings:
            rule_id = f.cwe or f.cve or f.title[:64]
            if rule_id not in rule_index:
                rule_index[rule_id] = len(rules)
                rules.append(
                    {
                        "id": rule_id,
                        "name": f.title,
                        "shortDescription": {"text": f.title},
                        "fullDescription": {"text": f.description},
                        "helpUri": (
                            f"https://nvd.nist.gov/vuln/detail/{f.cve}"
                            if f.cve
                            else None
                        ),
                    }
                )
            evidence = f.evidence if isinstance(f.evidence, dict) else {}
            attack_techniques = evidence.get("attack_techniques") or []
            detection = evidence.get("detection_guidance") or None
            sarif_props: dict[str, Any] = {
                "cvss_score": f.cvss_score,
                "severity": f.severity.value,
                "remediation": f.remediation,
                "risk_score": f.risk_score,
                "controls": list(f.controls or []),
            }
            if attack_techniques:
                sarif_props["attack_techniques"] = attack_techniques
                # ``tags`` is an established SARIF convention picked up by
                # GitHub Code Scanning + Defender; surface ATT&CK there too.
                sarif_props["tags"] = sorted(
                    {t.get("id", "") for t in attack_techniques if t.get("id")}
                )
            if detection:
                sarif_props["detection_guidance"] = detection
            results.append(
                {
                    "ruleId": rule_id,
                    "ruleIndex": rule_index[rule_id],
                    "level": _SARIF_LEVEL[f.severity],
                    "message": {"text": f.description or f.title},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": f.endpoint or f.target,
                                },
                            },
                        }
                    ],
                    "properties": sarif_props,
                }
            )

        runs.append(
            {
                "tool": {
                    "driver": {
                        "name": scanner,
                        "informationUri": "https://github.com/baselithcore/baselithcore-prod",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": runs,
    }
