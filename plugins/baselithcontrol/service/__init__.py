"""Service layer for the BaselithControl plugin.

* :mod:`aggregator` — read-only projection of the registry into wire views.
* :mod:`bridge`     — EventBus → per-client SSE queue fan-out.
* :mod:`control`    — gated lifecycle operations (RBAC + autonomy + audit).
* :mod:`audit`      — append-only audit sink (in-memory default, swappable).
* :mod:`deps`       — request-time construction from ``app.state``.
"""

from __future__ import annotations

from .aggregator import ControlAggregator
from .audit import AuditSink, InMemoryAuditSink, get_audit_sink
from .bridge import CONTROL_ACTION, control_sse, emit_action
from .control import ControlService
from .deps import (
    get_aggregator,
    get_config,
    get_control_service,
    get_registry,
)
from .config_store import read_all, read_enabled, set_enabled
from .plugin_meter import PluginMeter, PluginMeterMiddleware, get_plugin_meter
from .probe import StatusProber
from .resources import ResourceSampler, get_resource_sampler
from .widgets import display_meta, resolve_widget, resolve_widgets

__all__ = [
    "ControlAggregator",
    "ControlService",
    "StatusProber",
    "AuditSink",
    "InMemoryAuditSink",
    "get_audit_sink",
    "control_sse",
    "emit_action",
    "CONTROL_ACTION",
    "get_aggregator",
    "get_config",
    "get_control_service",
    "get_registry",
    "display_meta",
    "resolve_widget",
    "resolve_widgets",
    "read_all",
    "read_enabled",
    "set_enabled",
    "PluginMeter",
    "PluginMeterMiddleware",
    "get_plugin_meter",
    "ResourceSampler",
    "get_resource_sampler",
]
