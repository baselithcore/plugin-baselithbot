"""Threat-intel enrichment configuration mixins."""

from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class _EPSSKEVConfig(BaseModel):
    epss_kev_enricher_enabled: bool = Field(
        default=True,
        description=(
            "Annotate CVE-bearing findings with FIRST EPSS scores and CISA "
            "KEV listing. Fail-open: any HTTP/JSON error returns the "
            "findings list untouched. KEV catalog cached in-process for "
            "``epss_kev_cache_ttl_seconds`` (default 1h)."
        ),
    )
    epss_kev_bump_severity_on_kev: bool = Field(
        default=True,
        description=(
            "When true, findings whose CVE is on the CISA KEV catalog "
            "are bumped to severity HIGH (if currently lower). Real-world "
            "exploitation outranks CVSS for prioritization."
        ),
    )
    epss_kev_high_epss_threshold: float = Field(
        default=0.5,
        description=(
            "EPSS score above this threshold bumps the finding's severity "
            "by one step. 0.5 ≈ top 5% of CVEs by predicted exploitation."
        ),
    )
    epss_kev_cache_ttl_seconds: float = Field(
        default=3600.0,
        description="Time-to-live for the in-memory KEV catalog cache (seconds).",
    )
    epss_kev_request_timeout_seconds: float = Field(
        default=10.0,
        description="HTTP timeout per upstream EPSS/KEV request.",
    )

    attack_mapper_enabled: bool = Field(
        default=True,
        description=(
            "Annotate findings with MITRE ATT&CK technique IDs derived "
            "from CWE. Pure local lookup — no network, never fails."
        ),
    )


class _OSVConfig(BaseModel):
    osv_enricher_enabled: bool = Field(
        default=False,
        description=(
            "Annotate SCA findings with OSV.dev advisory data: cross-"
            "ecosystem fixed_in versions, GHSA IDs, advisory references. "
            "Free public API; off by default to keep first-run scans "
            "self-contained. Fail-open."
        ),
    )
    osv_request_timeout_seconds: float = Field(
        default=10.0,
        description="HTTP timeout per OSV API request.",
    )
    osv_max_concurrent_requests: int = Field(
        default=8,
        description="Concurrency cap for OSV lookups within a single scan iteration.",
    )


class _GreyNoiseConfig(BaseModel):
    greynoise_enricher_enabled: bool = Field(
        default=False,
        description=(
            "Annotate IP-target findings with GreyNoise reputation data "
            "(noise / riot / classification). Free community endpoint, "
            "rate-limited; provide an API key via "
            "``RED_AGENT_GREYNOISE_API_KEY`` for higher quotas."
        ),
    )
    greynoise_api_key: SecretStr | None = Field(
        default=None,
        description="Optional GreyNoise API key (premium tier).",
    )
    greynoise_request_timeout_seconds: float = Field(
        default=10.0,
        description="HTTP timeout per GreyNoise API request.",
    )
    greynoise_max_concurrent_requests: int = Field(
        default=4,
        description="Concurrency cap for GreyNoise lookups.",
    )
