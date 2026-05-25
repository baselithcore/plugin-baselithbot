"""Cloud Management Honeypot - Data Models.

Pydantic models for cloud API simulation, session states, and forensic capture.
Designed for high-interaction deception targeting APT and cloud-specific attacks.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field


class CloudProvider(str, Enum):
    """Emulated cloud provider type."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    GENERIC = "generic"


class SessionState(str, Enum):
    """State machine states for session progression."""

    # Initial states
    DISCOVERY = "discovery"  # Probing endpoints, no auth
    PRE_AUTH = "pre_auth"  # Attempting authentication

    # Authenticated states
    AUTHENTICATED = "authenticated"  # Valid session established
    EXPLORING = "exploring"  # Enumerating resources
    EXFILTRATING = "exfiltrating"  # Attempting data extraction

    # Privilege escalation states
    PRIVILEGE_ESCALATION = "privilege_escalation"  # IAM abuse attempts
    LATERAL_MOVEMENT = "lateral_movement"  # Cross-service access

    # Terminal states
    BLOCKED = "blocked"  # Session terminated by policy
    EXPIRED = "expired"  # Session timed out


class CloudAttackCategory(str, Enum):
    """Cloud-specific attack categories."""

    # Authentication attacks
    CREDENTIAL_STUFFING = "credential_stuffing"
    BRUTE_FORCE = "brute_force"
    TOKEN_THEFT = "token_theft"
    MFA_BYPASS = "mfa_bypass"

    # Reconnaissance
    IAM_ENUMERATION = "iam_enumeration"
    SERVICE_DISCOVERY = "service_discovery"
    BUCKET_ENUMERATION = "bucket_enumeration"
    METADATA_SERVICE_ABUSE = "metadata_service_abuse"

    # Exploitation
    SSRF = "ssrf"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ROLE_ASSUMPTION = "role_assumption"
    POLICY_MANIPULATION = "policy_manipulation"

    # Data exfiltration
    S3_EXFILTRATION = "s3_exfiltration"
    SECRETS_EXTRACTION = "secrets_extraction"
    LOG_TAMPERING = "log_tampering"

    # Persistence
    BACKDOOR_USER = "backdoor_user"
    ACCESS_KEY_CREATION = "access_key_creation"
    LAMBDA_BACKDOOR = "lambda_backdoor"

    # Generic
    UNKNOWN = "unknown"


class APICallSeverity(str, Enum):
    """Severity classification for cloud API calls."""

    CRITICAL = "critical"  # Immediate response required
    HIGH = "high"  # Significant threat indicator
    MEDIUM = "medium"  # Suspicious activity
    LOW = "low"  # Minor anomaly
    INFO = "info"  # Normal activity


class CloudCredential(BaseModel):
    """Captured cloud credential."""

    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None  # Always redacted in logs
    session_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    mfa_code: Optional[str] = None
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def redacted(self) -> Dict[str, Any]:
        """Return redacted version for logging."""
        return {
            "access_key_id": self.access_key_id,
            "secret_access_key": "***REDACTED***" if self.secret_access_key else None,
            "session_token": "***REDACTED***" if self.session_token else None,
            "username": self.username,
            "password": "***REDACTED***" if self.password else None,
            "mfa_code": self.mfa_code,
            "api_key": "***REDACTED***" if self.api_key else None,
            "bearer_token": "***REDACTED***" if self.bearer_token else None,
            "captured_at": self.captured_at.isoformat(),
        }


class TCPFingerprint(BaseModel):
    """TCP/IP stack fingerprint for OS/tool identification."""

    # TCP options
    window_size: Optional[int] = None
    ttl: Optional[int] = None
    df_flag: Optional[bool] = None  # Don't Fragment
    mss: Optional[int] = None  # Maximum Segment Size
    window_scale: Optional[int] = None
    sack_permitted: Optional[bool] = None
    timestamps: Optional[bool] = None
    nop_count: Optional[int] = None

    # Derived identification
    os_guess: Optional[str] = None
    tool_guess: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Raw option string (p0f style)
    options_signature: Optional[str] = None


class TLSFingerprint(BaseModel):
    """TLS Client Hello fingerprint."""

    # JA4 fingerprint components
    ja4: Optional[str] = None
    ja4h: Optional[str] = None

    # Raw components
    tls_version: Optional[str] = None
    cipher_suites: List[str] = Field(default_factory=list)
    extensions: List[str] = Field(default_factory=list)
    supported_groups: List[str] = Field(default_factory=list)
    signature_algorithms: List[str] = Field(default_factory=list)

    # ALPN (Application-Layer Protocol Negotiation)
    alpn_protocols: List[str] = Field(default_factory=list)

    # Derived identification
    client_guess: Optional[str] = None  # curl, python-requests, browser
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RequestTiming(BaseModel):
    """Request timing analysis for tool/automation detection."""

    # Individual request timing
    request_received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    time_since_last_request_ms: Optional[float] = None

    # Session-level timing patterns
    avg_inter_request_delay_ms: Optional[float] = None
    min_inter_request_delay_ms: Optional[float] = None
    max_inter_request_delay_ms: Optional[float] = None
    request_timing_variance: Optional[float] = None

    # Detection signals
    is_machine_timing: bool = False  # Sub-human delays
    timing_pattern: Optional[str] = None  # "constant", "linear", "random", "human"


