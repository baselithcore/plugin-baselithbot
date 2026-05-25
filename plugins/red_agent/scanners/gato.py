"""Praetorian Gato (GitHub Actions red team) scanner adapter.

Wraps the upstream `Gato <https://github.com/praetorian-inc/gato>`_
CLI to enumerate a GitHub org/repo for self-hosted runner abuse,
``pull_request_target`` script-injection vectors, and secret
exfiltration paths exploitable via crafted PRs. Gato needs a GitHub
PAT — read-only is sufficient for the surface this adapter targets
(``repo:read``, ``read:org``, ``actions:read``).

The PAT is supplied through the standard credential resolver
contract: ``Target.metadata['credentials_ref']`` resolves to a
:class:`IdentityCredential` whose ``password`` field carries the
PAT (token-style storage is the existing convention for vault
entries). The token reaches the container via the ``--env-file``
mechanism — never via argv — so it does not appear in the run log
or process tree.
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
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)


_SEVERITY_BY_CATEGORY: dict[str, Severity] = {
    "self_hosted_runner": Severity.HIGH,
    "pwn_request": Severity.CRITICAL,
    "secrets_in_logs": Severity.MEDIUM,
    "actions_oidc_trust": Severity.HIGH,
}


class GatoScanner(Scanner):
    name = "gato"
    kind = ScannerKind.CONFIG
    supports_intensity = (ScanIntensity.PASSIVE, ScanIntensity.ACTIVE)
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
        self.image = config.cicd_gato_image

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if not self._config.cicd_enabled or not self._config.cicd_gato_enabled:
            return []
        if target.type not in (TargetType.REPO, TargetType.HOSTNAME):
            return []

        meta = target.metadata if isinstance(target.metadata, dict) else {}
        credentials_ref = (
            meta.get("credentials_ref")
            if isinstance(meta.get("credentials_ref"), str)
            else None
        )

        token: str | None = None
        if credentials_ref:
            cred = await resolve_credentials(
                backend_name=self._config.identity_credentials_backend,
                target=target,
                credentials_ref=credentials_ref,
            )
            if cred.password is not None:
                token = cred.password.get_secret_value()
        if token is None and self._config.cicd_gato_pat is not None:
            token = self._config.cicd_gato_pat.get_secret_value()
        if not token:
            logger.warning("red_agent.gato.no_token", extra={"target": target.value})
            return []

        # Gato accepts PATs via the GH_TOKEN env var.
        env = {"GH_TOKEN": token}
        scan_target = self._scan_target_argv(target)

        argv = [
            "enumerate",
            *scan_target,
            "--output-json",
            "/workspace/gato.json",
        ]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
            env=env,
            artifacts=["gato.json"],
        )
        return self._parse(result.artifacts.get("gato.json", ""), target)

    def _scan_target_argv(self, target: Target) -> list[str]:
        # The "/" form means org/repo; a bare value means org-wide enum.
        value = target.value.strip()
        if "/" in value:
            return ["--repository", value]
        return ["--target", value]

    def _parse(self, blob: str, target: Target) -> list[Finding]:
        if not blob:
            return []
        try:
            doc = json.loads(blob)
        except json.JSONDecodeError:
            return []
        if not isinstance(doc, dict):
            return []

        findings: list[Finding] = []
        for category, severity in _SEVERITY_BY_CATEGORY.items():
            entries = doc.get(category)
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                repo = entry.get("repository") or entry.get("repo") or target.value
                title = entry.get("title") or category.replace("_", " ").title()
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"Gato {category}: {title}",
                        description=str(
                            entry.get("description")
                            or "Gato flagged a CI/CD misconfiguration; see evidence."
                        ),
                        severity=severity,
                        target=str(repo),
                        endpoint=entry.get("workflow") or entry.get("path"),
                        evidence={
                            "category": category,
                            "details": entry,
                        },
                        cwe="CWE-913" if category == "pwn_request" else "CWE-284",
                    )
                )
        return findings
