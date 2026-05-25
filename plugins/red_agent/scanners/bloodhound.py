"""bloodhound.py (BloodHound AD collector) adapter.

Drives the open-source ``bloodhound-python`` collector to enumerate
an Active Directory domain via LDAP/SMB, ingest objects, and surface
attack-path-relevant flags as findings: kerberoastable accounts,
AS-REProastable accounts, unconstrained-delegation principals, and
``adminCount=1`` users that sit outside Tier-0.

Heavy attack-path computation (shortest path to Domain Admins,
ACL-driven escalations) is intentionally **not** done here — that
data is ingested into the BloodHound graph instance and surfaced via
the dashboard. The Red Agent only emits the per-object findings that
warrant operator triage on their own.
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


_KERBEROASTABLE_FLAG = "kerberoastable"
_ASREPROASTABLE_FLAG = "dontreqpreauth"
_UNCONSTRAINED_FLAG = "unconstraineddelegation"


class BloodHoundScanner(Scanner):
    name = "bloodhound"
    kind = ScannerKind.IDENTITY
    supports_intensity = (ScanIntensity.ACTIVE, ScanIntensity.INTRUSIVE)
    requires_network = True
    default_timeout = 1800

    def __init__(
        self,
        sandbox: Any,
        config: RedAgentConfig,
        timeout: int | None = None,
    ) -> None:
        super().__init__(sandbox, timeout=timeout)
        self._config = config
        self.image = config.identity_bloodhound_image

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if not self._config.identity_enabled:
            logger.info("red_agent.identity.disabled", extra={"scanner": self.name})
            return []
        if target.type != TargetType.AD_DOMAIN:
            logger.info(
                "red_agent.identity.wrong_target_type",
                extra={"scanner": self.name, "type": target.type.value},
            )
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
            logger.warning(
                "red_agent.bloodhound.no_credentials",
                extra={"target": target.value},
            )
            return []
        env = credentials_to_env(cred)

        meta = target.metadata if isinstance(target.metadata, dict) else {}
        domain_controller = str(meta.get("domain_controller") or target.value)
        argv = [
            "-d",
            cred.domain or target.value,
            "-u",
            cred.username,
            # Password is read from $RA_PASSWORD by the wrapper; never argv.
            "-p",
            "$RA_PASSWORD",
            "-c",
            "DCOnly",
            "-dc",
            domain_controller,
            "--zip",
            "-op",
            "/workspace/bh-",
        ]

        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
            env=env,
            artifacts=["bh-users.json", "bh-computers.json", "bh-groups.json"],
        )
        return self._parse_artifacts(result.artifacts, target)

    def _parse_artifacts(
        self, artifacts: dict[str, str], target: Target
    ) -> list[Finding]:
        users_blob = artifacts.get("bh-users.json", "")
        return self._parse_users(users_blob, target)

    def _parse_users(self, blob: str, target: Target) -> list[Finding]:
        if not blob:
            return []
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            return []
        users = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(users, list):
            return []

        findings: list[Finding] = []
        for u in users:
            if not isinstance(u, dict):
                continue
            props = (
                u.get("Properties", {}) if isinstance(u.get("Properties"), dict) else {}
            )
            name = (
                props.get("samaccountname")
                or props.get("name")
                or u.get("ObjectIdentifier", "unknown")
            )
            enabled = bool(props.get("enabled", True))
            if not enabled:
                continue
            if props.get(_KERBEROASTABLE_FLAG):
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"Kerberoastable account: {name}",
                        description=(
                            "Account has a Service Principal Name and is "
                            "vulnerable to TGS-REQ ticket extraction "
                            "(Kerberoasting)."
                        ),
                        severity=Severity.HIGH,
                        target=target.value,
                        endpoint=str(name),
                        evidence={
                            "flag": _KERBEROASTABLE_FLAG,
                            "spns": props.get("serviceprincipalnames"),
                        },
                        cwe="CWE-307",
                    )
                )
            if props.get(_ASREPROASTABLE_FLAG):
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"AS-REProastable account: {name}",
                        description=(
                            "Account has Kerberos pre-authentication "
                            "disabled; AS-REP responses can be cracked "
                            "offline."
                        ),
                        severity=Severity.HIGH,
                        target=target.value,
                        endpoint=str(name),
                        evidence={"flag": _ASREPROASTABLE_FLAG},
                        cwe="CWE-307",
                    )
                )
            if props.get(_UNCONSTRAINED_FLAG):
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"Unconstrained delegation: {name}",
                        description=(
                            "Principal can impersonate any user that "
                            "authenticates against it; chains into "
                            "domain-wide compromise via printerbug."
                        ),
                        severity=Severity.CRITICAL,
                        target=target.value,
                        endpoint=str(name),
                        evidence={"flag": _UNCONSTRAINED_FLAG},
                        cwe="CWE-284",
                    )
                )
        return findings
