"""Outbound webhook notifier for clinical lifecycle events.

Hospitals routinely route critical events (red-flag triage, validation
rejection, EHR push failures) into Slack/Teams/PagerDuty via simple HTTPS
POST. This module provides a minimal, dependency-light dispatcher:

    * Multiple targets — each with its own URL + optional bearer token.
    * Per-target event allow-list, so an "operations" channel can be
      narrowed to red-flag events only.
    * HMAC-SHA256 signatures (header ``X-Baselithmed-Signature``) so the
      receiver can verify origin without trusting the network.
    * Fire-and-forget delivery; failures are captured in a per-instance
      counter so callers + tests can assert dispatch behaviour without
      racing on actual HTTP responses.

The dispatcher is **never** allowed to take down the clinical request
path. Every exception is swallowed and counted.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Final
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr


_DEFAULT_TIMEOUT_SECONDS: Final[float] = 5.0


class WebhookEventType(StrEnum):
    """Stable identifiers for the events callers can subscribe to."""

    RED_FLAG_DETECTED = "red_flag_detected"
    TRIAGE_FINALIZED = "triage_finalized"
    VALIDATION_RECORDED = "validation_recorded"
    EHR_PUSH_FAILED = "ehr_push_failed"


class WebhookTarget(BaseModel):
    """A single subscriber configuration."""

    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    secret: SecretStr | None = None
    events: tuple[WebhookEventType, ...] = Field(default_factory=tuple)
    timeout_seconds: float = Field(default=_DEFAULT_TIMEOUT_SECONDS, ge=0.5, le=60.0)
    verify_tls: bool = True

    def accepts(self, event: WebhookEventType) -> bool:
        """``True`` when the target subscribes to ``event`` (empty = all)."""
        if not self.events:
            return True
        return event in self.events


@dataclass
class DispatchCounters:
    """Per-instance dispatch stats — drives metrics + tests."""

    sent: int = 0
    failed: int = 0
    skipped_no_targets: int = 0
    skipped_not_subscribed: int = 0


@dataclass
class WebhookConfig:
    targets: list[WebhookTarget] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "WebhookConfig":
        """Load targets from ``BASELITHMED_WEBHOOKS_JSON``.

        The env var must be a JSON array of objects matching
        :class:`WebhookTarget`. Missing or unparseable → empty config.
        """
        raw = os.getenv("BASELITHMED_WEBHOOKS_JSON")
        if not raw:
            return cls()
        try:
            decoded = json.loads(raw)
            if not isinstance(decoded, list):
                return cls()
            targets = [WebhookTarget.model_validate(t) for t in decoded]
            return cls(targets=targets)
        except Exception:  # noqa: BLE001 — invalid config disables webhooks
            return cls()


def _sign_payload(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class WebhookDispatcher:
    """Async webhook fan-out — fire-and-forget, never raises."""

    def __init__(
        self,
        config: WebhookConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config or WebhookConfig()
        self._client = client  # test injection point
        self.counters = DispatchCounters()

    @property
    def enabled(self) -> bool:
        return bool(self._config.targets)

    def add_target(self, target: WebhookTarget) -> None:
        self._config.targets.append(target)

    async def dispatch(
        self,
        event: WebhookEventType,
        payload: dict[str, Any],
        *,
        session_id: str | None = None,
    ) -> None:
        """Fan out ``event`` + ``payload`` to all subscribed targets."""
        if not self._config.targets:
            self.counters.skipped_no_targets += 1
            return

        envelope = {
            "event": event.value,
            "event_id": str(uuid4()),
            "session_id": session_id,
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        body = json.dumps(envelope, sort_keys=True, default=str).encode("utf-8")

        await asyncio.gather(
            *[self._send_one(target, event, body) for target in self._config.targets],
            return_exceptions=True,
        )

    async def _send_one(
        self,
        target: WebhookTarget,
        event: WebhookEventType,
        body: bytes,
    ) -> None:
        if not target.accepts(event):
            self.counters.skipped_not_subscribed += 1
            return
        headers = {
            "Content-Type": "application/json",
            "X-Baselithmed-Event": event.value,
        }
        if target.secret is not None:
            headers["X-Baselithmed-Signature"] = _sign_payload(
                target.secret.get_secret_value(), body
            )

        client_cm: httpx.AsyncClient | None = None
        if self._client is None:
            client_cm = httpx.AsyncClient(
                timeout=target.timeout_seconds, verify=target.verify_tls
            )
            client = client_cm
        else:
            client = self._client

        try:
            try:
                response = await client.post(
                    str(target.url), content=body, headers=headers
                )
            except httpx.HTTPError:
                self.counters.failed += 1
                return
            if 200 <= response.status_code < 300:
                self.counters.sent += 1
            else:
                self.counters.failed += 1
        finally:
            if client_cm is not None:
                await client_cm.aclose()
