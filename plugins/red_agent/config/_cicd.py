"""CI/CD red-team configuration mixin.

CI/CD scanners audit the build pipeline for the same kinds of
misconfigurations that adversaries exploit in the wild today —
self-hosted runner abuse, ``pull_request_target`` script injection,
unpinned third-party actions, dependency confusion. Three scanners
share this mixin:

- ``gato`` (Praetorian) — runs end-to-end against a GitHub org/repo
  and surfaces actionable findings (runner takeover, secret
  exfiltration paths). Requires a GitHub PAT.
- ``workflow_audit`` — static analysis of ``.github/workflows/*.yml``
  performed locally on a repo checkout. Network-free.
- ``dependency_confusion`` — checks package manifests against the
  public registries to detect packages that an attacker could
  squat. Network is read-only against npm/PyPI metadata endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class _CICDConfig(BaseModel):
    cicd_enabled: bool = Field(
        default=False,
        description=(
            "Master toggle for CI/CD red-team scanners. Off by "
            "default. Each scanner has its own enable flag too — the "
            "master toggle is the single switch operators flip per "
            "engagement."
        ),
    )
    cicd_gato_enabled: bool = Field(
        default=False,
        description="Enable the Gato scanner (requires PAT).",
    )
    cicd_gato_image: str = Field(
        default="ghcr.io/praetorian-inc/gato:latest",
        description="Container image for Gato.",
    )
    cicd_gato_pat: SecretStr | None = Field(
        default=None,
        description=(
            "GitHub Personal Access Token Gato uses to enumerate the "
            "org/repo. Read-only scope is sufficient (``read:org``, "
            "``repo:read``, ``actions:read``). Override per-scan via "
            "``Target.metadata['credentials_ref']``."
        ),
    )
    cicd_workflow_audit_enabled: bool = Field(
        default=True,
        description=(
            "Enable the local GitHub-Actions workflow auditor. "
            "Network-free; safe to keep on."
        ),
    )
    cicd_dependency_confusion_enabled: bool = Field(
        default=True,
        description=(
            "Enable the dependency-confusion scanner. Reads npm/PyPI "
            "metadata over HTTPS; no traffic to the target."
        ),
    )
    cicd_dependency_confusion_request_timeout_seconds: float = Field(
        default=15.0,
        description="HTTP timeout per registry lookup.",
    )
    cicd_dependency_confusion_max_concurrent_requests: int = Field(
        default=8,
        description="Concurrency cap for registry lookups within one scan.",
    )
