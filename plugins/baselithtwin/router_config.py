"""Configuration & control endpoints for the dashboard.

Style training, whitelist management, salient-fact curation, the
human-in-the-loop approval queue, the audit trail, and the runtime kill-switch.
A thin, fully-async adapter over :class:`TwinService`; it owns no business logic.

Every state-changing route is guarded by the central RBAC slugs and the deciding
identity is taken from the authenticated principal — never from the request body
— so the audit trail records *who* actually approved a send. User-facing
acknowledgements are localized from the request ``Accept-Language`` header.
"""

from __future__ import annotations

from typing import Any

from core.auth.types import AuthUser
from fastapi import Depends, Request

from .audit.models import TwinAuditEvent
from .api_models import (
    FactRequest,
    MessageResponse,
    WhitelistRequest,
)
from .guards import actor_label
from .i18n import negotiate_locale, translate
from .models import (
    PendingReply,
    SalientFact,
    TwinStatus,
    WhitelistEntry,
)
from .service import TwinService
from .style.models import StyleProfile


def _client_ip(request: Request) -> str | None:
    """Best-effort client IP for the audit trail."""
    return request.client.host if request.client else None


def build_config_router(service: TwinService, version: str, guards: Any) -> Any:
    """Build the configuration/control sub-router bound to the service."""
    from fastapi import APIRouter, Header, HTTPException

    router = APIRouter(tags=["twin:config"])

    def _loc(accept_language: str | None) -> str:
        return negotiate_locale(accept_language)

    # -- Status & style (read) --------------------------------------------

    @router.get("/status", response_model=TwinStatus)
    async def status(_: AuthUser = Depends(guards.read)) -> TwinStatus:
        """Aggregate twin health for the dashboard header."""
        return await service.status(version)

    @router.get("/style", response_model=StyleProfile | None)
    async def get_style(
        _: AuthUser = Depends(guards.read),
    ) -> StyleProfile | None:
        """Return the current learned style profile, if trained."""
        return await service.get_style()

    @router.post("/style/train", response_model=StyleProfile)
    async def train_style(
        request: Request,
        principal: AuthUser = Depends(guards.manage),
    ) -> StyleProfile:
        """Recompute the style profile from the owner's message history."""
        return await service.train_style(
            actor=actor_label(principal), ip=_client_ip(request)
        )

    # -- Whitelist ---------------------------------------------------------

    @router.get("/whitelist", response_model=list[WhitelistEntry])
    async def list_whitelist(
        _: AuthUser = Depends(guards.read),
    ) -> list[WhitelistEntry]:
        """List contacts authorised for auto-reply."""
        return await service.list_whitelist()

    @router.post("/whitelist", response_model=MessageResponse)
    async def add_whitelist(
        body: WhitelistRequest,
        request: Request,
        principal: AuthUser = Depends(guards.manage),
        accept_language: str | None = Header(default=None),
    ) -> MessageResponse:
        """Authorise a contact for auto-reply."""
        await service.add_to_whitelist(
            WhitelistEntry(
                contact_id=body.contact_id,
                display_name=body.display_name,
                note=body.note,
            ),
            actor=actor_label(principal),
            ip=_client_ip(request),
        )
        return MessageResponse(
            message=translate(
                "twin.contact.allowed", _loc(accept_language), contact=body.contact_id
            )
        )

    @router.delete("/whitelist/{contact_id}", response_model=MessageResponse)
    async def remove_whitelist(
        contact_id: str,
        request: Request,
        principal: AuthUser = Depends(guards.manage),
        accept_language: str | None = Header(default=None),
    ) -> MessageResponse:
        """Revoke a contact's auto-reply authorisation."""
        removed = await service.remove_from_whitelist(
            contact_id, actor=actor_label(principal), ip=_client_ip(request)
        )
        if not removed:
            raise HTTPException(status_code=404, detail="contact not whitelisted")
        return MessageResponse(
            message=translate(
                "twin.contact.blocked", _loc(accept_language), contact=contact_id
            )
        )

    # -- Salient facts -----------------------------------------------------

    @router.get("/facts", response_model=list[SalientFact])
    async def list_facts(
        contact_id: str | None = None,
        _: AuthUser = Depends(guards.read),
    ) -> list[SalientFact]:
        """List salient facts, optionally scoped to a contact."""
        return await service.list_facts(contact_id)

    @router.post("/facts", response_model=MessageResponse, status_code=201)
    async def add_fact(
        body: FactRequest,
        request: Request,
        principal: AuthUser = Depends(guards.manage),
        accept_language: str | None = Header(default=None),
    ) -> MessageResponse:
        """Manually curate a salient fact into long-term memory."""
        await service.add_fact(
            contact_id=body.contact_id,
            text=body.text,
            salience=body.salience,
            tags=body.tags,
            actor=actor_label(principal),
            ip=_client_ip(request),
        )
        return MessageResponse(
            message=translate("twin.fact.stored", _loc(accept_language))
        )

    # -- HITL approval queue ----------------------------------------------

    @router.get("/replies", response_model=list[PendingReply])
    async def list_replies(
        only_queued: bool = False,
        _: AuthUser = Depends(guards.read),
    ) -> list[PendingReply]:
        """List tracked replies (auto-sent, queued, decided), newest first."""
        return await service.list_pending(only_queued=only_queued)

    @router.post("/replies/{reply_id}/approve", response_model=PendingReply)
    async def approve(
        reply_id: str,
        request: Request,
        principal: AuthUser = Depends(guards.approve),
    ) -> PendingReply:
        """Approve a queued reply and send it as the owner."""
        decided = await service.approve(
            reply_id, actor_label(principal), ip=_client_ip(request)
        )
        if decided is None:
            raise HTTPException(status_code=404, detail="reply not found")
        return decided

    @router.post("/replies/{reply_id}/reject", response_model=PendingReply)
    async def reject(
        reply_id: str,
        request: Request,
        principal: AuthUser = Depends(guards.approve),
    ) -> PendingReply:
        """Reject a queued reply; it is never sent."""
        decided = await service.reject(
            reply_id, actor_label(principal), ip=_client_ip(request)
        )
        if decided is None:
            raise HTTPException(status_code=404, detail="reply not found")
        return decided

    # -- Audit trail (read) -----------------------------------------------

    @router.get("/audit", response_model=list[TwinAuditEvent])
    async def list_audit(
        limit: int = 100,
        _: AuthUser = Depends(guards.read),
    ) -> list[TwinAuditEvent]:
        """Return the most recent audit-trail events, newest first."""
        return await service.list_audit(limit=limit)

    return router


__all__ = ["build_config_router"]
