"""The async orchestrator wiring the digital twin together.

:class:`TwinService` owns the runtime: it ingests WhatsApp messages, learns the
owner's style, distils salient facts into long-term memory, drafts replies in
the owner's voice, and routes each draft through the autonomy policy to either
auto-send (via the gateway) or the human-in-the-loop queue. It depends only on
the abstract gateway/store Protocols, so backends are interchangeable.

All public methods are ``async`` and side-effects are published to the
:class:`EventBroker` so the dashboard reflects state in real time.
"""

from __future__ import annotations

import uuid

from core.observability.logging import get_logger

from .audit.models import AuditAction, TwinAuditEvent
from .broker import EventBroker
from .config import TwinConfig
from .gateway import build_gateway
from .gateway.models import InboundMessage, OutboundMessage
from .memory import LTMIndex, extract_facts
from .metrics import DECISIONS_TOTAL, DRAFTS_TOTAL, SENDS_TOTAL
from .models import (
    DraftReply,
    PendingReply,
    ReplyStatus,
    SalientFact,
    StreamEvent,
    TwinStatus,
    WhitelistEntry,
)
from .policy import Decision, RateBudget, decide
from .store import build_store
from .style import StyleProfile, extract_style
from .twin import DraftEngine

logger = get_logger(__name__)


