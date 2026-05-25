"""Discovery Package - Botnet Detection and Pattern Analysis.

Provides graph-based analysis for detecting botnets, C&C servers,
and coordinated attack patterns from honeypot data.
"""

from .models import (
    BotnetCluster,
    HubNode,
    NetworkAnomaly,
    DiscoveryResult,
    DiscoveryGraphData,
)
from .service import DiscoveryService
from .behavioral_analyzer import BehavioralAnalyzer
from .statistical_analyzer import StatisticalAnalyzer
from .cc_detector import CCDetector
from .botnet_profiler import BotnetProfiler
from .ml_analyzer import MLAnalyzer
from .feature_extractor import FeatureExtractor
from .zeroday_detector import ZeroDayDetector
from .threat_intel import ThreatIntelGenerator
from .exploit_analyzer import ExploitAnalyzer
from .honeypot_suggester import HoneypotSuggestionEngine, HoneypotSuggestion

__all__ = [
    "BotnetCluster",
    "HubNode",
    "NetworkAnomaly",
    "DiscoveryResult",
    "DiscoveryGraphData",
    "DiscoveryService",
    "BehavioralAnalyzer",
    "StatisticalAnalyzer",
    "CCDetector",
    "BotnetProfiler",
    "MLAnalyzer",
    "FeatureExtractor",
    "ZeroDayDetector",
    "ThreatIntelGenerator",
    "ExploitAnalyzer",
    "HoneypotSuggestionEngine",
    "HoneypotSuggestion",
]
