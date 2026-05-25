"""NCC Group Principal Mapper (PMapper) AWS IAM privesc scanner.

PMapper builds a directed graph of every IAM principal in an AWS
account, computes the privilege-escalation paths between them, and
emits the result as JSON. We wrap the upstream CLI in a sandboxed
container, parse the per-account graph, and surface each escalation
edge that lands on a high-impact target (Administrator-equivalent
managed policy or wildcard ``*:*`` permission) as a Critical /
High-severity finding.

Credentials follow the standard contract: the AWS account target
carries a ``credentials_ref`` resolved by the credential backend.
The resolver is expected to return a generic credential whose
``password`` field is the AWS *secret access key* and whose
``username`` field is the *access key id*; ``domain`` carries the
session token when present. The runner injects them via env-file
(`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`).
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


_HIGH_IMPACT_ACTIONS = {
    "*",
    "iam:*",
    "iam:CreateAccessKey",
    "iam:UpdateAssumeRolePolicy",
    "iam:AttachUserPolicy",
    "iam:AttachRolePolicy",
    "iam:PutUserPolicy",
    "iam:PutRolePolicy",
    "iam:PassRole",
    "sts:AssumeRole",
    "lambda:UpdateFunctionCode",
    "ec2:RunInstances",
}


_ADMIN_POLICIES = {
    "arn:aws:iam::aws:policy/AdministratorAccess",
    "arn:aws:iam::aws:policy/PowerUserAccess",
    "arn:aws:iam::aws:policy/IAMFullAccess",
}


class PMapperScanner(Scanner):
    name = "pmapper"
    kind = ScannerKind.CSPM
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
        self.image = config.pmapper_image

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if not (self._config.cloud_red_team_enabled and self._config.pmapper_enabled):
            return []
        if target.type != TargetType.CLOUD_ACCOUNT:
            return []

        meta = target.metadata if isinstance(target.metadata, dict) else {}
        credentials_ref = (
            meta.get("credentials_ref")
            if isinstance(meta.get("credentials_ref"), str)
            else None
        )
        if not credentials_ref:
            logger.warning(
                "red_agent.pmapper.no_credentials_ref",
                extra={"target": target.value},
            )
            return []

        cred = await resolve_credentials(
            backend_name=self._config.identity_credentials_backend,
            target=target,
            credentials_ref=credentials_ref,
        )
        if not cred.username or cred.password is None:
            return []

        env = {
            "AWS_ACCESS_KEY_ID": cred.username,
            "AWS_SECRET_ACCESS_KEY": cred.password.get_secret_value(),
        }
        if cred.domain:
            env["AWS_SESSION_TOKEN"] = cred.domain

        argv = [
            "graph",
            "create",
            "--account",
            target.value,
            "--output",
            "/workspace/pmapper.json",
            "--include-unauthorized",
        ]

        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
            env=env,
            artifacts=["pmapper.json"],
        )
        return self._parse(result.artifacts.get("pmapper.json", ""), target)

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
        findings.extend(self._parse_paths(doc, target))
        findings.extend(self._parse_admin_assumable_roles(doc, target))
        return findings

    def _parse_paths(self, doc: dict[str, Any], target: Target) -> list[Finding]:
        out: list[Finding] = []
        paths = doc.get("privesc_paths") or doc.get("paths") or []
        if not isinstance(paths, list):
            return out
        for path in paths:
            if not isinstance(path, dict):
                continue
            source = path.get("source") or path.get("start")
            destination = path.get("destination") or path.get("end")
            edges = path.get("edges") or []
            if not (isinstance(source, str) and isinstance(destination, str)):
                continue
            risky_actions = self._collect_risky_actions(edges)
            severity = (
                Severity.CRITICAL
                if any(a in {"*", "iam:*", "sts:AssumeRole"} for a in risky_actions)
                else Severity.HIGH
            )
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"IAM privesc path: {source} → {destination}",
                    description=(
                        f"PMapper found a privesc chain of {len(edges)} "
                        f"edge(s) from {source} to {destination}."
                    ),
                    severity=severity,
                    target=target.value,
                    endpoint=destination,
                    evidence={
                        "source": source,
                        "destination": destination,
                        "edges": edges,
                        "risky_actions": sorted(risky_actions),
                    },
                    cwe="CWE-269",
                    remediation=(
                        "Remove the wildcard / iam:* / sts:AssumeRole "
                        "edge from the offending principal, or split "
                        "the role into one without privesc reach."
                    ),
                )
            )
        return out

    def _collect_risky_actions(self, edges: list[Any]) -> set[str]:
        actions: set[str] = set()
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            action = edge.get("action") or edge.get("via_action")
            if isinstance(action, str) and action in _HIGH_IMPACT_ACTIONS:
                actions.add(action)
        return actions

    def _parse_admin_assumable_roles(
        self, doc: dict[str, Any], target: Target
    ) -> list[Finding]:
        out: list[Finding] = []
        nodes = doc.get("nodes") or []
        if not isinstance(nodes, list):
            return out
        for node in nodes:
            if not isinstance(node, dict):
                continue
            arn = node.get("arn") or node.get("Arn")
            policies = (
                node.get("attached_policies") or node.get("AttachedPolicies") or []
            )
            if not isinstance(policies, list):
                continue
            attached = {str(p) for p in policies if isinstance(p, str)}
            admin_match = attached & _ADMIN_POLICIES
            if admin_match and isinstance(arn, str):
                out.append(
                    Finding(
                        scanner=self.name,
                        title=f"Principal carries admin-equivalent policy: {arn}",
                        description=(
                            f"Principal {arn} has {sorted(admin_match)} "
                            "directly attached. Any compromise of this "
                            "principal is a full account takeover."
                        ),
                        severity=Severity.HIGH,
                        target=target.value,
                        endpoint=arn,
                        evidence={"policies": sorted(admin_match)},
                        cwe="CWE-269",
                    )
                )
        return out