class TwinService:
    """Coordinates ingest, cognition, governance, and delivery for one owner."""

    def __init__(self, config: TwinConfig) -> None:
        self._config = config
        # Tenant-prefixed owner partition — single owner per process today, but
        # the store key is already tenancy-ready for a future multi-account split.
        self._owner_id = f"{config.tenant_id}:{config.owner_name or 'owner'}"
        self._store = build_store(config)
        self._gateway = build_gateway(config)
        self._engine = DraftEngine(config.owner_name)
        self._ltm = LTMIndex(semantic_enabled=config.semantic_enabled)
        self._rate = RateBudget(config.max_auto_replies_per_minute)
        self._broker = EventBroker()

    # -- Lifecycle ---------------------------------------------------------

    async def initialize(self) -> None:
        """Prepare the store and connect the gateway (best-effort)."""
        await self._store.initialize()
        await self._gateway.connect()

    async def shutdown(self) -> None:
        """Disconnect the gateway on teardown."""
        await self._gateway.disconnect()

    @property
    def broker(self) -> EventBroker:
        """The event broker SSE clients subscribe to."""
        return self._broker

    # -- Ingest ------------------------------------------------------------

    async def ingest(self, message: InboundMessage) -> PendingReply | None:
        """Process one inbound message end-to-end.

        Records the message, updates long-term memory, and — for messages from a
        contact (not the owner) — drafts a reply and applies the autonomy policy.

        Returns:
            The tracked :class:`PendingReply` when a draft was produced (queued
            or auto-sent), or ``None`` for the owner's own messages or a
            duplicate (already-processed) delivery.
        """
        if not await self._store.mark_seen(self._owner_id, message.id):
            logger.info("twin_ingest_duplicate", message_id=message.id)
            return None  # idempotency: drop a re-delivered webhook.
        await self._store.add_message(self._owner_id, message)
        await self._absorb_facts(message)
        await self._publish("inbound", message.model_dump(mode="json"))

        if message.from_me:
            return None  # owner's own message — learn from it, never reply to it.

        draft = await self._make_draft(message)
        await self._publish("draft", draft.model_dump(mode="json"))
        return await self._govern(message, draft)

    async def _absorb_facts(self, message: InboundMessage) -> None:
        """Extract and persist salient facts from an inbound message."""
        for fact in extract_facts(message):
            await self._store.add_fact(self._owner_id, fact)

    async def _make_draft(self, message: InboundMessage) -> DraftReply:
        """Build a style- and memory-grounded draft for an inbound message."""
        profile = await self._store.get_style(self._owner_id)
        all_facts = await self._store.list_facts(self._owner_id, message.contact_id)
        facts = await self._ltm.relevant(
            message.text, all_facts, top_k=self._config.ltm_top_k
        )
        history = await self._store.recent_messages(
            self._owner_id, message.contact_id, limit=12
        )
        draft = await self._engine.draft(message, profile, facts, history)
        DRAFTS_TOTAL.labels(degraded=str(draft.degraded).lower()).inc()
        return draft

    async def _govern(self, message: InboundMessage, draft: DraftReply) -> PendingReply:
        """Apply the autonomy policy and either auto-send or queue the draft."""
        whitelisted = await self._store.is_whitelisted(
            self._owner_id, message.contact_id
        )
        paused = await self._store.is_paused(self._owner_id)
        decision = (
            Decision.QUEUE
            if paused
            else decide(
                self._config.autonomy,
                is_whitelisted=whitelisted,
                rate_ok=self._rate.allow(message.contact_id),
                confidence=draft.confidence,
            )
        )
        DECISIONS_TOTAL.labels(decision=decision.value).inc()
        pending = PendingReply(
            id=str(uuid.uuid4()),
            contact_id=message.contact_id,
            in_reply_to=message.id,
            inbound_text=message.text,
            draft=draft,
            status=ReplyStatus.QUEUED,
        )
        if decision is Decision.AUTO_SEND:
            return await self._send(pending, decided_by="policy:auto")
        await self._store.save_pending(self._owner_id, pending)
        await self._publish("queued", pending.model_dump(mode="json"))
        return pending

    # -- Delivery ----------------------------------------------------------

    async def _send(
        self, pending: PendingReply, decided_by: str, ip: str | None = None
    ) -> PendingReply:
        """Send a reply via the gateway and record the outcome (+ audit/metrics)."""
        receipt = await self._gateway.send(
            OutboundMessage(
                contact_id=pending.contact_id,
                text=pending.draft.text,
                quoted_message_id=pending.in_reply_to,
            )
        )
        auto = decided_by == "policy:auto"
        status = ReplyStatus.AUTO_SENT if auto else ReplyStatus.APPROVED
        updated = pending.model_copy(
            update={
                "status": status if receipt.ok else ReplyStatus.FAILED,
                "decided_by": decided_by,
                "decided_at": _now(),
            }
        )
        await self._store.save_pending(self._owner_id, updated)
        SENDS_TOTAL.labels(result="ok" if receipt.ok else "failed").inc()
        if not receipt.ok:
            action = AuditAction.REPLY_SEND_FAILED
        elif auto:
            action = AuditAction.REPLY_AUTO_SENT
        else:
            action = AuditAction.REPLY_APPROVED
        await self._audit(
            action,
            actor=decided_by,
            resource=pending.id,
            success=receipt.ok,
            ip=ip,
            details={"contact_id": pending.contact_id},
        )
        event = "auto_sent" if status is ReplyStatus.AUTO_SENT else "decided"
        await self._publish(event, updated.model_dump(mode="json"))
        return updated

    # -- Human-in-the-loop -------------------------------------------------

    async def approve(
        self, reply_id: str, actor: str, ip: str | None = None
    ) -> PendingReply | None:
        """Approve a queued reply and send it as the owner."""
        pending = await self._store.get_pending(self._owner_id, reply_id)
        if pending is None or pending.status is not ReplyStatus.QUEUED:
            return pending if pending else None
        return await self._send(pending, decided_by=actor, ip=ip)

    async def reject(
        self, reply_id: str, actor: str, ip: str | None = None
    ) -> PendingReply | None:
        """Reject a queued reply; it is never sent."""
        pending = await self._store.get_pending(self._owner_id, reply_id)
        if pending is None:
            return None
        updated = pending.model_copy(
            update={
                "status": ReplyStatus.REJECTED,
                "decided_by": actor,
                "decided_at": _now(),
            }
        )
        await self._store.save_pending(self._owner_id, updated)
        await self._audit(
            AuditAction.REPLY_REJECTED, actor=actor, resource=reply_id, ip=ip
        )
        await self._publish("decided", updated.model_dump(mode="json"))
        return updated

    async def list_pending(self, only_queued: bool = False) -> list[PendingReply]:
        """List tracked replies, newest first."""
        return await self._store.list_pending(self._owner_id, only_queued=only_queued)

    # -- Style -------------------------------------------------------------

    async def train_style(
        self, actor: str = "system", ip: str | None = None
    ) -> StyleProfile:
        """Recompute the owner's style profile from their message history."""
        messages = await self._store.owner_messages(self._owner_id)
        profile = extract_style(self._owner_id, messages)
        await self._store.save_style(self._owner_id, profile)
        await self._audit(
            AuditAction.STYLE_TRAINED,
            actor=actor,
            ip=ip,
            details={"sample_size": profile.sample_size},
        )
        await self._publish("style_trained", profile.model_dump(mode="json"))
        return profile

    async def get_style(self) -> StyleProfile | None:
        """Return the current style profile, if trained."""
        return await self._store.get_style(self._owner_id)

    # -- Whitelist ---------------------------------------------------------

    async def add_to_whitelist(
        self, entry: WhitelistEntry, actor: str = "system", ip: str | None = None
    ) -> None:
        """Authorise a contact for auto-reply."""
        await self._store.add_whitelist(self._owner_id, entry)
        await self._audit(
            AuditAction.WHITELIST_ADDED, actor=actor, resource=entry.contact_id, ip=ip
        )

    async def remove_from_whitelist(
        self, contact_id: str, actor: str = "system", ip: str | None = None
    ) -> bool:
        """Revoke a contact's auto-reply authorisation."""
        removed = await self._store.remove_whitelist(self._owner_id, contact_id)
        if removed:
            await self._audit(
                AuditAction.WHITELIST_REMOVED,
                actor=actor,
                resource=contact_id,
                ip=ip,
            )
        return removed

    async def list_whitelist(self) -> list[WhitelistEntry]:
        """Return the auto-reply whitelist."""
        return await self._store.list_whitelist(self._owner_id)

    # -- Memory ------------------------------------------------------------

    async def list_facts(self, contact_id: str | None = None) -> list[SalientFact]:
        """List salient facts, optionally scoped to a contact."""
        return await self._store.list_facts(self._owner_id, contact_id)

    # -- Audit & runtime control ------------------------------------------

    async def list_audit(self, limit: int = 100) -> list[TwinAuditEvent]:
        """Return the most recent audit-trail events, newest first."""
        return await self._store.list_audit(self._owner_id, limit=limit)

    async def is_paused(self) -> bool:
        """Whether auto-send is currently paused (kill-switch engaged)."""
        return await self._store.is_paused(self._owner_id)

    async def set_paused(
        self, paused: bool, actor: str = "system", ip: str | None = None
    ) -> bool:
        """Engage/release the kill-switch; while paused nothing is auto-sent."""
        await self._store.set_paused(self._owner_id, paused)
        await self._audit(
            AuditAction.TWIN_PAUSED if paused else AuditAction.TWIN_RESUMED,
            actor=actor,
            ip=ip,
        )
        await self._publish("control", {"paused": paused})
        return paused

    async def _audit(
        self,
        action: AuditAction,
        *,
        actor: str,
        resource: str | None = None,
        success: bool = True,
        ip: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Append an immutable audit event (best-effort mirror to core audit)."""
        event = TwinAuditEvent(
            id=str(uuid.uuid4()),
            action=action,
            actor=actor,
            resource=resource,
            success=success,
            ip_address=ip,
            details=details or {},
        )
        await self._store.record_audit(self._owner_id, event)
        await self._mirror_core_audit(event)

    async def _mirror_core_audit(self, event: TwinAuditEvent) -> None:
        """Best-effort echo to the framework audit logger (never raises)."""
        try:
            from core.observability.audit import AuditEventType, get_audit_logger

            await get_audit_logger().log(
                AuditEventType.CUSTOM,
                user_id=event.actor,
                resource="baselithtwin",
                action=event.action.value,
                success=event.success,
                ip_address=event.ip_address,
                details=event.details,
            )
        except Exception:  # noqa: BLE001 — mirror is optional
            return None

    async def add_fact(
        self,
        *,
        contact_id: str,
        text: str,
        salience: float = 0.6,
        tags: list[str] | None = None,
        actor: str = "system",
        ip: str | None = None,
    ) -> SalientFact:
        """Manually curate a salient fact into long-term memory."""
        fact = SalientFact(
            id=str(uuid.uuid4()),
            contact_id=contact_id,
            text=text,
            salience=salience,
            tags=tags or [],
        )
        stored = await self._store.add_fact(self._owner_id, fact)
        await self._audit(
            AuditAction.FACT_CURATED, actor=actor, resource=contact_id, ip=ip
        )
        return stored

    # -- Status & realtime -------------------------------------------------

    async def status(self, version: str) -> TwinStatus:
        """Build the aggregate dashboard status."""
        profile = await self._store.get_style(self._owner_id)
        whitelist = await self._store.list_whitelist(self._owner_id)
        pending = await self._store.list_pending(self._owner_id, only_queued=True)
        facts = await self._store.list_facts(self._owner_id)
        return TwinStatus(
            owner_name=self._config.owner_name,
            autonomy=self._config.autonomy.value,
            gateway=self._config.gateway.value,
            gateway_connected=await self._gateway.is_connected(),
            style_trained=bool(profile and profile.trained),
            style_messages=profile.sample_size if profile else 0,
            whitelist_size=len(whitelist),
            pending_replies=len(pending),
            salient_facts=len(facts),
            paused=await self._store.is_paused(self._owner_id),
            version=version,
        )

    async def _publish(self, event_type: str, payload: dict) -> None:
        """Emit a real-time event to the dashboard SSE channel."""
        await self._broker.publish(StreamEvent(type=event_type, payload=payload))


def _now():
    """Timezone-aware UTC now (indirection keeps imports local to one place)."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


__all__ = ["TwinService"]
