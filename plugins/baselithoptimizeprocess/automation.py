"""Automation-rule evaluation — the pure core of BOP's intelligent automation.

Given the latest snapshots/bottlenecks for a process and its enabled rules, this
decides which rules fire and why. It performs no side effects: the service layer
turns each :class:`RuleFiring` into an action (alert event, webhook POST,
advisory optimization), keeping I/O out of the deterministic decision logic.
"""

from __future__ import annotations

from .anomaly import BreachForecast
from .automation_models import (
    AutomationRule,
    RuleFiring,
    TriggerType,
)
from .models import Bottleneck, KpiSnapshot, Severity

_SEVERITY_RANK = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def _min_rank(value: str) -> int:
    """Rank for a configured minimum severity string (defaults to HIGH)."""
    try:
        return _SEVERITY_RANK[Severity(value)]
    except ValueError:
        return _SEVERITY_RANK[Severity.HIGH]


def evaluate_rules(
    rules: list[AutomationRule],
    snapshots: list[KpiSnapshot],
    bottlenecks: list[Bottleneck],
    forecasts: list[BreachForecast] | None = None,
) -> list[RuleFiring]:
    """Return the firings for all enabled rules whose trigger currently matches.

    Args:
        rules: Candidate rules (any process; only enabled ones are evaluated).
        snapshots: Latest KPI snapshots for the process under evaluation.
        bottlenecks: Latest bottlenecks for the process under evaluation.
        forecasts: Optional breach forecasts (for ``PREDICTED_BREACH`` triggers).

    Returns:
        One :class:`RuleFiring` per matching rule.
    """
    snap_by_kpi = {s.kpi_id: s for s in snapshots}
    forecast_by_kpi = {f.kpi_id: f for f in (forecasts or [])}
    firings: list[RuleFiring] = []

    for rule in rules:
        if not rule.enabled:
            continue
        detail = _match(rule, snap_by_kpi, bottlenecks, forecast_by_kpi)
        if detail is None:
            continue
        firings.append(
            RuleFiring(
                rule_id=rule.id,
                process_id=rule.process_id,
                rule_name=rule.name,
                action_type=rule.action.type,
                detail=detail,
            )
        )
    return firings


def _match(
    rule: AutomationRule,
    snap_by_kpi: dict[str, KpiSnapshot],
    bottlenecks: list[Bottleneck],
    forecast_by_kpi: dict[str, BreachForecast],
) -> str | None:
    """Return a human-readable reason if the rule's trigger matches, else None."""
    trigger = rule.trigger
    if trigger.type is TriggerType.KPI_BREACH:
        snap = snap_by_kpi.get(trigger.kpi_id)
        if snap is not None and snap.breaching:
            return (
                f"KPI '{trigger.kpi_id}' breaching at {snap.value:.2f} "
                f"(target {snap.target})"
            )
        return None

    if trigger.type is TriggerType.PREDICTED_BREACH:
        forecast = forecast_by_kpi.get(trigger.kpi_id)
        if forecast is not None and forecast.will_breach:
            eta = forecast.samples_to_breach
            when = f"in ~{eta} samples" if eta else "imminently"
            return (
                f"KPI '{trigger.kpi_id}' is forecast to breach target "
                f"{forecast.target} {when} (projected {forecast.projected_value:.2f})"
            )
        return None

    if trigger.type is TriggerType.BOTTLENECK_SEVERITY:
        threshold = _min_rank(trigger.min_severity)
        worst = [b for b in bottlenecks if _SEVERITY_RANK[b.severity] >= threshold]
        if worst:
            top = max(worst, key=lambda b: _SEVERITY_RANK[b.severity])
            return (
                f"{len(worst)} bottleneck(s) at/above {trigger.min_severity}; "
                f"worst: {top.severity.value} on '{top.node_id or top.kpi_id}'"
            )
        return None

    return None


__all__ = ["evaluate_rules"]
