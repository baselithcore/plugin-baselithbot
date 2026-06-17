"""Project the framework's per-plugin metrics into ``MetricView`` chips.

Every loaded plugin records lifecycle/timing/error metrics in
``core.plugins.metrics`` — load counts, reload counts, failures, average load
time, and time-in-state. The control plane surfaces those as a zero-config
"core telemetry" panel so a plugin shows live operational signal in the detail
view **without** declaring a custom widget. A plugin with no recorded activity
yields an empty list and the UI falls back to its empty state.

This keeps the universal panel decoupled from any plugin-specific endpoint: the
data already exists in-process, so there is nothing to fetch and no SSRF surface.
"""

from __future__ import annotations

from typing import Any

from ..api_models import MetricView


def _num(value: Any) -> float | None:
    """Coerce to a finite float, or ``None`` when not numeric."""
    if isinstance(value, bool):  # bool is an int subclass — exclude explicitly
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _uptime_ms(data: dict[str, Any]) -> float | None:
    """Return active-state duration (ms) only while the plugin is active."""
    current = data.get("current_state") or {}
    if current.get("state") == "active":
        return _num(current.get("duration_ms"))
    return None


def plugin_metric_views(plugin: str) -> list[MetricView]:
    """Build core-telemetry chips for ``plugin`` (empty if nothing recorded)."""
    try:
        from core.plugins.metrics import get_metrics_collector

        data = get_metrics_collector().get_plugin_metrics(plugin)
    except Exception:  # noqa: BLE001 — telemetry is optional, never block status
        data = None
    if not isinstance(data, dict):
        return []

    counts = data.get("lifecycle_counts") or {}
    load_timing = (data.get("timing") or {}).get("load") or {}
    errors = data.get("errors") or {}
    views: list[MetricView] = []

    uptime = _uptime_ms(data)
    if uptime is not None:
        views.append(
            MetricView(label="Uptime", value=uptime, format="duration", tone="success")
        )

    avg_load = _num(load_timing.get("avg_ms"))
    if avg_load and avg_load > 0:
        views.append(
            MetricView(label="Avg load", value=round(avg_load, 1), format="duration")
        )

    views.append(
        MetricView(
            label="Loads", value=_num(counts.get("load")) or 0.0, format="number"
        )
    )
    reloads = _num(counts.get("reload")) or 0.0
    if reloads:
        views.append(MetricView(label="Reloads", value=reloads, format="number"))

    failures = _num(counts.get("failure")) or 0.0
    if failures:
        views.append(
            MetricView(label="Failures", value=failures, format="number", tone="danger")
        )

    total_errors = _num(errors.get("total_errors")) or 0.0
    if total_errors:
        views.append(
            MetricView(
                label="Errors", value=total_errors, format="number", tone="warning"
            )
        )

    return views


__all__ = ["plugin_metric_views"]
