"""Sandbox / scope / scanner / reasoning configuration mixins."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class _SandboxConfig(BaseModel):
    sandbox_provider: Literal["docker", "sbx", "k8s", "auto"] = Field(
        default="auto",
        description=(
            "Sandbox backend used to execute scanner binaries. ``auto`` "
            "picks docker when scanner images are pre-pulled locally, "
            "otherwise falls back to MockSandboxRunner. Set to ``k8s`` "
            "to dispatch each scanner as a Kubernetes Job (requires the "
            "``baselith-core[k8s]`` extra and the cluster credentials in "
            "the runtime environment)."
        ),
    )
    sandbox_k8s_namespace: str = Field(
        default="red-agent",
        description=(
            "Kubernetes namespace into which scanner Jobs are created. "
            "Operator must create the namespace + RBAC + NetworkPolicy "
            "manifests upfront."
        ),
    )
    sandbox_k8s_service_account: str | None = Field(
        default=None,
        description=(
            "Service account attached to scanner pods. None → use the "
            "namespace default. Use a least-privilege SA bound to a Role "
            "that allows only ``pods/log`` reads from this plugin."
        ),
    )
    sandbox_k8s_cpu_limit: str = Field(
        default="1",
        description="CPU resource limit applied to scanner Jobs (Kubernetes quantity).",
    )
    sandbox_k8s_memory_limit: str = Field(
        default="1Gi",
        description="Memory resource limit applied to scanner Jobs (Kubernetes quantity).",
    )
    sandbox_network: bool = Field(
        default=True,
        description="Allow egress network from sandbox during scan (required for active recon).",
    )
    sandbox_timeout_seconds: int = Field(
        default=900,
        description="Per-scan hard timeout. Scanner is killed past this.",
    )
    use_mock_scanners: bool = Field(
        default=False,
        description=(
            "Dev-only: replace the docker SandboxRunner with a deterministic "
            "MockSandboxRunner that returns canned scanner output. Lets the "
            "UI and lifecycle work end-to-end without docker images, network "
            "or scanner binaries. Never enable in production."
        ),
    )
    prepull_scanner_images: bool = Field(
        default=False,
        description=(
            "On plugin init, kick off background ``docker pull`` for every "
            "enabled scanner image so the first real scan does not stall on "
            "a registry round-trip. Best-effort: failures are logged."
        ),
    )


class _ScopeConfig(BaseModel):
    scope_allowlist: list[str] = Field(
        default_factory=list,
        description=(
            "Domains, IPs, or CIDRs explicitly authorized for scanning. "
            "Targets outside the allowlist are rejected unless bug_bounty_mode is enabled."
        ),
    )
    bug_bounty_mode: bool = Field(
        default=False,
        description=(
            "Bypass scope_allowlist enforcement and rely on bug-bounty in-scope policy "
            "fetched from upstream program (HackerOne/Bugcrowd). Requires program_id."
        ),
    )
    bug_bounty_program_id: str | None = Field(default=None)
    bug_bounty_api_token: SecretStr | None = Field(default=None)

    allow_internal_targets: bool = Field(
        default=False,
        description=(
            "Override SSRF guard to allow loopback/private/link-local targets. "
            "Mirrors BASELITH_BROWSER_ALLOW_INTERNAL — for trusted local lab only."
        ),
    )

    require_hitl_for_active: bool = Field(
        default=True,
        description="Active/intrusive scans (sqlmap exploit, fuzz) require human approval.",
    )


class _GraphConfig(BaseModel):
    graph_backend: Literal["falkordb"] = Field(default="falkordb")
    graph_host: str = Field(default="localhost")
    graph_port: int = Field(default=6379)
    graph_name: str = Field(default="red_agent_vulns")
    graph_password: SecretStr | None = Field(default=None)


class _ScannerConfig(BaseModel):
    max_concurrent_scans: int = Field(default=4)
    audit_retention_days: int = Field(default=365)

    enabled_scanners: list[str] = Field(
        default_factory=lambda: [
            "nmap",
            "nuclei",
            "zap",
            "trivy",
            "self_posture",
            "binary_analyzer",
        ],
        description=(
            "Scanners enabled by default. sqlmap requires explicit opt-in + HITL. "
            "Newer scanners (sslyze, secure_headers, semgrep, gitleaks, syft, "
            "grype) are off by default — operators add them explicitly to keep "
            "the existing scan profile stable across upgrades."
        ),
    )

    scanner_timeouts: dict[str, int] = Field(
        default_factory=lambda: {
            "nmap": 600,
            "nuclei": 900,
            "zap": 1800,
            "sqlmap": 1800,
            "trivy": 900,
            "sslyze": 600,
            "secure_headers": 60,
            "semgrep": 1800,
            "gitleaks": 900,
            "syft": 900,
            "grype": 1200,
            "checkov": 900,
            "prowler": 1800,
            "kube_bench": 600,
            "schemathesis": 1800,
            "llm_prompt_injection": 1800,
            "llm_tool_abuse": 1800,
            "llm_data_leakage": 1800,
            "llm_output_handling": 1800,
            "self_posture": 120,
            "binary_analyzer": 300,
        },
        description=(
            "Per-scanner hard timeout (seconds). Falls back to "
            "sandbox_timeout_seconds when a scanner is missing here."
        ),
    )

    scanner_output_max_bytes: int = Field(
        default=64 * 1024,
        description=(
            "Max bytes of raw scanner output stored in Finding.evidence/raw "
            "to bound memory and JSONB size; full output stays in the audit "
            "logs but the persisted finding only keeps a head slice."
        ),
    )


class _ReasoningConfig(BaseModel):
    multi_step_chains: bool = Field(
        default=False,
        description=(
            "Enable multi-step attack chaining. Off = deterministic "
            "single-pass behavior. On = orchestrator runs ChainingPlanner: "
            "recon first, then DAST against newly discovered endpoints."
        ),
    )
    chain_max_iterations: int = Field(
        default=3,
        description="Bound multi-step chains to this many planner steps.",
    )
    validated_impact_only: bool = Field(
        default=False,
        description=(
            "When true, drop findings that are not 'validated impact': "
            "info/low severity without an active confirmation marker are "
            "discarded. Reduces noise — keep only proven exploitable risk."
        ),
    )
    validated_impact_min_cvss: float = Field(
        default=4.0,
        description=(
            "Minimum CVSS score required for a finding to count as "
            "validated when validated_impact_only is enabled."
        ),
    )