class CloudAPICall(BaseModel):
    """Individual cloud API call with forensic metadata."""

    call_id: str = Field(..., description="Unique call identifier")
    session_id: str = Field(..., description="Parent session ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # API call details
    service: str = Field(..., description="Cloud service: iam, s3, ec2, etc.")
    action: str = Field(..., description="API action: ListBuckets, GetUser, etc.")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    body_hash: Optional[str] = None  # SHA256 of request body

    # Response simulation
    response_code: int = Field(default=200)
    response_body_preview: Optional[str] = None  # First 500 chars
    simulated_error: Optional[str] = None

    # Forensic analysis
    category: CloudAttackCategory = Field(default=CloudAttackCategory.UNKNOWN)
    severity: APICallSeverity = Field(default=APICallSeverity.INFO)
    detected_patterns: List[str] = Field(default_factory=list)
    heuristic_flags: List[str] = Field(default_factory=list)

    # Fingerprinting
    tcp_fingerprint: Optional[TCPFingerprint] = None
    tls_fingerprint: Optional[TLSFingerprint] = None
    request_timing: Optional[RequestTiming] = None

    # Source attribution
    source_ip: str = Field(...)
    source_port: int = Field(default=0)
    user_agent: Optional[str] = None


class CloudSession(BaseModel):
    """Cloud honeypot session with state machine tracking."""

    session_id: str = Field(..., description="Unique session identifier")
    honeypot_id: str = Field(default="cloud-mgmt", description="Honeypot instance")
    provider: CloudProvider = Field(default=CloudProvider.AWS)

    # Session lifecycle
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # State machine
    current_state: SessionState = Field(default=SessionState.DISCOVERY)
    state_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="State transitions with timestamps",
    )
    state_transition_count: int = Field(default=0)

    # Source tracking
    source_ip: str = Field(...)
    source_port: int = Field(default=0)
    geo_country: Optional[str] = None
    geo_city: Optional[str] = None
    asn: Optional[str] = None
    org: Optional[str] = None

    # Authentication tracking
    auth_attempts: int = Field(default=0)
    auth_success: bool = Field(default=False)
    authenticated_as: Optional[str] = None  # Username/role assumed
    credentials_captured: List[CloudCredential] = Field(default_factory=list)
    mfa_triggered: bool = Field(default=False)

    # API call tracking
    api_calls: List[str] = Field(
        default_factory=list, description="Call IDs for lookup"
    )
    api_call_count: int = Field(default=0)
    services_accessed: Set[str] = Field(default_factory=set)
    actions_performed: Set[str] = Field(default_factory=set)

    # Attack classification
    primary_category: CloudAttackCategory = Field(default=CloudAttackCategory.UNKNOWN)
    detected_categories: Set[CloudAttackCategory] = Field(default_factory=set)
    max_severity: APICallSeverity = Field(default=APICallSeverity.INFO)
    threat_score: float = Field(default=0.0, ge=0.0, le=100.0)

    # Behavioral analysis
    unique_endpoints_probed: int = Field(default=0)
    error_count: int = Field(default=0)
    success_count: int = Field(default=0)
    data_volume_requested_bytes: int = Field(default=0)

    # Fingerprinting (consolidated)
    tcp_fingerprints: List[TCPFingerprint] = Field(default_factory=list)
    tls_fingerprints: List[TLSFingerprint] = Field(default_factory=list)
    user_agents: Set[str] = Field(default_factory=set)

    # Timing analysis
    avg_request_interval_ms: Optional[float] = None
    is_automated: bool = Field(default=False)
    automation_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # AI/ML analysis
    ai_classification: Optional[str] = None
    ai_confidence: Optional[float] = None
    mitre_techniques: List[str] = Field(
        default_factory=list, description="MITRE ATT&CK technique IDs"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class HeuristicAlert(BaseModel):
    """Zero-day heuristic detection alert."""

    alert_id: str = Field(..., description="Unique alert identifier")
    session_id: str = Field(..., description="Associated session")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Alert classification
    heuristic_name: str = Field(..., description="Heuristic rule that triggered")
    heuristic_category: str = Field(
        default="unknown",
        description="Category: timing, sequence, payload, behavior",
    )
    severity: APICallSeverity = Field(default=APICallSeverity.MEDIUM)

    # Evidence
    trigger_reason: str = Field(..., description="Why this heuristic fired")
    evidence: Dict[str, Any] = Field(
        default_factory=dict, description="Supporting data"
    )
    related_api_calls: List[str] = Field(default_factory=list)

    # Context
    baseline_value: Optional[Any] = None  # Normal/expected value
    observed_value: Optional[Any] = None  # What was actually seen
    deviation_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Recommendations
    suggested_action: Optional[str] = None
    is_zero_day_candidate: bool = Field(default=False)


class CloudHoneypotStats(BaseModel):
    """Aggregated statistics for cloud honeypot."""

    # Session stats
    total_sessions: int = Field(default=0)
    active_sessions: int = Field(default=0)
    sessions_by_state: Dict[str, int] = Field(default_factory=dict)

    # Authentication stats
    auth_attempts: int = Field(default=0)
    unique_credentials_captured: int = Field(default=0)
    mfa_bypass_attempts: int = Field(default=0)

    # API stats
    total_api_calls: int = Field(default=0)
    calls_by_service: Dict[str, int] = Field(default_factory=dict)
    calls_by_severity: Dict[str, int] = Field(default_factory=dict)

    # Attack classification
    attacks_by_category: Dict[str, int] = Field(default_factory=dict)
    unique_attack_ips: int = Field(default=0)

    # Heuristic alerts
    heuristic_alerts: int = Field(default=0)
    zero_day_candidates: int = Field(default=0)

    # Fingerprinting
    unique_tcp_fingerprints: int = Field(default=0)
    unique_tls_fingerprints: int = Field(default=0)
    identified_tools: Dict[str, int] = Field(default_factory=dict)

    # Time-based
    last_activity: Optional[datetime] = None
    peak_concurrent_sessions: int = Field(default=0)
