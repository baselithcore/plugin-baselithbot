"""REST endpoints for the endpoint-daemon control plane.

Surfaces three logical groups:

* ``/agents`` — operator-facing CRUD over the enrolled fleet.
* ``/agents/enrollment-tokens`` — operator mints / lists / revokes
  single-use enrollment tokens.
* ``/agents/enroll`` — the only daemon-facing endpoint reachable
  without mTLS. Bearer-token authenticated; consumes a token and
  returns a freshly-signed leaf cert. Rate-limited by upstream
  middleware; this handler enforces single-use semantics atomically
  in :class:`EnrollmentTokenPersistence`.

After a successful redemption the daemon switches to the bidirectional
``AgentChannel`` gRPC service (Phase 1 next deliverable). This router
deliberately does not expose any other unauthenticated surface.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from core.context import get_current_tenant_id
from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.red_agent.agent_models import (
    AgentEnrollmentRequest,
    AgentEnrollmentResponse,
    AgentOS,
    AgentRecord,
    AgentStatus,
    EnrollmentTokenCreate,
    EnrollmentTokenIssued,
    EnrollmentTokenState,
)
from plugins.red_agent.crypto import AgentCAService, CSRValidationError
from plugins.red_agent.dependencies import (
    require_security_operator,
    require_viewer,
)
from plugins.red_agent.persistence.agent_audit import AgentAuditLog
from plugins.red_agent.persistence.agent_certs import AgentCertPersistence
from plugins.red_agent.persistence.agent_telemetry import AgentTelemetryStore
from plugins.red_agent.persistence.agents import AgentPersistence
from plugins.red_agent.persistence.enrollment_tokens import (
    EnrollmentTokenPersistence,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["red-agent", "fleet"])


# ---------------------------------------------------------------------------
# DI helpers
# ---------------------------------------------------------------------------


def _agents_store() -> AgentPersistence:
    store = ServiceRegistry.get(AgentPersistence)
    if store is None or not store.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AgentPersistence not available",
        )
    return store


def _certs_store() -> AgentCertPersistence:
    store = ServiceRegistry.get(AgentCertPersistence)
    if store is None or not store.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AgentCertPersistence not available",
        )
    return store


def _tokens_store() -> EnrollmentTokenPersistence:
    store = ServiceRegistry.get(EnrollmentTokenPersistence)
    if store is None or not store.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "EnrollmentTokenPersistence not available",
        )
    return store


def _audit() -> AgentAuditLog:
    store = ServiceRegistry.get(AgentAuditLog)
    if store is None or not store.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AgentAuditLog not available",
        )
    return store


def _telemetry_store() -> AgentTelemetryStore:
    store = ServiceRegistry.get(AgentTelemetryStore)
    if store is None or not store.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AgentTelemetryStore not available",
        )
    return store


def _ca() -> AgentCAService:
    ca = ServiceRegistry.get(AgentCAService)
    if ca is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AgentCAService not configured — set RED_AGENT_CA_CERT_PATH / RED_AGENT_CA_KEY_PATH",
        )
    return ca


def _actor(request: Request) -> str:
    """Best-effort actor identity for audit rows.

    Falls back to the remote address when no auth principal is
    attached to the request — production deployments rely on the
    upstream auth plugin to populate ``request.state.user``.
    """
    user = getattr(request.state, "user", None)
    if user is not None:
        return str(getattr(user, "username", None) or getattr(user, "id", "unknown"))
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Output schemas (kept minimal — full record models live in agent_models)
# ---------------------------------------------------------------------------


class AgentSummary(BaseModel):
    agent_uuid: UUID
    tenant_id: str
    os: AgentOS
    arch: str
    hostname: str | None
    status: AgentStatus
    daemon_version: str | None
    capabilities: list[str]
    labels: dict[str, Any]
    last_seen_at: Any | None
    enrolled_at: Any


def _to_summary(record: AgentRecord) -> AgentSummary:
    return AgentSummary(
        agent_uuid=record.agent_uuid,
        tenant_id=record.tenant_id,
        os=record.os,
        arch=record.arch.value,
        hostname=record.hostname,
        status=record.status,
        daemon_version=record.daemon_version,
        capabilities=record.capabilities,
        labels=record.labels,
        last_seen_at=record.last_seen_at,
        enrolled_at=record.enrolled_at,
    )


# ---------------------------------------------------------------------------
# Operator-facing fleet endpoints
# ---------------------------------------------------------------------------


@router.get("", dependencies=[require_viewer()])
async def list_agents(
    status_filter: AgentStatus | None = None,
    os: AgentOS | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[AgentSummary]:
    tenant_id = get_current_tenant_id()
    records = await _agents_store().list(
        tenant_id=tenant_id,
        status=status_filter,
        os=os,
        limit=min(max(limit, 1), 500),
        offset=max(offset, 0),
    )
    return [_to_summary(r) for r in records]


@router.get("/{agent_uuid}/telemetry", dependencies=[require_viewer()])
async def list_agent_telemetry(
    agent_uuid: UUID,
    kind: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Recent telemetry events for an agent (operator visibility).

    Capped at 500 rows per call. The fleet UI uses this for the
    per-agent activity timeline; backend tasks needing full-history
    access read the partitioned table directly.
    """
    tenant_id = get_current_tenant_id()
    return await _telemetry_store().list_recent(
        tenant_id=tenant_id,
        agent_uuid=agent_uuid,
        kind=kind,
        limit=min(max(limit, 1), 500),
    )


