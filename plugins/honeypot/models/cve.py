"""CVE Data Models.

Structured models for Common Vulnerabilities and Exposures data
from the National Vulnerability Database (NVD).
"""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CVEData(BaseModel):
    """Structured CVE data from NVD."""

    cve_id: str = Field(..., description="CVE identifier (e.g., CVE-2021-44228)")
    description: str = Field(default="", description="CVE description")
    published_date: Optional[datetime] = Field(
        default=None, description="Date when CVE was published"
    )
    last_modified: Optional[datetime] = Field(
        default=None, description="Date when CVE was last modified"
    )

    # CVSS Scoring
    cvss_v3_score: Optional[float] = Field(
        default=None, ge=0.0, le=10.0, description="CVSS v3 base score"
    )
    cvss_v3_severity: Optional[str] = Field(
        default=None, description="CVSS v3 severity (CRITICAL, HIGH, MEDIUM, LOW)"
    )
    cvss_v2_score: Optional[float] = Field(
        default=None, ge=0.0, le=10.0, description="CVSS v2 base score"
    )

    # Weakness and Platform
    cwe_ids: List[str] = Field(default_factory=list, description="Associated CWE IDs")
    cpe_uris: List[str] = Field(
        default_factory=list, description="Common Platform Enumeration URIs"
    )

    # References and Resources
    references: List[str] = Field(default_factory=list, description="Reference URLs")

    # Metadata
    source: str = Field(default="nvd", description="Data source (nvd, cache, static)")
    cached: bool = Field(default=False, description="Whether data came from cache")
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When data was fetched",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cve_id": "CVE-2021-44228",
                "description": "Apache Log4j2 JNDI features do not protect against attacker controlled LDAP...",
                "published_date": "2021-12-10T10:15:00",
                "cvss_v3_score": 10.0,
                "cvss_v3_severity": "CRITICAL",
                "cwe_ids": ["CWE-917", "CWE-20"],
                "references": ["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"],
            }
        }
    )


class CVESearchResult(BaseModel):
    """Result from a CVE search query."""

    query: str = Field(..., description="Original search query")
    query_type: str = Field(
        ..., description="Type of query (cve_id, cwe, keyword, recent)"
    )
    results: List[CVEData] = Field(
        default_factory=list, description="Matching CVE records"
    )
    total_found: int = Field(default=0, description="Total results found")
    cached: bool = Field(default=False, description="Whether results came from cache")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Query timestamp",
    )
    latency_ms: Optional[float] = Field(
        default=None, description="Query latency in milliseconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "CWE-89",
                "query_type": "cwe",
                "results": [],
                "total_found": 42,
                "cached": True,
                "timestamp": "2024-01-16T10:30:00",
                "latency_ms": 12.5,
            }
        }
    )


class CVELookupStats(BaseModel):
    """CVE service statistics."""

    total_lookups: int = Field(default=0, description="Total CVE lookups performed")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, description="Number of cache misses")
    api_calls: int = Field(default=0, description="Number of NVD API calls")
    errors: int = Field(default=0, description="Number of lookup errors")
    avg_latency_ms: float = Field(default=0.0, description="Average latency")

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_lookups == 0:
            return 0.0
        return (self.cache_hits / self.total_lookups) * 100

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_lookups": 1000,
                "cache_hits": 850,
                "cache_misses": 150,
                "api_calls": 150,
                "errors": 5,
                "avg_latency_ms": 45.2,
            }
        }
    )
