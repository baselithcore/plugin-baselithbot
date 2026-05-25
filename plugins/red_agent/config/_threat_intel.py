"""Multi-source threat-intel configuration mixin.

GreyNoise covers internet-wide noise / known-scanners. This mixin
adds the four other sources operators ask for in the field:

- VirusTotal — community detections for IP / domain / file hashes.
- Shodan — historical port + banner data for IPs.
- Censys — independent corroboration of Shodan, plus richer TLS
  certificate metadata.
- AlienVault OTX — community-curated pulses tying IPs / CVEs back
  to named threat actors.

Each enricher is fail-open and off by default — most customers
already pay one or two of these vendors and don't want the extra
egress / cost from running everything at once.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class _ThreatIntelConfig(BaseModel):
    virustotal_enricher_enabled: bool = Field(
        default=False,
        description="Enable VirusTotal IP/domain/hash enrichment.",
    )
    virustotal_api_key: SecretStr | None = Field(
        default=None,
        description="VirusTotal v3 API key.",
    )
    virustotal_request_timeout_seconds: float = Field(
        default=15.0, description="HTTP timeout per VirusTotal request."
    )
    virustotal_max_concurrent_requests: int = Field(
        default=4, description="Concurrency cap for VirusTotal lookups."
    )

    shodan_enricher_enabled: bool = Field(
        default=False,
        description="Enable Shodan host enrichment for IP-typed findings.",
    )
    shodan_api_key: SecretStr | None = Field(
        default=None, description="Shodan API key."
    )
    shodan_request_timeout_seconds: float = Field(
        default=15.0, description="HTTP timeout per Shodan request."
    )
    shodan_max_concurrent_requests: int = Field(
        default=4, description="Concurrency cap for Shodan lookups."
    )

    censys_enricher_enabled: bool = Field(
        default=False,
        description="Enable Censys host enrichment for IP-typed findings.",
    )
    censys_api_id: str | None = Field(default=None, description="Censys API ID.")
    censys_api_secret: SecretStr | None = Field(
        default=None, description="Censys API secret."
    )
    censys_request_timeout_seconds: float = Field(
        default=15.0, description="HTTP timeout per Censys request."
    )
    censys_max_concurrent_requests: int = Field(
        default=4, description="Concurrency cap for Censys lookups."
    )

    otx_enricher_enabled: bool = Field(
        default=False,
        description=(
            "Enable AlienVault OTX pulse enrichment. Free tier; an "
            "API key only raises rate limits."
        ),
    )
    otx_api_key: SecretStr | None = Field(
        default=None, description="OTX API key (optional)."
    )
    otx_request_timeout_seconds: float = Field(
        default=15.0, description="HTTP timeout per OTX request."
    )
    otx_max_concurrent_requests: int = Field(
        default=4, description="Concurrency cap for OTX lookups."
    )
