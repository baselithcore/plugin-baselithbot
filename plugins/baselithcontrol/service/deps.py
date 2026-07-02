"""Request-time construction of control-plane services from ``app.state``.

The plugin registry is owned by the framework and published on
``app.state.plugin_registry`` during startup. These helpers read it lazily per
request so the dashboard always reflects the live registry, never a stale
snapshot captured at import time.
"""

from __future__ import annotations

from typing import Any

from core.orchestration.autonomy import AutonomyLevel, AutonomyPolicy

from ..config import ControlConfig, GateLevel, get_runtime_config
from .aggregator import ControlAggregator
from .audit import get_audit_sink
from .control import ControlService

_GATE_TO_LEVEL = {
    GateLevel.OPEN: AutonomyLevel.FULLY_AUTONOMOUS,
    GateLevel.SEMI: AutonomyLevel.SEMI_AUTONOMOUS,
    GateLevel.STRICT: AutonomyLevel.SUPERVISED,
}


def get_config(app: Any) -> ControlConfig:
    """Return the runtime plugin config.

    An instance stashed on ``app.state.baselithcontrol_config`` wins (explicit
    override, used by tests); otherwise the config published at plugin
    ``initialize`` — the plugins.yaml block with env overrides — is returned.
    """
    cfg = getattr(app.state, "baselithcontrol_config", None)
    return cfg if isinstance(cfg, ControlConfig) else get_runtime_config()


def get_registry(app: Any) -> Any:
    """Return the framework plugin registry, or ``None`` if not yet started."""
    return getattr(app.state, "plugin_registry", None)


def get_aggregator(app: Any) -> ControlAggregator:
    """Build a read-only aggregator bound to the live registry."""
    return ControlAggregator(get_registry(app))


def build_policy(config: ControlConfig) -> AutonomyPolicy:
    """Map the configured gate level onto an autonomy policy."""
    level = _GATE_TO_LEVEL.get(config.gate_level, AutonomyLevel.FULLY_AUTONOMOUS)
    return AutonomyPolicy(level=level)


def get_control_service(app: Any) -> ControlService:
    """Build the gated control service for the current request."""
    config = get_config(app)
    human = getattr(app.state, "baselithcontrol_human_intervention", None)
    return ControlService(
        get_registry(app),
        policy=build_policy(config),
        audit=get_audit_sink(config.audit_max_events),
        human_intervention=human,
        approval_timeout=config.approval_timeout_seconds,
    )


__all__ = [
    "get_config",
    "get_registry",
    "get_aggregator",
    "get_control_service",
    "build_policy",
]
