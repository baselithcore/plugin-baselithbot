"""CVE Hunter Data Models.

Pydantic models for CVE data representation and API responses.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Timezone-aware UTC `datetime.now()` for default_factory fields."""
    return datetime.now(timezone.utc)


class CVESeverity(str, Enum):
    """CVE severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class CVESource(str, Enum):
    """Source of CVE information."""

    NVD = "nvd"
    MITRE = "mitre"
    GITHUB = "github"
    EXPLOIT_DB = "exploit_db"
    CISA_KEV = "cisa_kev"
    OSV = "osv"
    DISCOVERED = "discovered"


class CVSSVector(BaseModel):
    """CVSS scoring vector."""

    version: str = Field(default="3.1", description="CVSS version")
    vector_string: Optional[str] = Field(default=None, description="CVSS vector string")
    base_score: float = Field(default=0.0, ge=0.0, le=10.0)
    exploitability_score: Optional[float] = Field(default=None)
    impact_score: Optional[float] = Field(default=None)


class AffectedProduct(BaseModel):
    """Product affected by a CVE."""

    vendor: str
    product: str
    versions: List[str] = Field(default_factory=list)
    cpe: Optional[str] = Field(default=None, description="CPE identifier")


class CVEReference(BaseModel):
    """Reference link for a CVE."""

    url: str
    source: str
    tags: List[str] = Field(default_factory=list)


class CVERecord(BaseModel):
    """Complete CVE record."""

    cve_id: str = Field(..., description="CVE identifier (e.g., CVE-2024-12345)")
    title: Optional[str] = Field(default=None, description="Brief title")
    description: str = Field(default="", description="Full description")
    severity: CVESeverity = Field(default=CVESeverity.NONE)
    cvss: Optional[CVSSVector] = Field(default=None)
    source: CVESource = Field(default=CVESource.NVD)
    published_date: Optional[datetime] = Field(default=None)
    last_modified: Optional[datetime] = Field(default=None)
    affected_products: List[AffectedProduct] = Field(default_factory=list)
    references: List[CVEReference] = Field(default_factory=list)
    cwe_ids: List[str] = Field(default_factory=list, description="CWE identifiers")
    exploit_available: bool = Field(default=False)
    patch_available: bool = Field(default=False)
    ai_summary: Optional[str] = Field(default=None, description="AI-generated summary")
    raw_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Original source data"
    )

    @property
    def cvss_score(self) -> float:
        """Get CVSS base score."""
        return self.cvss.base_score if self.cvss else 0.0


class VulnerabilityAlert(BaseModel):
    """Alert for a detected vulnerability."""

    alert_id: str = Field(..., description="Unique alert identifier")
    cve: CVERecord
    alert_type: str = Field(
        default="new_cve", description="Type: new_cve, severity_change, exploit_found"
    )
    priority: int = Field(default=1, ge=1, le=5, description="1=highest priority")
    created_at: datetime = Field(default_factory=_utcnow)
    acknowledged: bool = Field(default=False)
    acknowledged_by: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class AgentTaskStatus(str, Enum):
    """Agent task status."""

    IDLE = "idle"
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    DISCOVERING = "discovering"
    ERROR = "error"


class CVEAgentStatus(BaseModel):
    """Status of a CVE Hunter agent."""

    agent_id: str
    agent_type: str = Field(description="scanner, analyzer, or discovery")
    status: AgentTaskStatus = Field(default=AgentTaskStatus.IDLE)
    current_task: Optional[str] = Field(default=None)
    tasks_completed: int = Field(default=0)
    tasks_failed: int = Field(default=0)
    last_active: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


class ScanResult(BaseModel):
    """Result of a CVE scan operation."""

    scan_id: str
    source: CVESource
    started_at: datetime
    completed_at: Optional[datetime] = Field(default=None)
    success: bool = Field(default=False)
    cves_found: int = Field(default=0)
    new_cves: int = Field(default=0)
    updated_cves: int = Field(default=0)
    errors: List[str] = Field(default_factory=list)
    duration_seconds: Optional[float] = Field(default=None)


class SwarmStatus(BaseModel):
    """Overall swarm status."""

    active_agents: int = Field(default=0)
    queued_tasks: int = Field(default=0)
    completed_tasks: int = Field(default=0)
    failed_tasks: int = Field(default=0)
    agents: List[CVEAgentStatus] = Field(default_factory=list)
    last_scan: Optional[datetime] = Field(default=None)
    is_scanning: bool = Field(default=False)


class CVEStats(BaseModel):
    """Aggregated CVE statistics."""

    total_cves: int = Field(default=0)
    critical_count: int = Field(default=0)
    high_count: int = Field(default=0)
    medium_count: int = Field(default=0)
    low_count: int = Field(default=0)
    with_exploit: int = Field(default=0)
    with_patch: int = Field(default=0)
    discovered_today: int = Field(default=0)
    discovered_this_week: int = Field(default=0)
    active_alerts: int = Field(default=0)
    sources_active: List[str] = Field(default_factory=list)


class SASTFinding(BaseModel):
    """Finding from a static code scan."""

    finding_id: str
    file_path: str
    pattern: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    severity: CVESeverity = Field(default=CVESeverity.MEDIUM)
    context: Optional[str] = Field(default=None)
    source: str = Field(default="sast")
    feedback: Optional[str] = Field(
        default=None, description="confirmed/false_positive"
    )
    engine: Optional[str] = Field(default=None, description="pattern or semgrep")
    rule_id: Optional[str] = Field(default=None, description="Semgrep rule id")


class SASTScanResult(BaseModel):
    """Result of a SAST scan operation."""

    scan_id: str
    started_at: datetime
    completed_at: Optional[datetime] = Field(default=None)
    files_scanned: int = Field(default=0)
    findings_count: int = Field(default=0)
    findings: List[SASTFinding] = Field(default_factory=list)
    duration_seconds: Optional[float] = Field(default=None)


class DASTFinding(BaseModel):
    """Finding from a dynamic scan."""

    finding_id: str
    url: str
    pattern: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    severity: CVESeverity = Field(default=CVESeverity.MEDIUM)
    context: Optional[str] = Field(default=None)
    source: str = Field(default="dast")
    engine: Optional[str] = Field(default=None, description="crawler or zap")
    rule_id: Optional[str] = Field(default=None, description="ZAP plugin id")
    feedback: Optional[str] = Field(
        default=None, description="confirmed/false_positive"
    )


class DASTScanResult(BaseModel):
    """Result of a DAST scan operation."""

    scan_id: str
    started_at: datetime
    completed_at: Optional[datetime] = Field(default=None)
    targets_scanned: int = Field(default=0)
    findings_count: int = Field(default=0)
    findings: List[DASTFinding] = Field(default_factory=list)
    duration_seconds: Optional[float] = Field(default=None)


class CVEListResponse(BaseModel):
    """API response for CVE list."""

    items: List[CVERecord]
    total: int
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    has_more: bool = Field(default=False)


class AlertListResponse(BaseModel):
    """API response for alerts list."""

    items: List[VulnerabilityAlert]
    total: int
    unacknowledged: int = Field(default=0)
