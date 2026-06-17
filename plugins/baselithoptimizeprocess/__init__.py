"""BaselithOptimizeProcess (BOP) plugin.

Map complex business processes as execution graphs, monitor user-defined
efficiency KPIs in real time over Server-Sent Events, and generate advisory,
human-in-the-loop optimization proposals grounded in detected bottlenecks.

Conforms to the Sacred Core rule: every line of domain logic lives in this
package; ``core/`` provides only the plugin machinery this module plugs into.
"""

from __future__ import annotations

from .agent import BopOptimizerAgent
from .automation_models import (
    ActionType,
    AutomationRule,
    RuleAction,
    RuleFiring,
    RuleTrigger,
    TriggerType,
)
from .event_models import (
    ConformanceReport,
    Event,
    MiningResult,
    Variant,
)
from .models import (
    Bottleneck,
    KpiDefinition,
    KpiDirection,
    KpiSnapshot,
    MetricSample,
    NodeKind,
    OptimizationProposal,
    ProcessEdge,
    ProcessGraph,
    ProcessNode,
    ProposalStatus,
    Severity,
)
from .plugin import BopPlugin
from .resources import Resource
from .service import BopService, ProcessValidationError

__all__ = [
    "BopPlugin",
    "BopService",
    "BopOptimizerAgent",
    "ProcessValidationError",
    "ProcessGraph",
    "ProcessNode",
    "ProcessEdge",
    "Resource",
    "KpiDefinition",
    "KpiDirection",
    "KpiSnapshot",
    "MetricSample",
    "NodeKind",
    "Bottleneck",
    "Severity",
    "OptimizationProposal",
    "ProposalStatus",
    "Event",
    "MiningResult",
    "Variant",
    "ConformanceReport",
    "AutomationRule",
    "RuleTrigger",
    "RuleAction",
    "RuleFiring",
    "TriggerType",
    "ActionType",
]
