"""Honeypot Plugin Data Models.

Pydantic models for attack events, sessions, and statistics.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HoneypotProtocol(str, Enum):
    """Supported honeypot protocols."""

    SSH = "ssh"
    HTTP = "http"
    TCP = "tcp"
    MCP = "mcp"  # LLM Guard / Prompt Injection
    MODBUS = "modbus"  # Modbus TCP (ICS/SCADA)
    MQTT = "mqtt"  # MQTT Broker (IoT)
    S7COMM = "s7comm"  # Siemens S7comm (PLC)


class AttackSeverity(str, Enum):
    """Attack severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AttackCategory(str, Enum):
    """Attack category classification."""

    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    XSS = "xss"
    RECONNAISSANCE = "reconnaissance"
    CREDENTIAL_HARVESTING = "credential_harvesting"
    MALWARE_DELIVERY = "malware_delivery"
    EXPLOIT_ATTEMPT = "exploit_attempt"
    SCADA_MANIPULATION = "scada_manipulation"
    FIRMWARE_TAMPERING = "firmware_tampering"
    PLC_SCAN = "plc_scan"
    UNKNOWN = "unknown"


class GeoLocation(BaseModel):
    """Geographic location data."""

    country: Optional[str] = Field(default=None)
    country_code: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)


class AttackEvent(BaseModel):
    """Individual attack event captured by honeypot."""

    event_id: str = Field(..., description="Unique event identifier")
    session_id: str = Field(..., description="Parent session ID")
    honeypot_id: str = Field(
        default="default", description="Honeypot that captured this event"
    )
    protocol: HoneypotProtocol = Field(..., description="Honeypot protocol")
    timestamp: datetime = Field(default_factory=datetime.now)

    # Source information
    source_ip: str = Field(..., description="Attacker IP address")
    source_port: int = Field(..., description="Attacker source port")
    geo: Optional[GeoLocation] = Field(default=None, description="Geo location")

    # Event data
    event_type: str = Field(
        default="command", description="Event type: command, auth, request, payload"
    )
    raw_data: str = Field(default="", description="Raw captured data/payload")

    # SSH-specific fields
    username: Optional[str] = Field(default=None, description="SSH username attempted")
    password: Optional[str] = Field(default=None, description="SSH password attempted")
    command: Optional[str] = Field(default=None, description="SSH command executed")

    # HTTP-specific fields
    http_method: Optional[str] = Field(default=None, description="HTTP method")
    http_path: Optional[str] = Field(default=None, description="HTTP request path")
    http_headers: Optional[Dict[str, str]] = Field(default=None)
    http_body: Optional[str] = Field(default=None, description="HTTP request body")

    # Analysis
    detected_patterns: List[str] = Field(
        default_factory=list, description="Detected attack patterns"
    )
    category: AttackCategory = Field(default=AttackCategory.UNKNOWN)
    severity: AttackSeverity = Field(default=AttackSeverity.INFO)
    ai_classification: Optional[str] = Field(
        default=None, description="AI-generated classification"
    )

    # CVE Hunter integration
    matched_cves: List[str] = Field(
        default_factory=list, description="Correlated CVE IDs"
    )
    matched_cwes: List[str] = Field(
        default_factory=list, description="Matched CWE identifiers"
    )
    correlation_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="CVE correlation confidence"
    )

    # Metadata for extensibility (JA4, etc.)
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event metadata"
    )
    ja4_fingerprint: Optional[str] = Field(
        default=None, description="JA4 TLS Fingerprint"
    )
    ja4h_fingerprint: Optional[str] = Field(
        default=None, description="JA4H HTTP Fingerprint"
    )
    ja4ssh_fingerprint: Optional[str] = Field(
        default=None, description="JA4SSH SSH Fingerprint"
    )

    # Bot detection fields
    is_bot: Optional[bool] = Field(
        default=None, description="True if detected as automated bot"
    )
    bot_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Bot detection confidence score"
    )
    bot_classification: Optional[str] = Field(
        default=None, description="Classification: bot, human, or unknown"
    )
    bot_signals: Optional[Dict[str, Any]] = Field(
        default=None, description="Raw detection signals used for classification"
    )


class HoneypotSession(BaseModel):
    """Attacker session tracking."""

    session_id: str = Field(..., description="Unique session identifier")
    honeypot_id: str = Field(default="default", description="Target honeypot")
    protocol: HoneypotProtocol = Field(..., description="Honeypot protocol")
    source_ip: str = Field(..., description="Attacker IP address")
    source_port: int = Field(..., description="Initial source port")

    # Timing
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = Field(default=None)
    last_activity: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)

    # Session data
    events_count: int = Field(default=0)
    auth_attempts: int = Field(default=0)
    auth_success: bool = Field(default=False)
    username: Optional[str] = Field(default=None, description="Username used for login")
    commands: List[str] = Field(default_factory=list, description="Commands executed")
    paths_accessed: List[str] = Field(
        default_factory=list, description="HTTP paths accessed"
    )

    # Analysis
    primary_category: AttackCategory = Field(default=AttackCategory.UNKNOWN)
    max_severity: AttackSeverity = Field(default=AttackSeverity.INFO)
    geo: Optional[GeoLocation] = Field(default=None)
    ai_summary: Optional[str] = Field(default=None, description="AI-generated summary")

    # CVE correlation
    matched_cves: List[str] = Field(default_factory=list)


