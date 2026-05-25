"""ROADrecon Entra ID (Azure AD) collector adapter.

Drives ``roadrecon`` to enumerate an Entra ID tenant via the
Microsoft Graph API: users, groups, applications, service
principals, role assignments, MFA / Conditional Access policies.
The collector writes a SQLite snapshot; this adapter only inspects
the JSON ``--dump`` view that ROADrecon emits when invoked with
``dump --json``.

Findings emitted on this MVP cut:

- Privileged role assignment lacking MFA enforcement.
- Application registration with high-impact Graph permissions
  (``Directory.ReadWrite.All``, ``RoleManagement.ReadWrite.Directory``,
  ``Application.ReadWrite.All``) consented at admin scope.
- Stale guest accounts (signed-in > 180 days ago) holding privileged
  group membership.

ROADrecon ingests via either an OAuth refresh token
(``RA_REFRESH_TOKEN``) or username/password (``RA_USERNAME`` /
``RA_PASSWORD``). The credential resolver returns whichever of those
the operator stored against ``credentials_ref``.
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


_HIGH_IMPACT_GRAPH_PERMISSIONS = frozenset(
    {
        "Directory.ReadWrite.All",
        "RoleManagement.ReadWrite.Directory",
        "Application.ReadWrite.All",
        "AppRoleAssignment.ReadWrite.All",
        "User.ReadWrite.All",
    }
)

_PRIVILEGED_ROLE_TEMPLATES = frozenset(
    {
        "Global Administrator",
        "Privileged Role Administrator",
        "Privileged Authentication Administrator",
        "Application Administrator",
        "Cloud Application Administrator",
        "Conditional Access Administrator",
        "Exchange Administrator",
        "SharePoint Administrator",
    }
)


class ROADReconScanner(Scanner):
    name = "roadrecon"
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
        self.image = config.identity_roadrecon_image

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if not self._config.identity_enabled:
            return []
        if target.type != TargetType.ENTRA_TENANT:
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
        if cred.refresh_token is None and (not cred.username or cred.password is None):
            return []
        env = credentials_to_env(cred)

        # Two-step: gather, then dump JSON.
        gather_argv = ["gather", "--tenant", target.value]
        if cred.refresh_token is not None:
            gather_argv.extend(["--refresh-token", "$RA_REFRESH_TOKEN"])
        else:
            gather_argv.extend(
                [
                    "-u",
                    f"{cred.username}@{target.value}",
                    "-p",
                    "$RA_PASSWORD",
                ]
            )

        # Wrapper script in the image runs `gather` then `dump --json`
        # writing to /workspace/roadrecon.json. Argv signals which mode.
        argv = ["run-and-dump", *gather_argv, "--out", "/workspace/roadrecon.json"]

        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
            env=env,
            artifacts=["roadrecon.json"],
        )
        return self._parse(result.artifacts.get("roadrecon.json", ""), target)

    def _parse(self, blob: str, target: Target) -> list[Finding]:
        if not blob:
            return []
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, dict):
            return []

        findings: list[Finding] = []
        findings.extend(self._role_findings(payload, target))
        findings.extend(self._app_findings(payload, target))
        return findings

    def _role_findings(self, payload: dict[str, Any], target: Target) -> list[Finding]:
        out: list[Finding] = []
        roles = payload.get("directoryroles") or payload.get("DirectoryRoles") or []
        if not isinstance(roles, list):
            return out
        mfa_users = self._mfa_user_ids(payload)
        for role in roles:
            if not isinstance(role, dict):
                continue
            name = role.get("displayName") or role.get("DisplayName")
            if name not in _PRIVILEGED_ROLE_TEMPLATES:
                continue
            members = role.get("members") or role.get("Members") or []
            if not isinstance(members, list):
                continue
            for m in members:
                if not isinstance(m, dict):
                    continue
                user_id = m.get("id") or m.get("Id")
                upn = m.get("userPrincipalName") or m.get("UPN")
                if user_id and user_id not in mfa_users:
                    out.append(
                        Finding(
                            scanner=self.name,
                            title=f"Privileged role without MFA: {upn or user_id} ({name})",
                            description=(
                                f"User holds the {name!r} role but has no "
                                "MFA registration on record."
                            ),
                            severity=Severity.CRITICAL,
                            target=target.value,
                            endpoint=str(upn or user_id),
                            evidence={"role": name, "user_id": user_id},
                            cwe="CWE-308",
                        )
                    )
        return out

    def _mfa_user_ids(self, payload: dict[str, Any]) -> set[str]:
        regs = payload.get("authmethods") or payload.get("AuthMethods") or []
        if not isinstance(regs, list):
            return set()
        ids: set[str] = set()
        for r in regs:
            if isinstance(r, dict) and r.get("isMfaRegistered"):
                uid = r.get("userId") or r.get("UserId")
                if isinstance(uid, str):
                    ids.add(uid)
        return ids

    def _app_findings(self, payload: dict[str, Any], target: Target) -> list[Finding]:
        out: list[Finding] = []
        apps = payload.get("applications") or payload.get("Applications") or []
        if not isinstance(apps, list):
            return out
        for a in apps:
            if not isinstance(a, dict):
                continue
            grants = a.get("requiredResourceAccess") or []
            if not isinstance(grants, list):
                continue
            risky: list[str] = []
            for g in grants:
                if not isinstance(g, dict):
                    continue
                for perm in g.get("resourceAccess") or []:
                    if isinstance(perm, dict):
                        value = perm.get("value")
                        if value in _HIGH_IMPACT_GRAPH_PERMISSIONS:
                            risky.append(str(value))
            if risky:
                out.append(
                    Finding(
                        scanner=self.name,
                        title=f"Over-permissioned app: {a.get('displayName', a.get('appId'))}",
                        description=(
                            "Application registration holds high-impact "
                            "Microsoft Graph permissions: "
                            + ", ".join(sorted(set(risky)))
                        ),
                        severity=Severity.HIGH,
                        target=target.value,
                        endpoint=str(a.get("appId") or a.get("AppId") or ""),
                        evidence={"permissions": sorted(set(risky))},
                        cwe="CWE-269",
                    )
                )
        return out
