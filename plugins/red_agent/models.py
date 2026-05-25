"""Red Agent domain models."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, SecretStr


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Severity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    AUTHORIZING = "authorizing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_APPROVAL = "awaiting_approval"


class ScanIntensity(str, enum.Enum):
    PASSIVE = "passive"
    ACTIVE = "active"
    INTRUSIVE = "intrusive"


class EngagementStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class AutonomyLevel(str, enum.Enum):
    """Operator-controlled autonomy ladder for an engagement.

    The agent is never granted more autonomy than the level set on the
    parent engagement. Each level subsumes the prior — e.g.
    ``EXECUTE_ACTIVE`` permits passive scans too, but always with HITL
    on active. Levels above ``RECOMMEND`` execute scanners; the lower
    three only plan and surface proposals to operators.
    """

    OBSERVE = "observe"
    PLAN = "plan"
    RECOMMEND = "recommend"
    EXECUTE_PASSIVE = "execute_passive"
    EXECUTE_ACTIVE = "execute_active"
    EXECUTE_INTRUSIVE = "execute_intrusive"


_AUTONOMY_RANK: dict["AutonomyLevel", int] = {}


def autonomy_rank(level: "AutonomyLevel") -> int:
    if not _AUTONOMY_RANK:
        for idx, lvl in enumerate(AutonomyLevel):
            _AUTONOMY_RANK[lvl] = idx
    return _AUTONOMY_RANK[level]


_INTENSITY_RANK: dict["ScanIntensity", int] = {}


def intensity_rank(intensity: "ScanIntensity") -> int:
    if not _INTENSITY_RANK:
        for idx, lvl in enumerate(ScanIntensity):
            _INTENSITY_RANK[lvl] = idx
    return _INTENSITY_RANK[intensity]


class TargetType(str, enum.Enum):
    URL = "url"
    HOSTNAME = "hostname"
    IP = "ip"
    CIDR = "cidr"
    REPO = "repo"
    IAC = "iac"
    CLOUD_ACCOUNT = "cloud_account"
    K8S_CLUSTER = "k8s_cluster"
    API_SPEC = "api_spec"
    AD_DOMAIN = "ad_domain"
    ENTRA_TENANT = "entra_tenant"
    BINARY = "binary"
    SYSTEM = "system"


class TargetKind(str, enum.Enum):
    """Coarse-grained category surfaced in the UI as a top-level facet.

    Drives the "New Target" wizard step picker and the Targets list filter.
    Maps loosely onto :class:`TargetType` (e.g. WEB → url|hostname, NETWORK
    → ip|cidr) so existing scanner adapters keep working unchanged.
    """

    WEB = "web"
    HOST = "host"
    CLOUD = "cloud"
    NETWORK = "network"
    IDENTITY = "identity"
    REPO = "repo"
    BINARY = "binary"


class FindingState(str, enum.Enum):
    OPEN = "open"
    TRIAGED = "triaged"
    FIXED = "fixed"
    WONTFIX = "wontfix"
    ACCEPTED = "accepted"


class ValidationStatus(str, enum.Enum):
    """Exploitability state set by ``ExploitValidationEnricher``.

    A vulnerability scanner detects *signal* (banner, version, CWE
    pattern). Validation re-issues the proof-of-concept against the
    same target in an authorized intrusive window and records whether
    the exploit primitive actually fires. Operators triage `VALIDATED`
    findings ahead of mere `UNVALIDATED` matches.
    """

    UNVALIDATED = "unvalidated"
    VALIDATED = "validated"
    NOT_EXPLOITABLE = "not_exploitable"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


class Target(BaseModel):
    type: TargetType
    value: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RulesOfEngagement(BaseModel):
    scope_allowlist: list[str] = Field(default_factory=list)
    excluded_targets: list[str] = Field(default_factory=list)
    max_intensity: ScanIntensity = ScanIntensity.PASSIVE
    autonomy_level: AutonomyLevel = AutonomyLevel.RECOMMEND
    require_human_approval: bool = True
    testing_window: str | None = None
    notes: str | None = None
    llm_probe_rate_limit_seconds: float | None = Field(
        default=None,
        description=(
            "Per-engagement rate limit (seconds between requests) for the "
            "LLM-attack probes. When set, overrides ``Target.metadata."
            "rate_limit_seconds`` for the duration of the scan. Engagements "
            "intended for production must declare this explicitly."
        ),
    )
    llm_auth_secret: SecretStr | None = Field(
        default=None,
        description=(
            "Override LLM target authentication token for the engagement. "
            "Wraps the token in ``SecretStr`` so it never leaks via "
            "``repr()``/Sentry frames. Resolved into ``Target.metadata."
            "auth_token`` only inside the orchestrator before scanner "
            "dispatch — the value never appears in the persisted scan row."
        ),
    )
    llm_require_rate_limit: bool = Field(
        default=False,
        description=(
            "When true, refuse to dispatch LLM-attack probes unless either "
            "``llm_probe_rate_limit_seconds`` (engagement) or "
            "``Target.metadata.rate_limit_seconds`` (request) is explicitly "
            "set. Defaults off to preserve backwards compatibility."
        ),
    )


class EngagementCreate(BaseModel):
    name: str
    objective: str
    rules: RulesOfEngagement = Field(default_factory=RulesOfEngagement)
    tags: list[str] = Field(default_factory=list)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class EngagementUpdate(BaseModel):
    name: str | None = None
    objective: str | None = None
    status: EngagementStatus | None = None
    rules: RulesOfEngagement | None = None
    tags: list[str] | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class EngagementRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    objective: str
    status: EngagementStatus = EngagementStatus.DRAFT
    rules: RulesOfEngagement = Field(default_factory=RulesOfEngagement)
    tags: list[str] = Field(default_factory=list)
    tenant_id: str | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    archived_at: datetime | None = None


class TargetRecord(BaseModel):
    """Persistent target ("project") that aggregates scans + findings over time."""

    id: UUID = Field(default_factory=uuid4)
    kind: TargetKind
    name: str
    value: str
    environment: str | None = None
    owner: str | None = None
    tags: list[str] = Field(default_factory=list)
    profile: dict[str, Any] = Field(default_factory=dict)
    schedule_cron: str | None = None
    scope_overrides: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
    tenant_id: str | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    last_scan_at: datetime | None = None
    archived_at: datetime | None = None


class TargetCreate(BaseModel):
    kind: TargetKind
    name: str
    value: str
    environment: str | None = None
    owner: str | None = None
    tags: list[str] = Field(default_factory=list)
    profile: dict[str, Any] = Field(default_factory=dict)
    schedule_cron: str | None = None
    scope_overrides: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None


class TargetUpdate(BaseModel):
    name: str | None = None
    environment: str | None = None
    owner: str | None = None
    tags: list[str] | None = None
    profile: dict[str, Any] | None = None
    schedule_cron: str | None = None
    scope_overrides: dict[str, Any] | None = None
    description: str | None = None
    archived: bool | None = None


class ScanRequest(BaseModel):
    target: Target
    target_id: UUID | None = None
    engagement_id: UUID | None = None
    scanners: list[str] = Field(default_factory=list)
    intensity: ScanIntensity = ScanIntensity.PASSIVE
    tenant_id: str | None = None
    requested_by: str
    bug_bounty_program: str | None = None
    notes: str | None = None


class Finding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    scanner: str
    title: str
    description: str
    severity: Severity
    cvss_score: float | None = None
    cwe: str | None = None
    cve: str | None = None
    target: str
    endpoint: str | None = None
    port: int | None = None
    service: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)
    discovered_at: datetime = Field(default_factory=_utcnow)
    remediation: str | None = None
    state: FindingState = FindingState.OPEN
    assignee: str | None = None
    triaged_at: datetime | None = None
    resolved_at: datetime | None = None
    due_at: datetime | None = None
    notes: str | None = None
    risk_score: float | None = Field(
        default=None,
        description=(
            "VPR-style normalized risk score in [0..10]. Combines CVSS, "
            "EPSS, KEV, reachability, exposure and asset criticality. "
            "Set by ``RiskScoringEnricher``; absent when scoring is off."
        ),
    )
    controls: list[str] = Field(
        default_factory=list,
        description=(
            "Compliance control IDs the finding maps to (e.g. "
            "``CIS-1.2.6``, ``PCI-6.5.1``, ``NIST-SI-2``). Populated by "
            "``ComplianceMapperEnricher``."
        ),
    )
    external_ref: str | None = Field(
        default=None,
        description=(
            "External system reference (e.g. Jira issue key, ServiceNow "
            "INC number, Linear issue ID). Set by the SOAR / ticketing "
            "integration when a finding is forwarded to a downstream "
            "system; lets inbound webhooks resolve the original finding."
        ),
    )
    validation_status: ValidationStatus = Field(
        default=ValidationStatus.UNVALIDATED,
        description=(
            "Exploitability outcome from ``ExploitValidationEnricher``. "
            "``UNVALIDATED`` is the default for every newly produced "
            "finding; only operator-approved intrusive scans flip it."
        ),
    )
    validation_method: str | None = Field(
        default=None,
        description=(
            "Identifier of the validator that produced ``validation_status`` "
            "(e.g. ``nuclei_poc``, ``metasploit_check``, ``manual``)."
        ),
    )
    validation_evidence: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Structured proof captured by the validator: request, response "
            "snippet, OAST callback id, timing, payload hash. Never stores "
            "raw secrets — the enricher redacts headers/cookies before "
            "persisting."
        ),
    )
    validated_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when validation last ran.",
    )


# SLA per severity (days). Used to compute Finding.due_at on insertion and to
# render countdown chips in the UI. Operators can later expose these as policy
# overrides; until then they are sane enterprise defaults aligned with common
# CISO expectations (NIST CSF / FAIR-style).
SLA_DAYS: dict[Severity, int] = {
    Severity.CRITICAL: 7,
    Severity.HIGH: 14,
    Severity.MEDIUM: 30,
    Severity.LOW: 90,
    Severity.INFO: 180,
}


class FindingTriageUpdate(BaseModel):
    state: FindingState | None = None
    assignee: str | None = None
    notes: str | None = None
    due_at: datetime | None = None


class ScanResult(BaseModel):
    scan_id: UUID
    status: ScanStatus
    started_at: datetime
    finished_at: datetime | None = None
    findings: list[Finding] = Field(default_factory=list)
    error: str | None = None
    duration_seconds: float | None = None
    target_id: UUID | None = None
    engagement_id: UUID | None = None
