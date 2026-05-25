"""Auto-remediation, differential, risk, compliance, reachability, VEX mixins."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class _AutoRemediationConfig(BaseModel):
    auto_remediation_enabled: bool = Field(
        default=False,
        description=(
            "Mount ``POST /red-agent/findings/{id}/auto-remediate`` so a "
            "security operator can open a fix-PR on the upstream "
            "repository for an SCA finding. Disabled by default — "
            "requires ``auto_remediation_github_token`` and per-finding "
            "repo metadata (``evidence.repo_owner``, ``repo_name``)."
        ),
    )
    auto_remediation_github_token: SecretStr | None = Field(
        default=None,
        description=(
            "GitHub PAT or fine-grained token with ``contents:write`` "
            "and ``pull-requests:write`` scope on the target repos."
        ),
    )
    auto_remediation_request_timeout_seconds: float = Field(
        default=15.0,
        description="HTTP timeout per GitHub API call.",
    )


class _DifferentialConfig(BaseModel):
    differential_enabled: bool = Field(
        default=False,
        description=(
            "Skip scanners whose input fingerprint matches a recent "
            "successful run. The fingerprint covers target + scanner + "
            "intensity + relevant target metadata (commit SHA, image "
            "digest, IaC tree hash). Findings are reused from the cached "
            "scan; the new scan emits an audit event listing the skips."
        ),
    )
    differential_ttl_seconds: int = Field(
        default=3600,
        description=(
            "Maximum age of a cached scan result that can be reused. "
            "Default 1h — short enough that threat-intel refresh on the "
            "next run still propagates, long enough to skip back-to-back "
            "duplicate scans during CI."
        ),
    )


class _RiskComplianceConfig(BaseModel):
    risk_scoring_enabled: bool = Field(
        default=True,
        description=(
            "Compute the unified VPR-style risk score (0..10) per finding "
            "from CVSS + EPSS + KEV + reachability + asset criticality + "
            "exposure. Lands on ``Finding.risk_score`` and "
            "``Finding.evidence['risk_band']``."
        ),
    )
    risk_kev_multiplier: float = Field(
        default=1.5,
        description="Multiplier applied when the finding's CVE is on the CISA KEV catalog.",
    )
    risk_max_epss_multiplier: float = Field(
        default=1.5,
        description=(
            "Maximum EPSS multiplier (linearly interpolated 1.0 → "
            "max as EPSS goes 0 → 1)."
        ),
    )
    compliance_mapper_enabled: bool = Field(
        default=True,
        description=(
            "Map findings to CIS / PCI DSS 4.0 / NIST 800-53 / ISO 27001 / "
            "SOC 2 control IDs via CWE lookup + scanner-specific compliance "
            "metadata (Checkov / Prowler / kube-bench). Output lands on "
            "``Finding.controls``."
        ),
    )


class _ReachabilityConfig(BaseModel):
    reachability_enabled: bool = Field(
        default=False,
        description=(
            "Annotate SCA findings (Trivy/Grype/Syft) with whether the "
            "vulnerable package is referenced anywhere in the repo's "
            "source tree. Enables Snyk-style noise reduction. Requires "
            "the scan target to expose ``Target.metadata['repo_path']`` "
            "or be a ``REPO`` / ``IAC`` target."
        ),
    )
    reachability_drop_unreachable: bool = Field(
        default=False,
        description=(
            "When true, findings with reachable=False and severity at or "
            "below ``reachability_drop_max_severity`` are dropped from "
            "the scan result. KEV-listed CVEs are *never* dropped."
        ),
    )
    reachability_drop_max_severity: Literal["info", "low", "medium", "high"] = Field(
        default="medium",
        description=(
            "Maximum severity at which an unreachable finding is dropped "
            "when ``reachability_drop_unreachable`` is true."
        ),
    )
    reachability_max_files: int = Field(
        default=5000,
        description=(
            "Hard cap on files inspected per repo to keep walk time "
            "bounded on large monorepos."
        ),
    )


class _VEXConfig(BaseModel):
    vex_enabled: bool = Field(
        default=False,
        description=(
            "Ingest OpenVEX 0.2.0 / CycloneDX VEX 1.6 documents from "
            "``vex_directory`` and suppress findings whose vendor "
            "attestation marks them as ``not_affected`` or ``fixed``. "
            "Fail-open: parse errors leave the findings list unchanged."
        ),
    )
    vex_directory: str = Field(
        default="./var/red_agent/vex",
        description=(
            "Filesystem directory scanned for VEX documents (``*.json``). "
            "Documents are reloaded on mtime change so operators can drop "
            "in new attestations without restarting the plugin."
        ),
    )
    vex_suppress_not_affected: bool = Field(
        default=True,
        description="Drop findings whose VEX status is ``not_affected``/``false_positive``.",
    )
    vex_suppress_fixed: bool = Field(
        default=True,
        description=(
            "Drop findings whose VEX status is ``fixed``/``resolved``/"
            "``resolved_with_pedigree``. Disable to keep historical "
            "tracking of resolved CVEs."
        ),
    )
