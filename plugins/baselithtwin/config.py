"""Typed configuration for the BaselithTwin plugin.

Settings are sourced from the plugin config block (``configs/plugins.yaml``)
with environment overrides under the ``BASELITH_TWIN_`` prefix. Every credential
is wrapped in :class:`pydantic.SecretStr` so it never leaks through ``repr`` or
Sentry frames.

The defaults make the plugin boot self-contained with **zero external infra**:
in-memory persistence, the ``fake`` gateway, and a ``whitelist`` autonomy mode
that auto-replies only to explicitly approved contacts (everything else is
queued for human review).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

try:  # repo-root .env, so overrides load regardless of import order / CWD
    from core.config.env import PROJECT_ENV_FILE as _PROJECT_ENV_FILE
except Exception:  # noqa: BLE001 — degrade to default ".env" lookup
    _PROJECT_ENV_FILE = ".env"


class AutonomyMode(str, Enum):
    """How freely the twin is allowed to send replies on the user's behalf."""

    SUGGEST = "suggest"  # every draft is queued; nothing is auto-sent.
    WHITELIST = "whitelist"  # auto-send to allow-listed contacts; queue the rest.
    FULL = "full"  # auto-send to everyone (high risk; opt-in only).


class GatewayKind(str, Enum):
    """Which :class:`WhatsAppGateway` backend to construct."""

    FAKE = "fake"  # in-memory loopback gateway (default; tests & local dev).
    OPENWA = "openwa"  # @open-wa/wa-automate REST + webhook sidecar.


class PersistenceKind(str, Enum):
    """Which persistence backend the store factory should build."""

    MEMORY = "memory"  # ephemeral, zero-config default.
    POSTGRES = "postgres"  # durable JSONB store (opt-in).


class TwinConfig(BaseSettings):
    """Validated runtime configuration for the digital twin."""

    model_config = SettingsConfigDict(
        env_prefix="BASELITH_TWIN_",
        env_file=str(_PROJECT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=True, description="Whether the plugin is active.")

    # -- Identity & tenancy -------------------------------------------------
    owner_name: str = Field(
        default="Owner",
        description="Display name of the human the twin impersonates.",
    )
    tenant_id: str = Field(
        default="default",
        description="Logical tenant the owner belongs to (state-partition seam).",
    )
    owner_locale: str = Field(
        default="it",
        description="Default locale for the owner's persona and UI fallback.",
    )

    # -- Autonomy & governance ---------------------------------------------
    autonomy: AutonomyMode = Field(
        default=AutonomyMode.WHITELIST,
        description="Reply autonomy level. 'whitelist' is the safe default.",
    )
    max_auto_replies_per_minute: int = Field(
        default=6,
        ge=0,
        description="Anti-runaway cap on auto-sent replies per contact/minute.",
    )
    require_admin: bool = Field(
        default=True,
        description=(
            "When auth is NOT enforced, require the local operator to hold the "
            "admin role for runtime control (pause/resume). Production-safe default."
        ),
    )
    require_webhook_secret: bool = Field(
        default=True,
        description=(
            "Reject inbound webhooks unless a shared secret is configured and "
            "matches. Fail-closed: an unset secret blocks all inbound delivery."
        ),
    )

    # -- Gateway (OpenWA) ---------------------------------------------------
    gateway: GatewayKind = Field(
        default=GatewayKind.FAKE,
        description="WhatsApp gateway backend.",
    )
    openwa_base_url: str = Field(
        default="http://localhost:8002",
        description="Base URL of the @open-wa/wa-automate REST sidecar.",
    )
    openwa_session: str = Field(
        default="baselith-twin",
        description="OpenWA session name.",
    )
    openwa_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Bearer key for the OpenWA REST API (if configured).",
    )
    webhook_secret: SecretStr = Field(
        default=SecretStr(""),
        description="Shared secret validated on inbound OpenWA webhooks.",
    )

    # -- Cognition ----------------------------------------------------------
    style_min_messages: int = Field(
        default=20,
        ge=1,
        description="Minimum owner messages required before a style profile is trusted.",
    )
    ltm_top_k: int = Field(
        default=5,
        ge=0,
        description="Salient facts retrieved from LTM per draft.",
    )
    semantic_enabled: bool = Field(
        default=False,
        description="Opt-in dense embeddings for LTM (falls back to keyword scoring).",
    )

    # -- Persistence --------------------------------------------------------
    persistence: PersistenceKind = Field(
        default=PersistenceKind.MEMORY,
        description="Storage backend ('memory' default; 'postgres' is durable).",
    )

    @classmethod
    def from_plugin_config(cls, raw: dict | None) -> "TwinConfig":
        """Build a config from the plugin's raw dict, honouring env overrides.

        Unknown keys are ignored (``extra='ignore'``) so the shared plugin
        manifest can carry framework-level keys without breaking validation.
        """
        return cls(**(raw or {}))


__all__ = [
    "TwinConfig",
    "AutonomyMode",
    "GatewayKind",
    "PersistenceKind",
]
