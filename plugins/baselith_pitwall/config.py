"""Typed configuration for the BaselithPitwall plugin.

Settings come from the plugin block in ``configs/plugins.yaml`` with environment
overrides under the ``BASELITH_PITWALL_`` prefix. Defaults make the plugin boot
self-contained with **zero external infra**: a built-in simulated telemetry
source feeds the async queue, the LLM is used only to phrase recommendations
(deterministic templates otherwise), and semantic historical recall is opt-in.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

try:  # repo-root .env, so overrides load regardless of import order / CWD
    from core.config.env import PROJECT_ENV_FILE as _PROJECT_ENV_FILE
except Exception:  # noqa: BLE001 — degrade to default ".env" lookup
    _PROJECT_ENV_FILE = ".env"


class PitwallConfig(BaseSettings):
    """Validated runtime configuration for the digital pit wall."""

    model_config = SettingsConfigDict(
        env_prefix="BASELITH_PITWALL_",
        env_file=str(_PROJECT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=True, description="Whether the plugin is active.")

    # -- Persistence (opt-in) ----------------------------------------------
    persistence: str = Field(
        default="memory",
        description="Durable store backend: 'memory' (default) or 'postgres'.",
    )
    persist_snapshots: bool = Field(
        default=False,
        description="Persist per-lap stint snapshots for post-race debrief.",
    )

    # -- Multi-tenancy & RBAC (opt-in) -------------------------------------
    auth_enabled: bool = Field(
        default=False,
        description="Gate routes via the central auth plugin RBAC. When True the "
        "tenant is taken from the trusted JWT context, not the header.",
    )
    tenant_header: str = Field(
        default="X-Tenant-ID",
        description="Request header carrying the tenant id in lightweight mode.",
    )

    # -- API hardening -----------------------------------------------------
    rate_limit_per_min: int = Field(
        default=0,
        ge=0,
        description="Per-tenant request cap on mutating endpoints (0 = disabled).",
    )

    # -- Telemetry adapters (real feeds) -----------------------------------
    replay_path: str | None = Field(
        default=None, description="CSV/JSONL recording path for file-replay sessions."
    )
    replay_speed: float = Field(
        default=1.0, ge=0.0, description="Replay speed multiplier (0 = as fast as can)."
    )
    replay_loop: bool = Field(
        default=False, description="Loop a file-replay recording when it ends."
    )
    websocket_url: str | None = Field(
        default=None, description="Upstream ws(s):// telemetry broker URL."
    )
    udp_host: str = Field(
        default="127.0.0.1", description="Bind address for the UDP telemetry source."
    )
    udp_port: int = Field(
        default=20777, gt=0, le=65535, description="Bind port for the UDP source."
    )

    # -- Telemetry ingestion ------------------------------------------------
    queue_maxsize: int = Field(
        default=2048,
        gt=0,
        description="Backpressure bound for the async telemetry queue.",
    )
    use_simulated_source: bool = Field(
        default=True,
        description="Start the built-in simulated telemetry generator at boot.",
    )
    sim_tick_seconds: float = Field(
        default=0.5,
        gt=0,
        description="Interval between simulated telemetry frames.",
    )
    sim_total_laps: int = Field(
        default=58, gt=0, description="Race distance for the simulated session."
    )

    # -- Recommendation engine ---------------------------------------------
    use_llm: bool = Field(
        default=True,
        description="Phrase recommendations with the core LLM. Falls back to "
        "deterministic templates when the LLM is unavailable.",
    )
    llm_model: str | None = Field(
        default=None, description="Optional model override for NL phrasing."
    )
    min_confidence: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        description="Suppress recommendations below this blended confidence.",
    )

    # -- Simulation (MCTS) --------------------------------------------------
    sim_max_iterations: int = Field(
        default=120, gt=0, description="MCTS iteration budget per decision."
    )
    sim_horizon_laps: int = Field(
        default=12, gt=0, description="Look-ahead horizon (laps) for race scenarios."
    )

    # -- Historical recall --------------------------------------------------
    semantic_enabled: bool = Field(
        default=False,
        description="Enable Qdrant/LTM-backed semantic recall of past stints.",
    )
    history_top_k: int = Field(
        default=5, ge=1, description="How many historical stints to recall."
    )

    # -- Realtime -----------------------------------------------------------
    sse_heartbeat_seconds: float = Field(
        default=15.0, gt=0, description="Idle keepalive interval for the SSE stream."
    )
    recommendation_buffer: int = Field(
        default=200, ge=1, description="Ring-buffer size for recent recommendations."
    )

    @classmethod
    def from_plugin_config(cls, config: dict[str, Any] | None) -> "PitwallConfig":
        """Build from the plugin config block, with env overrides applied."""
        return cls(**(config or {}))


__all__ = ["PitwallConfig"]
