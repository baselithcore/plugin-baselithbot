"""Captor Module for Honeypot Plugin.

Implements the HoneyDOC Captor architecture with core components:
- CaptorManager: Main integration point for all captor components
- DataCaptureManager: Unified data capture layer
- DataControlManager: Flow control and containment
- DataAnalysisManager: Analysis orchestration

Additional components:
- TrafficClassifier: Rule-based traffic classification
- FlowController: Flow control countermeasures
- DynamicDeployer: Runtime honeypot provisioning
- StealthManager: Stealth-aware operations

Reference: HoneyDOC Paper Section III-B
"""

from .classification import ClassificationResult, TrafficClassifier
from .countermeasures import DynamicDeployer, FlowController
from .data_analysis import AnalysisResult, AnalysisType, DataAnalysisManager
from .data_capture import CaptureStats, DataCaptureManager
from .data_control import ControlRule, DataControlManager, FlowAction
from .manager import CaptorManager
from .stealth import Fingerprint, MigrationContext, StealthManager

__all__ = [
    # Main integration point
    "CaptorManager",
    # Core managers
    "DataCaptureManager",
    "DataControlManager",
    "DataAnalysisManager",
    # Classification
    "TrafficClassifier",
    "ClassificationResult",
    # Flow control
    "FlowAction",
    "ControlRule",
    # Countermeasures
    "FlowController",
    "DynamicDeployer",
    # Stealth
    "StealthManager",
    "Fingerprint",
    "MigrationContext",
    # Stats
    "CaptureStats",
    # Analysis
    "AnalysisResult",
    "AnalysisType",
]
