"""Inbound webhook endpoints for SOAR / ticketing state-sync.

Receives signed POSTs from a downstream system and applies the
resulting state transition through ``RedAgentPersistence``. All routes
require a valid HMAC signature when ``RED_AGENT_WEBHOOK_IN_REQUIRE_SIGNATURE``
is true (default).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.integrations import WebhookReceiver
from plugins.red_agent.integrations.adapters import get_adapter
from plugins.red_agent.persistence import RedAgentPersistence

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["red-agent"])

_MAX_BODY_BYTES = 64 * 1024


def _get_receiver() -> WebhookReceiver:
    rcv = ServiceRegistry.get(WebhookReceiver)
    if rcv is None or not rcv.enabled:
        raise HTTPException(status_code=404, detail="webhook receiver disabled")
    return rcv


def _get_persistence() -> RedAgentPersistence:
    p = ServiceRegistry.get(RedAgentPersistence)
    if p is None or not p.available:
        raise HTTPException(status_code=503, detail="persistence unavailable")
    return p


def _get_audit() -> AuditLogger:
    a = ServiceRegistry.get(AuditLogger)
    if a is None:
        raise HTTPException(status_code=503, detail="audit unavailable")
    return a


async def _process_webhook(
    request: Request,
    *,
    adapter_name: str | None,
    sig_header: str | None,
    timestamp_header: str | None,
    nonce_header: str | None,
    receiver: WebhookReceiver,
    persistence: RedAgentPersistence,
    audit: AuditLogger,
) -> dict[str, Any]:
    body = await request.body()
    if len(body) > _MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="payload too large")
    if not receiver.verify_signature(
        body,
        sig_header,
        timestamp_header=timestamp_header,
        nonce_header=nonce_header,
    ):
        raise HTTPException(status_code=401, detail="invalid signature")
    adapter = None
    if adapter_name and adapter_name not in {"soar", "generic"}:
        adapter = get_adapter(adapter_name)
        if adapter is None:
            raise HTTPException(
                status_code=404, detail=f"unknown provider {adapter_name!r}"
            )
    event = await receiver.parse_event(body, persistence=persistence, adapter=adapter)
    if event is None:
        raise HTTPException(status_code=400, detail="cannot resolve finding")
    applied = await receiver.apply_event(event, persistence=persistence, audit=audit)
    return {
        "applied": applied,
        "finding_id": str(event.finding_id),
        "state": event.state.value if event.state else None,
        "provider": adapter_name or "generic",
    }


@router.post("/soar")
async def soar_webhook(
    request: Request,
    x_redagent_signature: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    x_redagent_timestamp: str | None = Header(default=None),
    x_redagent_nonce: str | None = Header(default=None),
    receiver: WebhookReceiver = Depends(_get_receiver),
    persistence: RedAgentPersistence = Depends(_get_persistence),
    audit: AuditLogger = Depends(_get_audit),
) -> dict[str, Any]:
    """Apply a generic-shape state update to the matching finding.

    Canonical payload::

        {"external_ref": "JIRA-1234", "state": "fixed", ...}

    For vendor-shaped payloads (Jira / ServiceNow / Linear) use
    ``POST /webhooks/{provider}`` instead.
    """
    return await _process_webhook(
        request,
        adapter_name=None,
        sig_header=x_redagent_signature or x_hub_signature_256,
        timestamp_header=x_redagent_timestamp,
        nonce_header=x_redagent_nonce,
        receiver=receiver,
        persistence=persistence,
        audit=audit,
    )


@router.post("/{provider}")
async def provider_webhook(
    provider: str,
    request: Request,
    x_redagent_signature: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    x_redagent_timestamp: str | None = Header(default=None),
    x_redagent_nonce: str | None = Header(default=None),
    receiver: WebhookReceiver = Depends(_get_receiver),
    persistence: RedAgentPersistence = Depends(_get_persistence),
    audit: AuditLogger = Depends(_get_audit),
) -> dict[str, Any]:
    """Apply a vendor-specific state update via the matching adapter.

    Supported provider names: ``jira``, ``servicenow``, ``linear``.
    Unknown values return 404. Use ``soar``/``generic`` for the
    canonical shape (no transformation).
    """
    return await _process_webhook(
        request,
        adapter_name=provider,
        sig_header=x_redagent_signature or x_hub_signature_256,
        timestamp_header=x_redagent_timestamp,
        nonce_header=x_redagent_nonce,
        receiver=receiver,
        persistence=persistence,
        audit=audit,
    )
