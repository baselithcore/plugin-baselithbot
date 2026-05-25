"""ScoutSuite multi-cloud auditor adapter.

Prowler covers AWS posture deeply; ScoutSuite is the pragmatic
choice for Azure and GCP coverage. The wrapper invokes
``scout`` with a provider flag, captures the JSON report it writes
into the workdir, and lifts each ``DANGER``-level rule hit into a
finding mapped onto the existing :class:`Severity` ladder.

Targets are :data:`TargetType.CLOUD_ACCOUNT`. The active provider
is read from ``Target.metadata['cloud_provider']`` (one of
``aws|azure|gcp|aliyun|oci``); falling back to the configured
default.
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


_LEVEL_TO_SEVERITY: dict[str, Severity] = {
    "danger": Severity.HIGH,
    "warning": Severity.MEDIUM,
    "info": Severity.INFO,
}


_PROVIDER_ALIASES = {"aws", "azure", "gcp", "aliyun", "oci"}


class ScoutSuiteScanner(Scanner):
    name = "scoutsuite"
    kind = ScannerKind.CSPM
    supports_intensity = (ScanIntensity.PASSIVE, ScanIntensity.ACTIVE)
    requires_network = True
    default_timeout = 2400

    def __init__(
        self,
        sandbox: Any,
        config: RedAgentConfig,
        timeout: int | None = None,
    ) -> None:
        super().__init__(sandbox, timeout=timeout)
        self._config = config
        self.image = config.scoutsuite_image

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if not (
            self._config.cloud_red_team_enabled and self._config.scoutsuite_enabled
        ):
            return []
        if target.type != TargetType.CLOUD_ACCOUNT:
            return []

        meta = target.metadata if isinstance(target.metadata, dict) else {}
        provider = str(
            meta.get("cloud_provider") or self._config.scoutsuite_default_provider
        ).lower()
        if provider not in _PROVIDER_ALIASES:
            logger.warning(
                "red_agent.scoutsuite.unknown_provider",
                extra={"target": target.value, "provider": provider},
            )
            return []

        env = await self._resolve_env(target, provider)
        if env is None:
            return []

        argv = [
            provider,
            "--report-dir",
            "/workspace",
            "--no-browser",
            "--result-format",
            "json",
        ]

        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
            env=env,
            artifacts=[
                f"scoutsuite-results/scoutsuite_results_{provider}-{target.value}.js"
            ],
        )
        return self._parse(result.artifacts, target, provider)

    async def _resolve_env(
        self, target: Target, provider: str
    ) -> dict[str, str] | None:
        meta = target.metadata if isinstance(target.metadata, dict) else {}
        credentials_ref = meta.get("credentials_ref")
        if not isinstance(credentials_ref, str) or not credentials_ref:
            return None
        cred = await resolve_credentials(
            backend_name=self._config.identity_credentials_backend,
            target=target,
            credentials_ref=credentials_ref,
        )
        env: dict[str, str] = {}
        if provider == "aws":
            if not cred.username or cred.password is None:
                return None
            env["AWS_ACCESS_KEY_ID"] = cred.username
            env["AWS_SECRET_ACCESS_KEY"] = cred.password.get_secret_value()
            if cred.domain:
                env["AWS_SESSION_TOKEN"] = cred.domain
        elif provider == "azure":
            if cred.refresh_token is None:
                return None
            env["AZURE_REFRESH_TOKEN"] = cred.refresh_token.get_secret_value()
        elif provider == "gcp":
            if cred.password is None:
                return None
            # password slot carries the JSON service-account key body.
            env["GOOGLE_APPLICATION_CREDENTIALS_JSON"] = (
                cred.password.get_secret_value()
            )
        return env

    def _parse(
        self, artifacts: dict[str, str], target: Target, provider: str
    ) -> list[Finding]:
        # ScoutSuite writes its JSON inside a JS module wrapper. Strip
        # the leading variable assignment if present.
        blob = next(iter(artifacts.values()), "") if artifacts else ""
        if not blob:
            return []
        if blob.lstrip().startswith("scoutsuite_results"):
            blob = blob.split("=", 1)[1].strip().rstrip(";")
        try:
            doc = json.loads(blob)
        except json.JSONDecodeError:
            return []
        if not isinstance(doc, dict):
            return []

        findings: list[Finding] = []
        services = doc.get("services") or {}
        if not isinstance(services, dict):
            return findings
        for svc_name, svc in services.items():
            if not isinstance(svc, dict):
                continue
            findings_block = svc.get("findings") or {}
            if not isinstance(findings_block, dict):
                continue
            for rule_id, rule in findings_block.items():
                if not isinstance(rule, dict):
                    continue
                level = str(rule.get("level", "")).lower()
                if level not in _LEVEL_TO_SEVERITY:
                    continue
                items = rule.get("items") or []
                if not items:
                    continue
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"{provider}/{svc_name}: {rule.get('description') or rule_id}",
                        description=str(
                            rule.get("rationale") or rule.get("description") or rule_id
                        ),
                        severity=_LEVEL_TO_SEVERITY[level],
                        target=target.value,
                        endpoint=str(svc_name),
                        evidence={
                            "rule_id": rule_id,
                            "items": items[:25],
                            "compliance": rule.get("compliance"),
                        },
                        cwe="CWE-732",
                        remediation=str(rule.get("remediation") or ""),
                    )
                )
        return findings
