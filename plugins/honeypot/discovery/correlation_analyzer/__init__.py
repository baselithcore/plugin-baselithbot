"""Correlation Analyzer Module.

Detects attacker-to-attacker correlations for botnet and coordinated attack detection.
Uses cybersecurity best practices including:
- MITRE ATT&CK TTP correlation
- IOC (Indicators of Compromise) matching
- Temporal analysis windows
"""

from .core import CorrelationAnalyzer
from .models import (
    AttackerCorrelation,
    CorrelationType,
    CorrelationConfig,
)

__all__ = [
    "CorrelationAnalyzer",
    "AttackerCorrelation",
    "CorrelationType",
    "CorrelationConfig",
]
