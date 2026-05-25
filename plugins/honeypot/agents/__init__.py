"""Honeypot Agents Package.

Specialized agents for the honeypot plugin:
- PatternAnalyzer: AI attack pattern analysis
- CVECorrelator: CVE correlation with honeypot attacks
- LLMResponder: LLM-powered response generation
"""

from .responder import LLMResponder
from .pattern_analyzer import PatternAnalyzer
from .correlator import HoneypotCVECorrelator
from .pentester import ThreatInformedPentester
from .pentest_models import ThreatProfile, PentestPlaybook, PentestResult

__all__ = [
    "LLMResponder",
    "PatternAnalyzer",
    "HoneypotCVECorrelator",
    "ThreatInformedPentester",
    "ThreatProfile",
    "PentestPlaybook",
    "PentestResult",
]
