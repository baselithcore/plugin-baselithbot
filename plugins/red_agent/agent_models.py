"""Pydantic models for the endpoint-daemon control plane.

Kept in a dedicated module so the original ``models.py`` (scan /
finding / target schemas) stays focused. These models cover the
server-side persistence and REST surface; the wire schema with the
daemon is defined in ``proto/agent.proto`` and is the source of truth
for any field that crosses the network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentOS(str, Enum):
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"


class AgentArch(str, Enum):
    X86_64 = "x86_64"
    AARCH64 = "aarch64"


class AgentStatus(str, Enum):
    ENROLLED = "enrolled"
    ONLINE = "online"
    OFFLINE = "offline"
    REVOKED = "revoked"
    DISABLED = "disabled"


class CertState(str, Enum):
    ACTIVE = "active"
    ROTATED = "rotated"
    EXPIRED = "expired"
    REVOKED = "revoked"


class EnrollmentTokenState(str, Enum):
    UNUSED = "unused"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AgentRecord(BaseModel):
    """One row in ``red_agent_agents``."""

    model_config = ConfigDict(extra="forbid")

    agent_uuid: UUID
    tenant_id: str
    os: AgentOS
    os_version: str | None = None
    kernel_version: str | None = None
    arch: AgentArch
    hostname: str | None = None
    boot_id: str | None = None
    cpu_count: int | None = None
    mem_total_bytes: int | None = None
    daemon_version: str | None = None
    protocol_version: int
    capabilities: list[str] = Field(default_factory=list)
    labels: dict[str, Any] = Field(default_factory=dict)
    status: AgentStatus = AgentStatus.ENROLLED
    last_seen_at: datetime | None = None
    last_disconnect_reason: str | None = None
    enrolled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    enrolled_by: str | None = None
    archived_at: datetime | None = None


class AgentCertRecord(BaseModel):
    """One row in ``red_agent_agent_certs``."""

    model_config = ConfigDict(extra="forbid")

    serial: str
    agent_uuid: UUID
    tenant_id: str
    fingerprint_sha256: str
    spiffe_uri: str
    not_before: datetime
    not_after: datetime
    state: CertState = CertState.ACTIVE
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rotated_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_reason: str | None = None
    revoked_by: str | None = None


class EnrollmentTokenRecord(BaseModel):
    """One row in ``red_agent_enrollment_tokens``.

    The plaintext token is **never** stored. Only its SHA-256 hash
    persists. The plaintext is returned to the operator exactly once
    at creation time.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    token_sha256: str
    bind_agent_uuid: UUID | None = None
    labels: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str
    expires_at: datetime
    state: EnrollmentTokenState = EnrollmentTokenState.UNUSED
    redeemed_at: datetime | None = None
    redeemed_agent_uuid: UUID | None = None
    revoked_at: datetime | None = None
    revoked_by: str | None = None

    @field_validator("token_sha256")
    @classmethod
    def _hex_sha256(cls, v: str) -> str:
        if len(v) != 64:
            raise ValueError("token_sha256 must be 64 hex chars (SHA-256)")
        try:
            int(v, 16)
        except ValueError as exc:
            raise ValueError("token_sha256 must be hex") from exc
        return v.lower()


# ---------------------------------------------------------------------------
# REST request / response schemas
# ---------------------------------------------------------------------------


class EnrollmentTokenCreate(BaseModel):
    """Operator-facing input to mint a fresh enrollment token."""

    model_config = ConfigDict(extra="forbid")

    ttl_seconds: int = Field(
        default=86400,
        ge=300,
        le=86400 * 7,
        description="Token validity. Default 24h, max 7d.",
    )
    bind_agent_uuid: UUID | None = Field(
        default=None,
        description="When set, only this agent_uuid may redeem.",
    )
    labels: dict[str, Any] = Field(
        default_factory=dict,
        description="Initial labels applied to the resulting agent row.",
    )


class EnrollmentTokenIssued(BaseModel):
    """Returned exactly once to the operator at creation time.

    The plaintext ``token`` is **not** retrievable later — re-mint if
    lost.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID
    token: str
    tenant_id: str
    expires_at: datetime
    bind_agent_uuid: UUID | None = None


class AgentEnrollmentRequest(BaseModel):
    """Daemon → backend body for ``POST /red-agent/agents/enroll``."""

    model_config = ConfigDict(extra="forbid")

    enrollment_token: str = Field(min_length=32, max_length=512)
    agent_uuid: UUID
    csr_pem: str = Field(min_length=64, max_length=8192)
    daemon_version: str
    protocol_version: int = Field(ge=1)
    os: AgentOS
    os_version: str | None = None
    kernel_version: str | None = None
    arch: AgentArch
    hostname: str | None = None
    boot_id: str | None = None
    cpu_count: int | None = Field(default=None, ge=0)
    mem_total_bytes: int | None = Field(default=None, ge=0)
    declared_capabilities: list[str] = Field(default_factory=list)


class AgentEnrollmentResponse(BaseModel):
    """Backend → daemon response on successful enrollment."""

    model_config = ConfigDict(extra="forbid")

    agent_uuid: UUID
    tenant_id: str
    cert_pem: str
    chain_pem: str
    not_after: datetime
    spiffe_uri: str
    backend_grpc_endpoint: str
    root_ca_fingerprint_sha256: str
    server_hello_capabilities: list[str]