@router.get("/telemetry", dependencies=[require_viewer()])
async def list_fleet_telemetry(
    kind: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Recent telemetry events across the whole tenant fleet."""
    tenant_id = get_current_tenant_id()
    return await _telemetry_store().list_recent(
        tenant_id=tenant_id,
        agent_uuid=None,
        kind=kind,
        limit=min(max(limit, 1), 500),
    )


@router.get("/{agent_uuid}", dependencies=[require_viewer()])
async def get_agent(agent_uuid: UUID) -> AgentRecord:
    tenant_id = get_current_tenant_id()
    record = await _agents_store().get(agent_uuid, tenant_id=tenant_id)
    if record is None:
        raise HTTPException(404, "agent not found")
    return record


@router.delete(
    "/{agent_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    dependencies=[require_security_operator()],
)
async def archive_agent(agent_uuid: UUID, request: Request) -> None:
    tenant_id = get_current_tenant_id()
    actor = _actor(request)
    archived = await _agents_store().archive(agent_uuid, tenant_id=tenant_id)
    if not archived:
        raise HTTPException(404, "agent not found")
    active = await _certs_store().get_active(agent_uuid, tenant_id=tenant_id)
    if active is not None:
        await _certs_store().revoke(
            active.serial,
            tenant_id=tenant_id,
            reason="agent archived",
            revoked_by=actor,
        )
    await _audit().record(
        tenant_id=tenant_id,
        actor=actor,
        event="agent.archived",
        agent_uuid=agent_uuid,
        payload={"agent_uuid": str(agent_uuid)},
    )


# ---------------------------------------------------------------------------
# Enrollment token endpoints (operator-only)
# ---------------------------------------------------------------------------


@router.post(
    "/enrollment-tokens",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_security_operator()],
)
async def create_enrollment_token(
    body: EnrollmentTokenCreate,
    request: Request,
) -> EnrollmentTokenIssued:
    tenant_id = get_current_tenant_id()
    actor = _actor(request)
    issued = await _tokens_store().mint(
        tenant_id=tenant_id,
        created_by=actor,
        ttl_seconds=body.ttl_seconds,
        bind_agent_uuid=body.bind_agent_uuid,
        labels=body.labels,
    )
    await _audit().record(
        tenant_id=tenant_id,
        actor=actor,
        event="enrollment_token.created",
        payload={
            "token_id": str(issued.id),
            "ttl_seconds": body.ttl_seconds,
            "bind_agent_uuid": (
                str(body.bind_agent_uuid) if body.bind_agent_uuid else None
            ),
        },
    )
    return issued


@router.get(
    "/enrollment-tokens",
    dependencies=[require_security_operator()],
)
async def list_enrollment_tokens(
    state: EnrollmentTokenState | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return token metadata only — never the plaintext (already destroyed)."""
    tenant_id = get_current_tenant_id()
    records = await _tokens_store().list(
        tenant_id=tenant_id,
        state=state,
        limit=min(max(limit, 1), 500),
        offset=max(offset, 0),
    )
    return [
        {
            "id": str(r.id),
            "tenant_id": r.tenant_id,
            "bind_agent_uuid": (str(r.bind_agent_uuid) if r.bind_agent_uuid else None),
            "labels": r.labels,
            "created_at": r.created_at,
            "created_by": r.created_by,
            "expires_at": r.expires_at,
            "state": r.state.value,
            "redeemed_at": r.redeemed_at,
            "redeemed_agent_uuid": (
                str(r.redeemed_agent_uuid) if r.redeemed_agent_uuid else None
            ),
        }
        for r in records
    ]


@router.delete(
    "/enrollment-tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    dependencies=[require_security_operator()],
)
async def revoke_enrollment_token(token_id: UUID, request: Request) -> None:
    tenant_id = get_current_tenant_id()
    actor = _actor(request)
    revoked = await _tokens_store().revoke(
        token_id, tenant_id=tenant_id, revoked_by=actor
    )
    if not revoked:
        raise HTTPException(404, "token not found or not revocable")
    await _audit().record(
        tenant_id=tenant_id,
        actor=actor,
        event="enrollment_token.revoked",
        payload={"token_id": str(token_id)},
    )


# ---------------------------------------------------------------------------
# Daemon-facing enrollment redemption (only unauthenticated surface)
# ---------------------------------------------------------------------------


@router.post(
    "/enroll",
    status_code=status.HTTP_201_CREATED,
)
async def enroll(
    body: AgentEnrollmentRequest,
    request: Request,
) -> AgentEnrollmentResponse:
    """Atomically redeem an enrollment token and return a signed cert.

    No FastAPI auth dependency: authentication is the bearer token
    itself, validated inside :meth:`EnrollmentTokenPersistence.redeem`
    (single-use, expiry-checked, optionally bound to ``agent_uuid``).
    A failed redemption never reveals **why** it failed — every
    invalid path returns 401 to deny token-state oracles.
    """
    actor = f"daemon:{body.agent_uuid}"

    # Stage 1: redeem token. The function returns the token row only
    # on a fully successful, atomic redemption.
    token = await _tokens_store().redeem(
        body.enrollment_token, agent_uuid=body.agent_uuid
    )
    if token is None:
        # Constant-time message: never differentiate failure modes.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "enrollment token invalid")

    tenant_id = token.tenant_id

    # Stage 2: sign CSR.
    try:
        issued = _ca().issue_from_csr(
            body.csr_pem,
            tenant_id=tenant_id,
            agent_uuid=body.agent_uuid,
        )
    except CSRValidationError as exc:
        await _audit().record(
            tenant_id=tenant_id,
            actor=actor,
            event="agent.enroll.csr_rejected",
            agent_uuid=body.agent_uuid,
            payload={
                "token_id": str(token.id),
                "error": str(exc),
            },
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    # Stage 3: persist agent + cert atomically per-table.
    record = AgentRecord(
        agent_uuid=body.agent_uuid,
        tenant_id=tenant_id,
        os=body.os,
        os_version=body.os_version,
        kernel_version=body.kernel_version,
        arch=body.arch,
        hostname=body.hostname,
        boot_id=body.boot_id,
        cpu_count=body.cpu_count,
        mem_total_bytes=body.mem_total_bytes,
        daemon_version=body.daemon_version,
        protocol_version=body.protocol_version,
        capabilities=body.declared_capabilities,
        labels=token.labels,
        status=AgentStatus.ENROLLED,
        enrolled_by=token.created_by,
    )
    await _agents_store().upsert(record, tenant_id=tenant_id)

    from plugins.red_agent.agent_models import AgentCertRecord, CertState

    await _certs_store().issue(
        AgentCertRecord(
            serial=issued.serial,
            agent_uuid=body.agent_uuid,
            tenant_id=tenant_id,
            fingerprint_sha256=issued.fingerprint_sha256,
            spiffe_uri=issued.spiffe_uri,
            not_before=issued.not_before,
            not_after=issued.not_after,
            state=CertState.ACTIVE,
        ),
        tenant_id=tenant_id,
    )

    await _audit().record(
        tenant_id=tenant_id,
        actor=actor,
        event="agent.enrolled",
        agent_uuid=body.agent_uuid,
        payload={
            "token_id": str(token.id),
            "serial": issued.serial,
            "fingerprint_sha256": issued.fingerprint_sha256,
            "spiffe_uri": issued.spiffe_uri,
            "not_after": issued.not_after.isoformat(),
            "platform": {
                "os": body.os.value,
                "arch": body.arch.value,
                "hostname": body.hostname,
            },
        },
    )

    ca = _ca()
    return AgentEnrollmentResponse(
        agent_uuid=body.agent_uuid,
        tenant_id=tenant_id,
        cert_pem=issued.cert_pem,
        chain_pem=issued.chain_pem,
        not_after=issued.not_after,
        spiffe_uri=issued.spiffe_uri,
        backend_grpc_endpoint=ca.config.backend_grpc_endpoint,
        root_ca_fingerprint_sha256=ca.root_fingerprint_sha256,
        server_hello_capabilities=body.declared_capabilities,
    )
