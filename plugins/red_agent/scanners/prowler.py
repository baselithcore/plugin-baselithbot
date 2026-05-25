"""Prowler CSPM scanner adapter.

Multi-cloud posture scanner (AWS / Azure / GCP / Kubernetes). Maps to
hundreds of compliance controls across CIS, PCI DSS, ISO27001, SOC2,
NIST 800-53, HIPAA, GDPR.

Authentication is supplied by the operator-controlled cloud provider
chain (env vars, IRSA, workload identity). The adapter does **not**
inject credentials; it relies on whatever the SandboxRunner exposes via
mounted credentials/env. Failed checks emit findings; passed/skipped
checks are dropped.

Output format: ``--output-formats json-ocsf`` (preferred — already
schema-aligned with this plugin's OCSF exporter) falls back to
``--output-formats json`` for older prowler builds.
"""

from __future__ import annotations

import json
from typing import Any

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

_SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "informational": Severity.INFO,
    "info": Severity.INFO,
}

_PROVIDER_FROM_VALUE = {
    "aws": "aws",
    "azure": "azure",
    "gcp": "gcp",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
}


class ProwlerScanner(Scanner):
    name = "prowler"
    kind = ScannerKind.CSPM
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = "toniblyx/prowler:latest"
    requires_network = True
    default_timeout = 1800

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if target.type not in (TargetType.CLOUD_ACCOUNT, TargetType.K8S_CLUSTER):
            return []
        provider = _resolve_provider(target)
        argv = [
            provider,
            "--output-formats",
            "json-ocsf",
            "--output-directory",
            "/workspace",
            "--no-banner",
            "--quiet",
        ]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
        )
        return self._parse(result.stdout, target)

    def _parse(self, json_text: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        try:
            doc = json.loads(json_text)
        except json.JSONDecodeError:
            return findings

        # Prowler json-ocsf shape: a list of OCSF Compliance Finding events
        # (class_uid=2003) with ``status_id=2`` for failed checks. Older
        # builds emit the legacy json shape: a list of dict checks.
        events = doc if isinstance(doc, list) else doc.get("findings", [])
        for ev in events or []:
            if not isinstance(ev, dict):
                continue
            findings.append(_finding_from_event(ev, target))
        return [f for f in findings if f is not None]


def _resolve_provider(target: Target) -> str:
    """Resolve the Prowler provider sub-command from a :class:`Target`.

    Falls back to AWS — the most common case — when the value does not
    encode a recognized provider.
    """
    if target.type == TargetType.K8S_CLUSTER:
        return "kubernetes"
    raw = target.value.lower()
    for key, prov in _PROVIDER_FROM_VALUE.items():
        if raw.startswith(f"{key}:") or raw == key:
            return prov
    meta_provider = target.metadata.get("provider") if target.metadata else None
    if isinstance(meta_provider, str):
        return _PROVIDER_FROM_VALUE.get(meta_provider.lower(), "aws")
    return "aws"


def _finding_from_event(ev: dict[str, Any], target: Target) -> Finding:
    # OCSF-shaped event from prowler json-ocsf
    if "finding_info" in ev or "metadata" in ev:
        info = ev.get("finding_info") or {}
        title = info.get("title") or ev.get("message") or "prowler finding"
        desc = info.get("desc") or ev.get("status_detail") or title
        sev = ev.get("severity") or ev.get("severity_id") or "medium"
        sev_value = (
            sev
            if isinstance(sev, str)
            else _OCSF_SEVERITY_REVERSE.get(int(sev), "medium")
        )
        return Finding(
            scanner="prowler",
            title=str(title),
            description=str(desc),
            severity=_SEVERITY_MAP.get(sev_value.lower(), Severity.MEDIUM),
            target=target.value,
            endpoint=info.get("uid"),
            evidence={
                "compliance": ev.get("compliance"),
                "resource_uid": (ev.get("resources") or [{}])[0].get("uid"),
                "region": ev.get("cloud", {}).get("region"),
                "account": ev.get("cloud", {}).get("account", {}).get("uid"),
            },
            raw=ev,
            remediation=info.get("desc"),
        )

    # Legacy prowler JSON
    return Finding(
        scanner="prowler",
        title=str(ev.get("CheckTitle") or ev.get("check_title") or "prowler finding"),
        description=str(ev.get("StatusExtended") or ev.get("description") or ""),
        severity=_SEVERITY_MAP.get(
            str(ev.get("Severity", "medium")).lower(), Severity.MEDIUM
        ),
        target=target.value,
        evidence={
            "check_id": ev.get("CheckID"),
            "service": ev.get("ServiceName"),
            "region": ev.get("Region"),
            "resource": ev.get("ResourceName"),
            "compliance": ev.get("Compliance"),
        },
        raw=ev,
        remediation=ev.get("Remediation", {}).get("Recommendation", {}).get("Text"),
    )


_OCSF_SEVERITY_REVERSE: dict[int, str] = {
    1: "informational",
    2: "low",
    3: "medium",
    4: "high",
    5: "critical",
    6: "critical",
}
