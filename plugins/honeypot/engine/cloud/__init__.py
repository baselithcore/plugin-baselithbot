"""Cloud Management Honeypot Module.

High-interaction honeypot simulating AWS-like cloud management APIs
for advanced threat detection, APT identification, and zero-day pattern capture.

Components:
- CloudManagementHandler: Main HTTP handler for cloud API simulation
- CloudPatternDetector: Cloud-specific attack pattern detection
- CloudResponseGenerator: Realistic AWS-like response generation
- HeuristicEngine: Zero-day pattern detection through behavioral analysis
- SessionStateMachine: Multi-state session tracking

Usage:
    from plugins.honeypot.engine.cloud import CloudManagementHandler
    from plugins.honeypot.config import HoneypotConfig

    config = HoneypotConfig()
    handler = CloudManagementHandler(config)
    await handler.start(port=8443)
"""

# Main handler (modularized)
from .handler import CloudManagementHandler

# Heuristics (modularized)
from .heuristics import (
    AbnormalDataVolumeHeuristic,
    BurstRequestHeuristic,
    EncodedPayloadHeuristic,
    HighErrorRateHeuristic,
    HeuristicEngine,
    HeuristicRule,
    MachineTimingHeuristic,
    PrivilegeEscalationSequenceHeuristic,
    RapidStateTransitionHeuristic,
    SuspiciousResourceNameHeuristic,
    UnusualServiceCombinationHeuristic,
    get_heuristic_engine,
)

# Models (unchanged)
from .models import (
    APICallSeverity,
    CloudAPICall,
    CloudAttackCategory,
    CloudCredential,
    CloudHoneypotStats,
    CloudProvider,
    CloudSession,
    HeuristicAlert,
    RequestTiming,
    SessionState,
    TCPFingerprint,
    TLSFingerprint,
)

# Pattern detection (unchanged)
from .patterns import CloudPatternDetector, get_cloud_pattern_detector

# Protocols (for DI)
from .protocols import (
    CloudPatternDetectorProtocol,
    GeoIPServiceProtocol,
    HeuristicEngineProtocol,
    TLSFingerprintingServiceProtocol,
)

# Response generation (modularized)
from .responses import CloudResponseGenerator

# Services
from .services import (
    GeoIPService,
    TLSFingerprintingService,
    get_fingerprinting_service,
    get_geoip_service,
)

# State machine (unchanged)
from .state_machine import SessionStateMachine

__all__ = [
    # Main handler
    "CloudManagementHandler",
    # Pattern detection
    "CloudPatternDetector",
    "get_cloud_pattern_detector",
    # Response generation
    "CloudResponseGenerator",
    # Heuristics
    "HeuristicEngine",
    "HeuristicRule",
    "get_heuristic_engine",
    # Heuristic rules (for custom extensions)
    "MachineTimingHeuristic",
    "BurstRequestHeuristic",
    "PrivilegeEscalationSequenceHeuristic",
    "UnusualServiceCombinationHeuristic",
    "EncodedPayloadHeuristic",
    "SuspiciousResourceNameHeuristic",
    "RapidStateTransitionHeuristic",
    "HighErrorRateHeuristic",
    "AbnormalDataVolumeHeuristic",
    # State machine
    "SessionStateMachine",
    # Services
    "GeoIPService",
    "get_geoip_service",
    "TLSFingerprintingService",
    "get_fingerprinting_service",
    # Protocols (for DI)
    "CloudPatternDetectorProtocol",
    "HeuristicEngineProtocol",
    "GeoIPServiceProtocol",
    "TLSFingerprintingServiceProtocol",
    # Models
    "CloudProvider",
    "SessionState",
    "CloudAttackCategory",
    "APICallSeverity",
    "CloudCredential",
    "TCPFingerprint",
    "TLSFingerprint",
    "RequestTiming",
    "CloudAPICall",
    "CloudSession",
    "HeuristicAlert",
    "CloudHoneypotStats",
]
