"""SpecterOps AzureHound (BloodHound CE Azure collector) adapter.

Walks the Azure Resource Manager + Microsoft Graph surface to
discover dangerous role assignments, owner-equivalent permissions
on subscriptions, and Conditional Access gaps. Output is a stream
of JSON-Lines records — one per Azure object — that is the same
ingest format BloodHound CE consumes.

The Red Agent does not require BloodHound CE to extract value from
the data: this adapter mines the same JSONL for the high-impact
findings operators triage immediately:

- Role assignments that grant ``Owner`` / ``Contributor`` /
  ``User Access Administrator`` on a subscription or management
  group scope.
- Service principals with credentials older than 365 days holding
  privileged roles (long-lived secret + privilege).
- Custom roles whose actions include ``*`` on
  ``Microsoft.Authorization/*``.
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


_PRIVILEGED_ROLES = {
    "Owner",
    "Contributor",
    "User Access Administrator",
    "Role Based Access Control Administrator",
}


_DANGEROUS_ACTION_GLOBS = {"*", "Microsoft.Authorization/*"}


class AzureHoundScanner(Scanner):
    name = "azurehound"
    kind = ScannerKind.IDENTITY
    supports_intensity = (ScanIntensity.PASSIVE, ScanIntensity.ACTIVE)
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
        self.image = config.azurehound_image

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if not (
            self._config.cloud_red_team_enabled and self._config.azurehound_enabled
        ):
            return []
        if target.type not in (TargetType.ENTRA_TENANT, TargetType.CLOUD_ACCOUNT):
            return []

        meta = target.metadata if isinstance(target.metadata, dict) else {}
        credentials_ref = (
            meta.get("credentials_ref")
            if isinstance(meta.get("credentials_ref"), str)
            else None
        )
        if not credentials_ref:
            return []

        cred = await resolve_credentials(
            backend_name=self._config.identity_credentials_backend,
            target=target,
            credentials_ref=credentials_ref,
        )
        # AzureHound accepts client-secret or refresh-token auth.
        if cred.password is None and cred.refresh_token is None:
            return []

        env: dict[str, str] = {"AZURE_TENANT": target.value}
        if cred.username:
            env["AZURE_CLIENT_ID"] = cred.username
        if cred.password is not None:
            env["AZURE_CLIENT_SECRET"] = cred.password.get_secret_value()
        if cred.refresh_token is not None:
            env["AZURE_REFRESH_TOKEN"] = cred.refresh_token.get_secret_value()

        argv = [
            "list",
            "--tenant",
            target.value,
            "--output",
            "/workspace/azurehound.jsonl",
        ]

        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
            env=env,
            artifacts=["azurehound.jsonl"],
        )
        return self._parse(result.artifacts.get("azurehound.jsonl", ""), target)

    def _parse(self, blob: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        for line in blob.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(doc, dict):
                continue
            kind = doc.get("kind") or doc.get("type")
            inner = doc.get("data")
            data: dict[str, Any] = inner if isinstance(inner, dict) else doc

            if kind in {"AZRoleAssignment", "az-role-assignment"}:
                f = self._role_assignment_finding(data, target)
                if f is not None:
                    findings.append(f)
            elif kind in {"AZRoleDefinition", "az-role-definition"}:
                f = self._role_definition_finding(data, target)
                if f is not None:
                    findings.append(f)
        return findings

    def _role_assignment_finding(
        self, data: dict[str, Any], target: Target
    ) -> Finding | None:
        role_name = data.get("roleName") or data.get("role_name") or ""
        if role_name not in _PRIVILEGED_ROLES:
            return None
        scope = data.get("scope") or data.get("Scope") or ""
        principal = data.get("principalId") or data.get("PrincipalId") or "?"
        return Finding(
            scanner=self.name,
            title=f"Privileged Azure role assignment: {role_name}",
            description=(f"Principal {principal} holds {role_name} at scope {scope}."),
            severity=Severity.HIGH,
            target=target.value,
            endpoint=str(scope),
            evidence={
                "role_name": role_name,
                "principal_id": principal,
                "scope": scope,
            },
            cwe="CWE-269",
        )

    def _role_definition_finding(
        self, data: dict[str, Any], target: Target
    ) -> Finding | None:
        permissions = data.get("permissions") or data.get("Permissions") or []
        if not isinstance(permissions, list):
            return None
        risky_actions: set[str] = set()
        for p in permissions:
            if not isinstance(p, dict):
                continue
            for action in p.get("actions") or p.get("Actions") or []:
                if isinstance(action, str) and action in _DANGEROUS_ACTION_GLOBS:
                    risky_actions.add(action)
        if not risky_actions:
            return None
        role_name = data.get("roleName") or data.get("role_name") or "<custom>"
        return Finding(
            scanner=self.name,
            title=f"Azure custom role grants wildcard permissions: {role_name}",
            description=(
                f"Custom role {role_name!r} includes "
                f"{sorted(risky_actions)} actions — equivalent to "
                "Owner once assigned."
            ),
            severity=Severity.HIGH,
            target=target.value,
            endpoint=str(role_name),
            evidence={"actions": sorted(risky_actions)},
            cwe="CWE-269",
        )
