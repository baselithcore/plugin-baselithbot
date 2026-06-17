"""Real-time surface: the OpenWA inbound webhook and the dashboard SSE feed.

* ``POST /webhook`` — receives messages pushed by the OpenWA sidecar, validates
  the shared secret (constant-time), normalises the payload, and hands it to the
  service for end-to-end processing.
* ``GET /stream`` — a Server-Sent Events channel the dashboard subscribes to for
  live updates (inbound, draft, auto-send, queue, decisions).

Pure async; the SSE generator drains the per-client broker queue and exits
cleanly on disconnect.
"""

from __future__ import annotations

import asyncio
import hmac
import json
from collections.abc import AsyncIterator
from typing import Any

from core.observability.logging import get_logger

from .api_models import InboundWebhook, MessageResponse
from .config import TwinConfig
from .gateway.models import InboundMessage
from .i18n import negotiate_locale, translate
from .metrics import WEBHOOKS_TOTAL
from .service import TwinService

logger = get_logger(__name__)

# Idle keepalive: emit an SSE comment so proxies don't drop the connection and
# the browser's EventSource stays in the "open" state.
_HEARTBEAT_SECONDS = 20.0


def build_realtime_router(service: TwinService, config: TwinConfig) -> Any:
    """Build the webhook + SSE sub-router bound to the service."""
    from fastapi import APIRouter, Header, HTTPException
    from fastapi.responses import StreamingResponse

    router = APIRouter(tags=["twin:realtime"])
    secret = config.webhook_secret.get_secret_value()
    require_secret = config.require_webhook_secret

    @router.post("/webhook", response_model=MessageResponse)
    async def webhook(
        body: InboundWebhook,
        x_webhook_secret: str | None = Header(default=None),
        accept_language: str | None = Header(default=None),
    ) -> MessageResponse:
        """Receive an inbound WhatsApp message from the OpenWA sidecar.

        Fail-closed: when secret enforcement is on (default), a missing
        server-side secret or a mismatched header rejects the delivery — an
        unconfigured webhook never silently accepts spoofed inbound traffic.
        """
        locale = negotiate_locale(accept_language)
        if require_secret and not secret:
            WEBHOOKS_TOTAL.labels(result="rejected").inc()
            raise HTTPException(
                status_code=503,
                detail=translate("twin.webhook.secret_unset", locale),
            )
        if secret and not hmac.compare_digest(secret, x_webhook_secret or ""):
            WEBHOOKS_TOTAL.labels(result="rejected").inc()
            raise HTTPException(
                status_code=401,
                detail=translate("twin.webhook.invalid_secret", locale),
            )
        result = await service.ingest(
            InboundMessage(
                id=body.id,
                contact_id=body.contact_id,
                contact_name=body.contact_name,
                text=body.text,
                media=body.media,
                from_me=body.from_me,
            )
        )
        # ingest returns None for the owner's own messages *and* for a duplicate
        # delivery; the message log distinguishes them — for metrics we treat a
        # non-owner None as a duplicate drop.
        duplicate = result is None and not body.from_me
        WEBHOOKS_TOTAL.labels(result="duplicate" if duplicate else "accepted").inc()
        return MessageResponse(message=translate("twin.webhook.accepted", locale))

    @router.get("/stream")
    async def stream() -> StreamingResponse:
        """Stream live twin events to the dashboard as Server-Sent Events."""
        return StreamingResponse(
            _sse(service),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router


async def _sse(service: TwinService) -> AsyncIterator[str]:
    """Stream broker events as default (unnamed) SSE messages.

    Unnamed ``data:`` frames are delivered to ``EventSource.onmessage`` in the
    browser (named ``event:`` frames would need a per-type ``addEventListener``).
    The event's ``type`` travels inside the JSON body. An initial comment opens
    the stream immediately; an idle heartbeat keeps proxies from closing it.
    """
    yield ": connected\n\n"  # flush headers + fire onopen right away
    events = service.broker.subscribe()
    try:
        while True:
            try:
                event = await asyncio.wait_for(
                    events.__anext__(), timeout=_HEARTBEAT_SECONDS
                )
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # idle keepalive
                continue
            yield f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
    except (asyncio.CancelledError, StopAsyncIteration):
        return


__all__ = ["build_realtime_router"]
