"""Static configuration for the dbview Node child process.

Composed once at plugin ``initialize()`` time from the plugin directory, the
host environment (``DBVIEW_*`` knobs) and optional plugin-YAML overrides.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)


# Env prefixes forwarded verbatim from the host process to the Node child.
# Everything else is withheld so the child never sees unrelated host secrets.
PASSTHROUGH_ENV_PREFIXES: tuple[str, ...] = (
    "DBVIEW_",
    "OLLAMA_",
    "OPENAI_",
    "ANTHROPIC_",
    "OTEL_",
    "LOG_",
    "NODE_",
    "APP_VERSION",
)


@dataclass(slots=True)
class SupervisorConfig:
    """Static configuration captured at plugin initialize() time."""

    plugin_dir: Path
    """Filesystem root of the plugin (contains ``dbview/``)."""

    dbview_root: Path
    """Filesystem root of the embedded dbview monorepo."""

    mode: str = "prod"
    """``prod`` = ``node dist/main.js``; ``dev`` = ``pnpm dev`` (turbo)."""

    host: str = "127.0.0.1"
    """Bind address. Loopback by default — the proxy fronts external traffic."""

    port: int | None = None
    """Explicit port. ``None`` triggers ephemeral allocation."""

    startup_timeout_s: float = 90.0
    """Max wait for the first successful ``/api/health`` probe."""

    health_probe_interval_s: float = 0.5
    """Delay between probes during the startup wait loop."""

    health_path: str = "/api/health"
    """Endpoint hit by both the startup gate and runtime liveness checks."""

    shutdown_grace_s: float = 10.0
    """Seconds between SIGTERM and SIGKILL."""

    restart_backoff_initial_s: float = 1.0
    restart_backoff_max_s: float = 30.0
    restart_max_attempts: int = 0
    """0 = restart forever. >0 = stop after that many consecutive failures."""

    extra_env: Mapping[str, str] = field(default_factory=dict)
    """Plugin-controlled overrides merged on top of the passthrough env."""


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("[dbview] invalid %s=%r, falling back to %d", name, raw, default)
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("[dbview] invalid %s=%r, falling back to %s", name, raw, default)
        return default


def build_supervisor_config(
    plugin_dir: Path,
    *,
    extra_env: Mapping[str, str] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> SupervisorConfig:
    """Compose a :class:`SupervisorConfig` from plugin dir + env + overrides.

    Operators tune the supervisor primarily via environment variables; the
    plugin-level YAML config (passed to ``initialize``) is the secondary
    lever for ``mode`` / ``host`` / ``port``.
    """
    overrides = overrides or {}
    # Resolve to absolute so the supervisor never depends on the host cwd at
    # spawn time — a relative root would silently concat with a changed cwd.
    plugin_dir = Path(plugin_dir).resolve()
    dbview_root = plugin_dir / "dbview"

    mode = overrides.get("mode") or os.environ.get("DBVIEW_PLUGIN_MODE") or "prod"
    if mode not in {"prod", "dev"}:
        logger.warning("[dbview] invalid mode %r, falling back to 'prod'", mode)
        mode = "prod"

    host = overrides.get("host") or os.environ.get("DBVIEW_INTERNAL_HOST") or "127.0.0.1"

    port_override = overrides.get("port")
    if port_override is None and "DBVIEW_INTERNAL_PORT" in os.environ:
        try:
            port_override = int(os.environ["DBVIEW_INTERNAL_PORT"])
        except ValueError:
            logger.warning("[dbview] invalid DBVIEW_INTERNAL_PORT, allocating dynamically")
            port_override = None

    return SupervisorConfig(
        plugin_dir=plugin_dir,
        dbview_root=dbview_root,
        mode=str(mode),
        host=str(host),
        port=port_override,
        startup_timeout_s=_env_float("DBVIEW_STARTUP_TIMEOUT_S", 90.0),
        health_probe_interval_s=_env_float("DBVIEW_HEALTH_INTERVAL_S", 0.5),
        shutdown_grace_s=_env_float("DBVIEW_SHUTDOWN_GRACE_S", 10.0),
        restart_max_attempts=_env_int("DBVIEW_RESTART_MAX_ATTEMPTS", 0),
        extra_env=dict(extra_env or {}),
    )


__all__ = [
    "PASSTHROUGH_ENV_PREFIXES",
    "SupervisorConfig",
    "build_supervisor_config",
]
