"""nuclei template-based vulnerability scanner adapter."""

from __future__ import annotations

import json

from core.observability.logging import get_logger
from plugins.red_agent.auth_profile import AuthProfile
from plugins.red_agent.models import Finding, ScanIntensity, Severity, Target
from plugins.red_agent.scanners._auth_helpers import (
    AuthProfileError,
    cookies_to_cookie_header,
    headers_to_nuclei_argv,
    render_auth,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)

_SEVERITY_MAP: dict[str, Severity] = {
    "info": Severity.INFO,
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
}


class NucleiScanner(Scanner):
    name = "nuclei"
    kind = ScannerKind.DAST
    supports_intensity = (
        ScanIntensity.PASSIVE,
        ScanIntensity.ACTIVE,
    )
    image = "projectdiscovery/nuclei:latest"
    requires_network = True
    default_timeout = 900

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        # The image's ENTRYPOINT is `nuclei` — argv carries flags only.
        argv = [
            "-target",
            target.value,
            "-jsonl",
            "-silent",
            "-rate-limit",
            "50" if intensity == ScanIntensity.ACTIVE else "20",
        ]
        if intensity == ScanIntensity.PASSIVE:
            argv.extend(["-severity", "info,low,medium"])

        # Authenticated DAST: if the target carries an AuthProfile in
        # its metadata, render it into ``-H`` flags so nuclei probes
        # the application as the authenticated user. Failure to
        # render the profile is loud — we never silently downgrade to
        # an unauthenticated scan.
        meta = target.metadata if isinstance(target.metadata, dict) else {}
        profile_dict = meta.get("auth_profile")
        if isinstance(profile_dict, dict):
            try:
                profile = AuthProfile.model_validate(profile_dict)
                rendered = await render_auth(profile)
            except (AuthProfileError, ValueError) as exc:
                logger.warning(
                    "red_agent.nuclei.auth_profile_invalid",
                    extra={"target": target.value, "err": str(exc)},
                )
                raise
            argv.extend(headers_to_nuclei_argv(rendered.headers))
            cookie_header = cookies_to_cookie_header(rendered.cookies)
            if cookie_header:
                argv.extend(["-H", f"Cookie: {cookie_header}"])

        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
        )
        return self._parse(result.stdout, target)

    def _parse(self, jsonl: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        for line in jsonl.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue

            info = doc.get("info", {})
            sev_raw = str(info.get("severity", "info")).lower()
            classification = info.get("classification", {}) or {}
            cvss = classification.get("cvss-score")
            cwe_list = classification.get("cwe-id") or []
            cwe = cwe_list[0] if isinstance(cwe_list, list) and cwe_list else None
            cve_list = classification.get("cve-id") or []
            cve = cve_list[0] if isinstance(cve_list, list) and cve_list else None

            findings.append(
                Finding(
                    scanner=self.name,
                    title=info.get("name", doc.get("template-id", "nuclei finding")),
                    description=info.get("description", ""),
                    severity=_SEVERITY_MAP.get(sev_raw, Severity.INFO),
                    cvss_score=float(cvss) if cvss is not None else None,
                    cwe=cwe,
                    cve=cve,
                    target=target.value,
                    endpoint=doc.get("matched-at"),
                    evidence={
                        "matcher": doc.get("matcher-name"),
                        "template": doc.get("template-id"),
                        "tags": info.get("tags"),
                    },
                    raw=doc,
                    remediation=info.get("remediation"),
                )
            )
        return findings
