"""Typed configuration for the Compliance (GRC) plugin.

Settings come from the plugin block in ``configs/plugins.yaml`` with environment
overrides under the ``COMPLIANCE_`` prefix. The plugin is a **governance
surface**, not a data store: it consumes the framework's compliance primitives
(``core.incidents`` NIS2/DORA, ``core.privacy`` GDPR DSR, ``core.thirdparty``
DORA register, ``core.transparency`` AI-Act). Defaults make it boot
self-contained: read-only views require an authenticated reader, mutations the
``admin`` (effective-wildcard) role.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

try:  # repo-root .env, so overrides load regardless of import order / CWD
    from core.config.env import PROJECT_ENV_FILE as _PROJECT_ENV_FILE
except Exception:  # noqa: BLE001 — degrade to default ".env" lookup
    _PROJECT_ENV_FILE = ".env"


class ComplianceConfig(BaseSettings):
    """Validated runtime configuration for the compliance console."""

    model_config = SettingsConfigDict(
        env_prefix="COMPLIANCE_",
        env_file=str(_PROJECT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=True, description="Whether the plugin is active.")

    require_admin: bool = Field(
        default=True,
        description=(
            "Gate mutating actions behind the auth `admin` role (effective "
            "wildcard). Set false only for trusted single-operator deployments."
        ),
    )

    @classmethod
    def from_plugin_config(cls, config: dict[str, Any] | None) -> "ComplianceConfig":
        """Build from the plugin config block, with env overrides applied."""
        return cls(**(config or {}))


__all__ = ["ComplianceConfig"]
