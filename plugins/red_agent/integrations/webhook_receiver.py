"""Inbound webhook receiver for SOAR / ticketing state-sync.

Closes the loop opened by :class:`WebhookNotifier`: when a downstream
system (Jira / ServiceNow / Linear / PagerDuty / generic) emits an
event indicating a ticket transition, the receiver applies the
corresponding state change to the original finding.

Generic payload shape (operator-agnostic):

.. code-block:: json

    {
      "external_ref": "JIRA-1234",       // OR "finding_id": "uuid"
      "state": "fixed | wontfix | accepted | triaged | open",
      "notes": "optional free text",
      "assignee": "optional",
      "actor": "optional"
    }

Provider-specific shape adaptation (Jira / ServiceNow / Linear) lives
in upcoming sub-modules; the generic adapter is the baseline that any
SOAR integration can target with a small JSON transformation.

Security:

* ``X-RedAgent-Signature: sha256=<hex>`` (and ``X-Hub-Signature-256``)
  is verified against ``secret`` using :func:`hmac.compare_digest`.
* Bodies above ``max_body_bytes`` are rejected upstream (router level).
* Audit event ``soar.webhook_applied`` carries the resolved finding id
  + the new state.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from core.observability.logging import get_logger
from plugins.red_agent.models import FindingState, FindingTriageUpdate

if TYPE_CHECKING:  # pragma: no cover
    from plugins.red_agent.audit import AuditLogger
    from plugins.red_agent.persistence import RedAgentPersistence

logger = get_logger(__name__)

_DEFAULT_REPLAY_WINDOW_SECONDS = 300
_DEFAULT_NONCE_CACHE_SIZE = 4096


class _NonceCache:
    """Bounded TTL set of recently-seen nonces.

    Implements a simple LRU + clock-based eviction: every ``check`` call
    drops entries older than ``ttl_seconds`` and caps total size at
    ``max_size``. ``check_and_add`` returns True when the nonce is fresh
    (and records it); False when it has been seen within the window.
    """

    def __init__(self, *, ttl_seconds: int, max_size: int) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._seen: OrderedDict[str, float] = OrderedDict()

    def check_and_add(self, nonce: str, *, now: float | None = None) -> bool:
        ts = now if now is not None else time.monotonic()
        self._evict(ts)
        if nonce in self._seen:
            return False
        self._seen[nonce] = ts
        if len(self._seen) > self.max_size:
            self._seen.popitem(last=False)
        return True

    def _evict(self, now: float) -> None:
        cutoff = now - self.ttl_seconds
        while self._seen:
            _, oldest_ts = next(iter(self._seen.items()))
            if oldest_ts < cutoff:
                self._seen.popitem(last=False)
            else:
                break


_STATE_FROM_STR: dict[str, FindingState] = {
    "open": FindingState.OPEN,
    "triaged": FindingState.TRIAGED,
    "fixed": FindingState.FIXED,
    "wontfix": FindingState.WONTFIX,
    "accepted": FindingState.ACCEPTED,
    # Common SOAR aliases
    "resolved": FindingState.FIXED,
    "closed": FindingState.FIXED,
    "done": FindingState.FIXED,
    "in_progress": FindingState.TRIAGED,
    "in progress": FindingState.TRIAGED,
}


@dataclass(slots=True)
class WebhookEvent:
    """Normalized inbound event ready to apply via persistence."""

    finding_id: UUID
    state: FindingState | None
    notes: str | None = None
    assignee: str | None = None
    actor: str = "soar_webhook"


class WebhookSignatureInvalid(Exception):
    """HMAC signature verification failed."""


class WebhookReceiver:
    """Verify, parse, and apply inbound SOAR webhook events."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        secret: str | None = None,
        require_signature: bool = True,
        replay_protection: bool = False,
        replay_window_seconds: int = _DEFAULT_REPLAY_WINDOW_SECONDS,
        nonce_cache_size: int = _DEFAULT_NONCE_CACHE_SIZE,
    ) -> None:
        self.enabled = enabled
        self.secret = secret
        self.require_signature = require_signature
        self.replay_protection = replay_protection
        self.replay_window_seconds = replay_window_seconds
        self._nonces = _NonceCache(
            ttl_seconds=replay_window_seconds,
            max_size=nonce_cache_size,
        )

    # --- signature verification --------------------------------------

    def verify_signature(
        self,
        body: bytes,
        signature_header: str | None,
        *,
        timestamp_header: str | None = None,
        nonce_header: str | None = None,
    ) -> bool:
        """Constant-time HMAC-SHA256 verification.

        Two modes:

        * **Default** — body-only HMAC. Header format: ``sha256=<hex>``.
        * **Replay-protected** (``replay_protection=True``) — Stripe-style
          ``sha256(secret, f"{ts}.{body}")``. Requires
          ``X-RedAgent-Timestamp`` within ``replay_window_seconds`` of
          server time. Optional ``X-RedAgent-Nonce`` is cached so the
          same payload cannot be replayed inside the window.

        Returns False on missing / malformed inputs or any mismatch.
        """
        if not self.require_signature:
            return True
        if not self.secret or not signature_header:
            return False
        prefix = "sha256="
        if not signature_header.startswith(prefix):
            return False
        provided = signature_header[len(prefix) :]

        if self.replay_protection:
            if not self._timestamp_in_window(timestamp_header):
                return False
            payload = f"{timestamp_header}.".encode() + body
        else:
            payload = body

        expected = hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(provided, expected):
            return False

        if self.replay_protection and nonce_header:
            if not self._nonces.check_and_add(nonce_header):
                logger.warning(
                    "red_agent.webhook.nonce_replay",
                    extra={"nonce": nonce_header[:32]},
                )
                return False
        return True

    def _timestamp_in_window(self, ts_header: str | None) -> bool:
        if not ts_header:
            return False
        try:
            ts = int(ts_header)
        except (TypeError, ValueError):
            return False
        now = int(time.time())
        return abs(now - ts) <= self.replay_window_seconds

    # --- parse + apply ----------------------------------------------

    async def parse_event(
        self,
        body: bytes,
        *,
        persistence: "RedAgentPersistence",
        adapter: Any | None = None,
    ) -> WebhookEvent | None:
        """Decode the JSON body and resolve to a :class:`WebhookEvent`.

        When ``adapter`` is supplied, the raw vendor payload is first
        transformed into the canonical ``{external_ref, state, ...}``
        shape; otherwise the body is parsed as already-canonical.
        Returns ``None`` on malformed JSON, missing finding reference,
        or unresolvable ``external_ref``.
        """
        try:
            payload: Any = json.loads(body.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None

        if adapter is not None:
            try:
                canonical = adapter.parse(payload)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"red_agent.webhook.adapter.{getattr(adapter, 'name', 'unknown')}.failed",
                    extra={"err": str(exc)},
                )
                return None
            if not isinstance(canonical, dict):
                return None
            payload = canonical

        finding_id = await self._resolve_finding_id(payload, persistence)
        if finding_id is None:
            return None

        state = _STATE_FROM_STR.get(str(payload.get("state", "")).lower())
        notes = payload.get("notes")
        assignee = payload.get("assignee")
        actor = str(payload.get("actor") or "soar_webhook")
        return WebhookEvent(
            finding_id=finding_id,
            state=state,
            notes=notes if isinstance(notes, str) else None,
            assignee=assignee if isinstance(assignee, str) else None,
            actor=actor,
        )

    async def apply_event(
        self,
        event: WebhookEvent,
        *,
        persistence: "RedAgentPersistence",
        audit: "AuditLogger",
    ) -> bool:
        """Apply the parsed event to persistence + audit. Returns True on success."""
        update = FindingTriageUpdate(
            state=event.state,
            assignee=event.assignee,
            notes=event.notes,
        )
        ok = await persistence.update_finding_triage(
            event.finding_id, update, actor=event.actor
        )
        await audit.record(
            scan_id=None,
            actor=event.actor,
            event="soar.webhook_applied",
            payload={
                "finding_id": str(event.finding_id),
                "state": event.state.value if event.state else None,
                "applied": ok,
                "assignee": event.assignee,
            },
        )
        return ok

    @staticmethod
    async def _resolve_finding_id(
        payload: dict[str, Any], persistence: "RedAgentPersistence"
    ) -> UUID | None:
        # Direct finding_id wins.
        raw_id = payload.get("finding_id")
        if isinstance(raw_id, str):
            try:
                return UUID(raw_id)
            except ValueError:
                pass
        external_ref = payload.get("external_ref")
        if isinstance(external_ref, str) and external_ref:
            return await persistence.find_by_external_ref(external_ref)
        return None
