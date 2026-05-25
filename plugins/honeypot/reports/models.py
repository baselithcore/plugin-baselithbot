"""Report Data Models.

Pydantic models for security report generation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReportFormat(str, Enum):
    """Supported report output formats."""

    PDF = "pdf"
    MARKDOWN = "markdown"
    JSON = "json"


class ReportType(str, Enum):
    """Types of security reports."""

    EXECUTIVE = "executive"  # High-level executive summary
    TECHNICAL = "technical"  # Detailed technical analysis
    COMPLIANCE = "compliance"  # Compliance-focused report
    INCIDENT = "incident"  # Incident response report
    PENTEST = "pentest"  # Penetration test results
    THREAT_INTEL = "threat_intel"  # Threat intelligence report
    RESEARCH = "research"  # Academic/threat intel research report


class ReportSection(str, Enum):
    """Report sections that can be included."""

    EXECUTIVE_SUMMARY = "executive_summary"
    THREAT_LANDSCAPE = "threat_landscape"
    ATTACK_ANALYTICS = "attack_analytics"
    GEO_ANALYSIS = "geo_analysis"
    BOTNET_DISCOVERY = "botnet_discovery"
    PENTEST_RESULTS = "pentest_results"
    CVE_CORRELATIONS = "cve_correlations"
    RECOMMENDATIONS = "recommendations"
    IOC_LIST = "ioc_list"
    TIMELINE = "timeline"
    # Research-specific sections
    ABSTRACT = "abstract"
    KEY_FINDINGS = "key_findings"
    MITRE_MAPPING = "mitre_mapping"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    PAYLOAD_ANALYSIS = "payload_analysis"
    SEQUENTIAL_ANALYSIS = "sequential_analysis"


class ReportConfig(BaseModel):
    """Configuration for report generation."""

    report_type: ReportType = Field(
        default=ReportType.TECHNICAL, description="Type of report to generate"
    )
    format: ReportFormat = Field(
        default=ReportFormat.MARKDOWN, description="Output format"
    )
    sections: List[ReportSection] = Field(
        default_factory=lambda: [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.THREAT_LANDSCAPE,
            ReportSection.ATTACK_ANALYTICS,
            ReportSection.RECOMMENDATIONS,
        ],
        description="Sections to include in the report",
    )
    time_range_hours: int = Field(
        default=168, ge=1, le=720, description="Time range in hours (default 7 days)"
    )
    honeypot_id: Optional[str] = Field(
        default=None, description="Filter by specific honeypot"
    )
    include_raw_data: bool = Field(
        default=False, description="Include raw data in technical reports"
    )
    organization_name: Optional[str] = Field(
        default=None, description="Organization name for branding"
    )
    classification: str = Field(
        default="INTERNAL", description="Document classification level"
    )


class ThreatSummary(BaseModel):
    """Summary of threat activity."""

    total_events: int = 0
    unique_attackers: int = 0
    critical_events: int = 0
    high_events: int = 0
    medium_events: int = 0
    low_events: int = 0
    top_attack_categories: Dict[str, int] = Field(default_factory=dict)
    top_attacking_countries: Dict[str, int] = Field(default_factory=dict)
    top_protocols: Dict[str, int] = Field(default_factory=dict)
    detected_botnets: int = 0
    potential_cc_servers: int = 0
    cve_matches: int = 0
    bot_traffic_percentage: float = 0.0


class AttackTimelineEntry(BaseModel):
    """Timeline entry for attacks."""

    timestamp: datetime
    event_type: str
    source_ip: str
    severity: str
    category: str
    description: str
    country_code: Optional[str] = None


class VulnerabilityItem(BaseModel):
    """Vulnerability finding for reports."""

    finding_id: str
    name: str
    severity: str
    category: str
    description: str
    remediation: str
    cve_references: List[str] = Field(default_factory=list)
    confidence: float = 0.0


class IOCEntry(BaseModel):
    """Indicator of Compromise entry."""

    ioc_type: str  # ip, domain, hash, url
    value: str
    first_seen: datetime
    last_seen: datetime
    confidence: float
    associated_campaigns: List[str] = Field(default_factory=list)
    threat_level: str = "medium"


class GeoDistribution(BaseModel):
    """Geographic distribution of attacks."""

    country_code: str
    country_name: str
    attack_count: int
    unique_ips: int
    primary_attack_types: List[str] = Field(default_factory=list)


class BotnetSummary(BaseModel):
    """Summary of detected botnet activity."""

    cluster_id: str
    member_count: int
    severity: str
    attack_coordination_score: float
    suspected_cc_servers: List[str] = Field(default_factory=list)
    common_protocols: List[str] = Field(default_factory=list)
    first_detected: datetime
    last_activity: datetime


class PentestSummaryItem(BaseModel):
    """Summary of pentest results."""

    pentest_id: str
    playbook_name: str
    security_score: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    critical_findings: int
    high_findings: int
    status: str
    completed_at: Optional[datetime] = None


class ReportMetadata(BaseModel):
    """Report metadata."""

    report_id: str
    generated_at: datetime
    generated_by: str = "Honeypot Security System"
    report_type: ReportType
    classification: str
    time_range_start: datetime
    time_range_end: datetime
    honeypot_filter: Optional[str] = None
    organization: Optional[str] = None
    version: str = "1.0"


class SecurityReport(BaseModel):
    """Complete security report structure.

    Extended with discovery enrichment, correlations, MISP status,
    threat intel summary, and payload excerpts for comprehensive reporting.
    """

    metadata: ReportMetadata
    threat_summary: ThreatSummary
    executive_summary: Optional[str] = None
    attack_timeline: List[AttackTimelineEntry] = Field(default_factory=list)
    geo_distribution: List[GeoDistribution] = Field(default_factory=list)
    botnet_activity: List[BotnetSummary] = Field(default_factory=list)
    vulnerabilities: List[VulnerabilityItem] = Field(default_factory=list)
    pentest_results: List[PentestSummaryItem] = Field(default_factory=list)
    iocs: List[IOCEntry] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None

    # Discovery Enrichment (Phase 2 enhancement)
    discovery_enrichment: Optional["DiscoveryEnrichment"] = Field(
        default=None, description="Enrichment data from discovery analysis"
    )
    correlations: List["AttackerCorrelation"] = Field(
        default_factory=list, description="Attacker correlation analysis"
    )
    misp_status: Optional["MISPStatus"] = Field(
        default=None, description="MISP integration status"
    )
    threat_intel_summary: Optional["ThreatIntelSummary"] = Field(
        default=None, description="Threat intelligence summary"
    )
    payload_excerpts: List["PayloadExcerpt"] = Field(
        default_factory=list, description="Sanitized payload excerpts for research"
    )
    credential_analysis: Optional["CredentialAnalysis"] = Field(
        default=None, description="Credential attack analysis"
    )
    sequential_analysis: Optional[List["AttackSessionAnalysis"]] = Field(
        default=None, description="Sequential kill-chain analysis of top sessions"
    )

    model_config = ConfigDict()


class ReportGenerationRequest(BaseModel):
    """API request for report generation."""

    config: ReportConfig = Field(default_factory=ReportConfig)
    title: Optional[str] = Field(default=None, description="Custom report title")


class ReportGenerationResponse(BaseModel):
    """API response for report generation."""

    report_id: str
    status: str  # generating, completed, failed
    format: ReportFormat
    download_url: Optional[str] = None
    preview: Optional[SecurityReport] = None
    error: Optional[str] = None
    generated_at: Optional[datetime] = None


class SavedReport(BaseModel):
    """Saved report metadata for listing."""

    report_id: str
    title: str
    report_type: ReportType
    format: ReportFormat
    generated_at: datetime
    time_range_hours: int
    honeypot_filter: Optional[str] = None
    threat_summary: ThreatSummary
    file_size_bytes: Optional[int] = None


# =============================================================================
# Discovery Enrichment Models
# =============================================================================


class DiscoveryEnrichment(BaseModel):
    """Enrichment data from discovery analysis.

    Contains metadata from all 8 discovery analyzers for comprehensive
    threat intelligence context in reports.
    """

    analysis_id: Optional[str] = Field(
        default=None, description="Discovery analysis identifier"
    )
    analyzed_at: Optional[datetime] = Field(
        default=None, description="When the discovery analysis was performed"
    )

    # Analyzer metadata
    behavioral_meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Behavioral analysis: timing sync, payload similarity, scan patterns",
    )
    statistical_meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Statistical analysis: geo clustering, IAT, TTL patterns",
    )
    cc_meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="C&C detection: beaconing, DGA, fast-flux indicators",
    )
    ml_meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="ML analysis: clustering, anomaly detection, sequence analysis",
    )
    zeroday_meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Zero-day detection: novel attack patterns, indicators",
    )
    exploit_meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Exploit analysis: techniques, chains, CVE correlations",
    )
    threat_intel_meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Threat intel: IOC extraction, YARA rules, command patterns",
    )

    # Profiling data
    botnet_profiles: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed botnet profiles with malware family and tactics",
    )
    identified_malware_families: List[str] = Field(
        default_factory=list, description="Identified malware families from profiling"
    )


class AttackerCorrelation(BaseModel):
    """Correlation between attackers indicating coordinated behavior."""

    correlation_type: str = Field(
        ...,
        description="Type: timing, pattern, infrastructure, cross_honeypot",
    )
    involved_ips: List[str] = Field(
        default_factory=list, description="IPs involved in correlation"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    evidence: str = Field(default="", description="Evidence description")


class MISPStatus(BaseModel):
    """MISP threat intelligence platform integration status."""

    enabled: bool = Field(default=False, description="Whether MISP is enabled")
    status: str = Field(
        default="not_configured",
        description="Connection status: not_configured, connected, error",
    )
    sync_percentage: int = Field(
        default=0, ge=0, le=100, description="Sync percentage (0-100)"
    )
    last_sync: Optional[datetime] = Field(
        default=None, description="Last successful sync time"
    )
    exported_iocs_count: int = Field(
        default=0, description="Total IOCs exported to MISP"
    )


class ThreatIntelSummary(BaseModel):
    """Summary of threat intelligence extracted from attacks."""

    yara_rules: List[str] = Field(
        default_factory=list, description="Auto-generated YARA rules"
    )
    yara_rules_count: int = Field(default=0, description="Number of YARA rules")
    command_patterns: List[str] = Field(
        default_factory=list, description="Common command patterns observed"
    )
    user_agents: List[str] = Field(
        default_factory=list, description="User agents observed in HTTP attacks"
    )
    payload_hashes: List[Dict[str, str]] = Field(
        default_factory=list, description="Payload hashes (SHA256, MD5)"
    )
    ioc_counts: Dict[str, int] = Field(
        default_factory=dict, description="IOC type counts (ips, domains, urls, hashes)"
    )


class PayloadExcerpt(BaseModel):
    """Sanitized payload excerpt for research context.

    All payloads are sanitized via sanitize_for_llm() before inclusion
    to prevent prompt injection and security issues.
    """

    category: str = Field(..., description="Attack category (sql_injection, etc)")
    severity: str = Field(..., description="Severity level")
    excerpt: str = Field(
        ..., description="Sanitized, truncated payload excerpt (max 500 chars)"
    )
    source_country: str = Field(default="Unknown", description="Source country")
    protocol: str = Field(default="unknown", description="Protocol (http, ssh, etc)")
    ai_classification: Optional[str] = Field(
        default=None, description="AI classification of the attack"
    )
    timestamp: Optional[datetime] = Field(
        default=None, description="When the attack occurred"
    )


class CredentialAnalysis(BaseModel):
    """Analysis of credential-based attacks (brute force, credential stuffing)."""

    total_attempts: int = Field(default=0, description="Total credential attempts")
    unique_usernames: int = Field(default=0, description="Unique usernames tried")
    unique_passwords: int = Field(default=0, description="Unique passwords tried")
    top_usernames: List[Dict[str, Any]] = Field(
        default_factory=list, description="Top usernames with counts"
    )
    top_passwords: List[Dict[str, Any]] = Field(
        default_factory=list, description="Top password patterns (masked)"
    )
    credential_pairs_count: int = Field(
        default=0, description="Unique username/password combinations"
    )


class AttackStep(BaseModel):
    """A single step in an attack sequence (Kill Chain)."""

    timestamp: datetime = Field(..., description="When the step occurred")
    phase: str = Field(..., description="Attack phase (Recon, Exploit, etc.)")
    description: str = Field(..., description="Description of the action")
    payload_snippet: Optional[str] = Field(
        None, description="Sanitized payload snippet"
    )
    severity: str = Field("medium", description="Severity of this step")


class AttackSessionAnalysis(BaseModel):
    """Sequential analysis of an attack session."""

    session_id: str = Field(..., description="Session identifier")
    attacker_ip: str = Field(..., description="Attacker IP address")
    steps: List[AttackStep] = Field(
        default_factory=list, description="Ordered attack steps"
    )
    narrative: Optional[str] = Field(
        None, description="LLM-generated narrative of the attack"
    )
