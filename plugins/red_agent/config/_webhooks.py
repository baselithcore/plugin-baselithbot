"""Outbound + inbound webhook configuration mixins."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class _WebhookOutConfig(BaseModel):
    webhook_enabled: bool = Field(
        default=False,
        description=(
            "Send an HMAC-signed OCSF event per qualifying finding to "
            "``webhook_url`` after persistence. Receivers can ingest the "
            "same shape used by ``/reports/{scan_id}/ocsf``."
        ),
    )
    webhook_url: str | None = Field(
        default=None,
        description="HTTPS endpoint that receives the OCSF event.",
    )
    webhook_secret: SecretStr | None = Field(
        default=None,
        description=(
            "HMAC-SHA256 secret. The signature ships in "
            "``X-RedAgent-Signature`` and ``X-Hub-Signature-256``."
        ),
    )
    webhook_min_severity: Literal["info", "low", "medium", "high", "critical"] = Field(
        default="high",
        description=(
            "Minimum severity at which a finding is forwarded. "
            "Defaults to HIGH so the receiver does not get spammed."
        ),
    )
    webhook_request_timeout_seconds: float = Field(
        default=10.0,
        description="HTTP timeout per webhook request.",
    )
    webhook_max_concurrent_requests: int = Field(
        default=4,
        description="Concurrency cap for webhook deliveries within a scan iteration.",
    )
    webhook_retry_count: int = Field(
        default=1,
        description=(
            "Retry attempts on transient (5xx / 429 / network) failures. "
            "0 = no retry; the notifier never loops infinitely."
        ),
    )


class _WebhookInConfig(BaseModel):
    webhook_in_enabled: bool = Field(
        default=False,
        description=(
            "Mount ``POST /red-agent/webhooks/soar`` to receive state "
            "updates from a downstream SOAR / ticketing system. The "
            "endpoint requires a valid HMAC signature when "
            "``webhook_in_require_signature`` is true (default)."
        ),
    )
    webhook_in_secret: SecretStr | None = Field(
        default=None,
        description=(
            "HMAC-SHA256 secret used to verify inbound webhook signatures. "
            "May reuse the same value as ``webhook_secret`` when the same "
            "downstream system is on both sides of the loop."
        ),
    )
    webhook_in_require_signature: bool = Field(
        default=True,
        description=(
            "Reject inbound webhooks without a valid HMAC signature. "
            "Set to false only on localhost dev or behind a trusted "
            "ingress that already authenticates the caller."
        ),
    )
    webhook_replay_protection: bool = Field(
        default=False,
        description=(
            "Enable Stripe-style replay protection on both inbound and "
            "outbound webhooks: timestamp is bound into the HMAC payload "
            "as ``hmac(secret, f'{ts}.{body}')`` and a per-request nonce "
            "is cached so the same payload cannot be re-delivered inside "
            "``webhook_replay_window_seconds``. Inbound rejects requests "
            "whose timestamp lies outside the window or whose nonce is "
            "already cached. Outbound notifier sets matching headers."
        ),
    )
    webhook_replay_window_seconds: int = Field(
        default=300,
        description=(
            "Half-window (seconds) for the timestamp freshness check. "
            "Inbound timestamps must satisfy "
            "``abs(now - ts) <= webhook_replay_window_seconds``."
        ),
    )
    webhook_replay_nonce_cache_size: int = Field(
        default=4096,
        description=(
            "Maximum number of nonces tracked per receiver. LRU + TTL "
            "eviction; sized to cover ``replay_window_seconds`` of peak "
            "traffic on most deployments."
        ),
    )
