"""Heuristic Detection Module.

Zero-day pattern detection through behavioral analysis, timing anomalies,
and sequence analysis.
"""

from .base import HeuristicRule
from .behavior import (
    AbnormalDataVolumeHeuristic,
    HighErrorRateHeuristic,
    RapidStateTransitionHeuristic,
)
from .engine import HeuristicEngine, get_heuristic_engine
from .payload import EncodedPayloadHeuristic, SuspiciousResourceNameHeuristic
from .sequence import (
    PrivilegeEscalationSequenceHeuristic,
    UnusualServiceCombinationHeuristic,
)
from .timing import BurstRequestHeuristic, MachineTimingHeuristic

__all__ = [
    # Base
    "HeuristicRule",
    # Engine
    "HeuristicEngine",
    "get_heuristic_engine",
    # Timing
    "MachineTimingHeuristic",
    "BurstRequestHeuristic",
    # Sequence
    "PrivilegeEscalationSequenceHeuristic",
    "UnusualServiceCombinationHeuristic",
    # Payload
    "EncodedPayloadHeuristic",
    "SuspiciousResourceNameHeuristic",
    # Behavior
    "RapidStateTransitionHeuristic",
    "HighErrorRateHeuristic",
    "AbnormalDataVolumeHeuristic",
]
