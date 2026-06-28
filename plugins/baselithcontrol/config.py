"""Typed configuration for the BaselithControl plugin.

Settings come from the plugin block in ``configs/plugins.yaml`` with environment
overrides under the ``BASELITHCONTROL_`` prefix. The defaults make the plugin
boot self-contained with **zero external infra**: read-only aggregation is open
to any authenticated reader, lifecycle mutations require the ``admin`` role, and
the optional autonomy gate is off (RBAC is the primary control gate). Tighten
per environment by exporting scoped overrides before boot.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

try:  # repo-root .env, so overrides load regardless of import order / CWD
    from core.config.env import PROJECT_ENV_FILE as _PROJECT_ENV_FILE
except Exception:  # noqa: BLE001 — degrade to default ".env" lookup
    _PROJECT_ENV_FILE = ".env"


class GateLevel(str, Enum):
    """Optional autonomy gate applied to destructive lifecycle actions.

    Maps onto :class:`core.orchestration.autonomy.AutonomyLevel`. The default
    ``open`` level performs no extra approval check — the ``admin`` RBAC role is
    the gate. Stricter levels require a human-approval channel to be wired, and
    fail closed when one is absent.
    """

    OPEN = "open"  # AutonomyLevel.FULLY_AUTONOMOUS — RBAC is the only gate.
    SEMI = "semi"  # AutonomyLevel.SEMI_AUTONOMOUS — destructive needs approval.
    STRICT = "strict"  # AutonomyLevel.SUPERVISED — mutating + destructive gated.


class ControlConfig(BaseSettings):
    """Validated runtime configuration for the control-plane dashboard."""

    model_config = SettingsConfigDict(
        env_prefix="BASELITHCONTROL_",
        env_file=str(_PROJECT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=True, description="Whether the plugin is active.")

    # -- Access control -----------------------------------------------------
    require_admin: bool = Field(
        default=True,
        description=(
            "Gate lifecycle actions behind the auth `admin` role. Set false to "
            "allow any authenticated user (trusted single-operator deployments)."
        ),
    )

    # -- Autonomy gate (opt-in, layered on top of RBAC) ---------------------
    gate_level: GateLevel = Field(
        default=GateLevel.OPEN,
        description="Extra approval gate for destructive actions. 'open' = RBAC only.",
    )
    approval_timeout_seconds: int = Field(
        default=60,
        ge=0,
        description="How long to wait for a human approval before failing closed.",
    )

    # -- Realtime -----------------------------------------------------------
    sse_heartbeat_seconds: float = Field(
        default=20.0,
        gt=0,
        description="Idle keepalive interval for the SSE stream.",
    )

    # -- Audit --------------------------------------------------------------
    audit_max_events: int = Field(
        default=500,
        ge=0,
        description="Ring-buffer capacity for the in-memory audit trail.",
    )

    # -- Retained telemetry (server-side, survive page reloads) -------------
    volume_interval_seconds: float = Field(
        default=5.0,
        gt=0,
        description="Sampling cadence for the retained request-volume series.",
    )
    volume_capacity: int = Field(
        default=720,  # 720 × 5s ≈ 1 hour of history
        ge=1,
        description="Ring-buffer capacity for the request-volume time-series.",
    )
    lifecycle_capacity: int = Field(
        default=200,
        ge=1,
        description="Ring-buffer capacity for the retained lifecycle timeline.",
    )

    # -- News ticker (public RSS/Atom headlines on the dashboard home) -------
    news_enabled: bool = Field(
        default=True,
        description="Whether the scrolling news ticker fetches and renders feeds.",
    )
    news_feeds: list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            "Override feed list: a list of {url, source, category, lang} dicts. "
            "When unset, a curated default set (AI/tech/cyber) is used. Every URL "
            "is SSRF-validated at fetch time regardless of source."
        ),
    )
    news_cache_ttl_seconds: float = Field(
        default=600.0,
        gt=0,
        description="How long a fetched news snapshot is cached before refresh.",
    )
    news_max_items: int = Field(
        default=40,
        ge=1,
        le=200,
        description="Maximum merged headlines kept in the ticker snapshot.",
    )
    news_fetch_timeout_seconds: float = Field(
        default=6.0,
        gt=0,
        description="Per-feed HTTP timeout when refreshing the news snapshot.",
    )
    news_allow_internal: bool = Field(
        default=False,
        description=(
            "Skip the SSRF private/loopback checks for news feeds (dev only — "
            "lets you point the ticker at a local fixture feed)."
        ),
    )

    # -- Live log viewer (in-memory tail of application logs) ---------------
    logs_enabled: bool = Field(
        default=True,
        description="Whether the root log handler captures records for the viewer.",
    )
    log_buffer_capacity: int = Field(
        default=2000,
        ge=1,
        le=20000,
        description="Ring-buffer capacity for the retained application-log tail.",
    )

    @classmethod
    def from_plugin_config(cls, config: dict[str, Any] | None) -> "ControlConfig":
        """Build from the plugin config block, with env overrides applied."""
        return cls(**(config or {}))


__all__ = ["ControlConfig", "GateLevel"]
