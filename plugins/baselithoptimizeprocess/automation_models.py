"""Automation-rule models — BOP's Appian/Pega-style intelligent automation.

A rule binds a *condition* over live process signals (a breaching KPI, a
bottleneck of some severity) to an *action*. Actions are deliberately
HITL-safe: the strongest one generates advisory optimization proposals — it
never mutates a live process — so automation accelerates response without
removing the human from the loop.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Timezone-aware UTC now (testable seam)."""
    return datetime.now(timezone.utc)


class TriggerType(str, Enum):
    """What kind of signal a rule watches."""

    KPI_BREACH = "kpi_breach"
    BOTTLENECK_SEVERITY = "bottleneck_severity"
    PREDICTED_BREACH = "predicted_breach"


class ActionType(str, Enum):
    """What a rule does when it fires (all non-destructive)."""

    ALERT = "alert"
    RECOMMEND_OPTIMIZATION = "recommend_optimization"
    WEBHOOK = "webhook"


class RuleTrigger(BaseModel):
    """Condition a rule evaluates against the latest snapshots/bottlenecks."""

    type: TriggerType = Field(default=TriggerType.KPI_BREACH)
    kpi_id: str = Field(default="", description="KPI to watch (KPI_BREACH triggers).")
    min_severity: str = Field(
        default="high",
        description="Minimum bottleneck severity for BOTTLENECK_SEVERITY triggers.",
    )


class RuleAction(BaseModel):
    """What happens when the trigger matches."""

    type: ActionType = Field(default=ActionType.ALERT)
    message: str = Field(default="", description="Human-readable alert text.")
    webhook_url: str = Field(default="", description="Target for WEBHOOK actions.")


class AutomationRule(BaseModel):
    """A persisted condition→action rule scoped to one process."""

    id: str = Field(..., description="Rule identifier.")
    process_id: str = Field(..., description="Process the rule governs.")
    name: str = Field(..., description="Human-readable rule name.")
    trigger: RuleTrigger = Field(default_factory=RuleTrigger)
    action: RuleAction = Field(default_factory=RuleAction)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)


class RuleFiring(BaseModel):
    """A record that a rule's condition matched and its action ran."""

    rule_id: str
    process_id: str
    rule_name: str
    action_type: ActionType
    detail: str = Field(default="", description="Why it fired / what it did.")
    fired_at: datetime = Field(default_factory=_utcnow)


__all__ = [
    "TriggerType",
    "ActionType",
    "RuleTrigger",
    "RuleAction",
    "AutomationRule",
    "RuleFiring",
]
