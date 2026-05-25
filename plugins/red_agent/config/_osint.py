"""OSINT / EASM configuration mixin.

OSINT scanners enumerate the externally observable attack surface of a
tenant — subdomains, certificate transparency entries, public asset
registries — without sending traffic to the assets themselves. The
discovered hosts are *informational findings* by default; promotion
into ``red_agent_targets`` requires either an explicit operator
action or bug-bounty mode (where scope is delegated to the program
rules).

Disabled by default for two reasons:

1. The scope allowlist model in :class:`_ScopeConfig` is intentionally
   strict; auto-discovered hosts must enter through a controlled gate.
2. Many enterprise customers operate a dedicated EASM (Defender ASM /
   Tenable ASM / Cycognito); the built-in scanners are intended as a
   minimum viable fallback, not a competing product.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class _OSINTConfig(BaseModel):
    osint_enabled: bool = Field(
        default=False,
        description=(
            "Master toggle for OSINT scanners (subfinder, crt.sh). Off "
            "by default. When false the scanners refuse to run and the "
            "auto-target ingestion path is dormant."
        ),
    )
    osint_passive_sources_only: bool = Field(
        default=True,
        description=(
            "Restrict subdomain enumeration to passive sources (CT logs, "
            "public DNS aggregators, search engines). Active resolution "
            "/ brute force require explicit override and are not "
            "appropriate outside intrusive engagements."
        ),
    )
    osint_auto_promote_to_targets: bool = Field(
        default=False,
        description=(
            "When true, hostnames discovered by OSINT scanners are "
            "auto-inserted into ``red_agent_targets`` with state "
            "``discovered`` so they appear in the UI for operator "
            "review. Only safe with bug-bounty mode (program-defined "
            "scope) or with a tight per-engagement allowlist regex."
        ),
    )
    osint_max_results_per_run: int = Field(
        default=500,
        description=(
            "Per-scan ceiling on discovered assets. Protects the DB "
            "and the operator review queue against runaway enumeration "
            "on broad seeds."
        ),
    )
    osint_request_timeout_seconds: float = Field(
        default=30.0,
        description="HTTP timeout per upstream OSINT API request (crt.sh, etc.).",
    )
    osint_subfinder_image: str = Field(
        default="projectdiscovery/subfinder:latest",
        description="Container image for the subfinder runner.",
    )
    osint_external_easm_provider: str | None = Field(
        default=None,
        description=(
            "Identifier of the external EASM connector to merge into "
            "the discovery output. Built-ins: ``none``. Future "
            "candidates: ``defender_easm``, ``tenable_asm``, "
            "``cycognito``. ``None`` (default) disables external "
            "merging."
        ),
    )
    osint_external_easm_api_key: SecretStr | None = Field(
        default=None,
        description="Optional API key forwarded to the configured EASM connector.",
    )
