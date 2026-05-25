"""Certipy ADCS misconfiguration scanner adapter.

Wraps ``certipy-ad find`` (read-only mode) against an Active
Directory Certificate Services environment and surfaces ESC1–ESC11
vulnerabilities as findings. Mutating sub-commands (``account
create``, ``template create``) are gated behind
``identity_allow_mutating_actions`` and INTRUSIVE intensity.

Severity ladder:

| ESC | Severity | Reason |
| --- | --- | --- |
| ESC1, ESC2, ESC3 | Critical | Direct DA via cert request. |
| ESC4, ESC5 | Critical | ACL takeover of templates / CA. |
| ESC6, ESC7 | High | EDITF_ATTRIBUTESUBJECTALTNAME2 / CA admin. |
| ESC8 | High | NTLM relay to ADCS web enrolment. |
| ESC9, ESC10, ESC11 | High | Schannel / weak StrongCertBinding. |
"""

from __future__ import annotations

import json
from typing import Any

from core.observability.logging import get_logger
from plugins.red_agent._credential_resolver import resolve_credentials
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners._identity_base import (
    credentials_to_env,
    passive_blocked,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)


_ESC_SEVERITY: dict[str, Severity] = {
    "ESC1": Severity.CRITICAL,
    "ESC2": Severity.CRITICAL,
    "ESC3": Severity.CRITICAL,
    "ESC4": Severity.CRITICAL,
    "ESC5": Severity.CRITICAL,
    "ESC6": Severity.HIGH,
    "ESC7": Severity.HIGH,
    "ESC8": Severity.HIGH,
    "ESC9": Severity.HIGH,
    "ESC10": Severity.HIGH,
    "ESC11": Severity.HIGH,
}


class CertipyScanner(Scanner):
    name = "certipy"
    kind = ScannerKind.IDENTITY
    supports_intensity = (ScanIntensity.ACTIVE, ScanIntensity.INTRUSIVE)
    requires_network = True
    default_timeout = 1200

    def __init__(
        self,
        sandbox: Any,
        config: RedAgentConfig,
        timeout: int | None = None,
    ) -> None:
        super().__init__(sandbox, timeout=timeout)
        self._config = config
        self.image = config.identity_certipy_image

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if not self._config.identity_enabled:
            return []
        if target.type != TargetType.AD_DOMAIN:
            return []
        if passive_blocked(intensity):
            return []

        cred = await resolve_credentials(
            backend_name=self._config.identity_credentials_backend,
            target=target,
            credentials_ref=(
                target.metadata.get("credentials_ref")
                if isinstance(target.metadata, dict)
                else None
            ),
        )
        if not cred.username or cred.password is None:
            return []
        env = credentials_to_env(cred)

        meta = target.metadata if isinstance(target.metadata, dict) else {}
        domain_controller = str(meta.get("domain_controller") or target.value)
        argv = [
            "find",
            "-u",
            f"{cred.username}@{cred.domain or target.value}",
            "-p",
            "$RA_PASSWORD",
            "-dc-ip",
            domain_controller,
            "-vulnerable",
            "-json",
            "-output",
            "/workspace/certipy",
        ]

        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
            env=env,
            artifacts=["certipy_Certipy.json"],
        )
        return self._parse(result.artifacts.get("certipy_Certipy.json", ""), target)

    def _parse(self, blob: str, target: Target) -> list[Finding]:
        if not blob:
            return []
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            return []
        templates = payload.get("Certificate Templates")
        if not isinstance(templates, dict):
            return []

        findings: list[Finding] = []
        for tmpl_name, tmpl in templates.items():
            if not isinstance(tmpl, dict):
                continue
            vulns = tmpl.get("[!] Vulnerabilities") or tmpl.get("Vulnerabilities")
            if not isinstance(vulns, dict):
                continue
            for esc_id, description in vulns.items():
                severity = _ESC_SEVERITY.get(esc_id.upper(), Severity.HIGH)
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"ADCS {esc_id}: {tmpl_name}",
                        description=str(description),
                        severity=severity,
                        target=target.value,
                        endpoint=str(tmpl_name),
                        evidence={
                            "esc": esc_id,
                            "template": tmpl_name,
                            "enabled": tmpl.get("Enabled"),
                            "ca_name": tmpl.get("Certificate Authorities"),
                        },
                        cwe="CWE-295",
                    )
                )
        return findings