class HoneypotAgentStatus(BaseModel):
    """Status of a honeypot service agent."""

    agent_id: str = Field(..., description="Agent identifier")
    protocol: HoneypotProtocol = Field(..., description="Handled protocol")
    status: str = Field(default="idle", description="running, idle, error")
    current_sessions: int = Field(default=0)
    total_events: int = Field(default=0)
    last_event: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


class HoneypotStatus(BaseModel):
    """Overall honeypot system status."""

    is_running: bool = Field(default=False)
    ssh_enabled: bool = Field(default=False)
    http_enabled: bool = Field(default=False)
    ssh_port: Optional[int] = Field(default=None)
    http_port: Optional[int] = Field(default=None)
    active_sessions: int = Field(default=0)
    total_events_today: int = Field(default=0)
    total_events_all_time: int = Field(default=0)
    unique_ips_today: int = Field(default=0)
    last_attack: Optional[datetime] = Field(default=None)
    agents: List[HoneypotAgentStatus] = Field(default_factory=list)


class HoneypotStats(BaseModel):
    """Aggregated honeypot statistics."""

    # Connection stats
    total_connections: int = Field(default=0)
    total_sessions: int = Field(default=0)
    active_sessions: int = Field(default=0)
    total_events: int = Field(default=0)

    # IP stats
    unique_ips: int = Field(default=0)
    banned_ips: int = Field(default=0)
    top_attacker_ips: List[Dict[str, Any]] = Field(default_factory=list)

    # Protocol breakdown
    protocol_breakdown: Dict[str, int] = Field(default_factory=dict)

    # Severity breakdown
    severity_breakdown: Dict[str, int] = Field(
        default_factory=lambda: {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
    )

    # Bot breakdown
    bot_breakdown: Dict[str, int] = Field(
        default_factory=lambda: {
            "bot": 0,
            "human": 0,
            "unknown": 0,
        }
    )

    # Category breakdown
    category_breakdown: Dict[str, int] = Field(default_factory=dict)

    # CVE Hunter integration
    cve_correlations: int = Field(default=0)
    top_matched_cves: List[Dict[str, Any]] = Field(default_factory=list)

    # Time-based
    events_last_hour: int = Field(default=0)
    events_today: int = Field(default=0)
    events_this_week: int = Field(default=0)

    # Activity history for charts
    activity_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="Time-series activity data"
    )


class EventListResponse(BaseModel):
    """API response for event list."""

    items: List[AttackEvent]
    total: int
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    has_more: bool = Field(default=False)


class SessionListResponse(BaseModel):
    """API response for session list."""

    items: List[HoneypotSession]
    total: int
    active: int = Field(default=0)


class CVECorrelation(BaseModel):
    """Attack-to-CVE correlation result."""

    correlation_id: str = Field(..., description="Unique correlation identifier")
    event_id: str = Field(..., description="Source attack event ID")
    cve_id: str = Field(..., description="Matched CVE ID")
    cwe_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    match_reason: str = Field(default="", description="Why this CVE matched")
    attack_pattern: str = Field(default="", description="Detected attack pattern")
    timestamp: datetime = Field(default_factory=datetime.now)


class CVECorrelationListResponse(BaseModel):
    """API response for CVE correlations."""

    items: List[CVECorrelation]
    total: int
    unique_cves: int = Field(default=0)


class DiscoveryLog(BaseModel):
    """Log entry for attack discovery feed."""

    message: str = Field(..., description="Log message")
    timestamp: datetime = Field(default_factory=datetime.now)
    is_alert: bool = Field(default=False, description="Is high-priority alert")
    is_error: bool = Field(default=False, description="Is error message")
    agent_type: str = Field(default="system", description="Agent that generated log")
    severity: AttackSeverity = Field(default=AttackSeverity.INFO)
    country_code: Optional[str] = Field(default=None, description="ISO country code")
    source_ip: Optional[str] = Field(default=None, description="Attacker IP address")


class HoneypotInfo(BaseModel):
    """Honeypot instance information for frontend."""

    id: str = Field(..., description="Unique honeypot identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="Human-readable description")
    protocol: str = Field(..., description="Protocol: ssh, http, tcp")
    port: int = Field(..., description="Listening port")
    enabled: bool = Field(default=True, description="Whether honeypot is active")
    active_attackers: int = Field(default=0, description="Current unique attacker IPs")
    total_events: int = Field(default=0, description="Total events captured")
    tags: List[str] = Field(default_factory=list, description="Classification tags")
