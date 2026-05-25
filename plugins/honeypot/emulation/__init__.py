"""Advanced Deception System - Emulation Module.

This module provides sophisticated emulation capabilities for the honeypot,
including stateful session management, fingerprint coherence, and latency modeling.

Components:
    - StatefulEmulator: Maintains coherent session state across commands
    - FingerprintEngine: Generates consistent OS-accurate fingerprints
    - LatencyModeler: Simulates realistic response timing
    - SessionState: Tracks per-session context and mutations

Usage:
    from plugins.honeypot.emulation import (
        StatefulEmulator,
        FingerprintEngine,
        LatencyModeler,
        FingerprintProfile,
        SessionState,
    )

    # Create emulator with fingerprint profile
    profile = FingerprintProfile.load("linux_ubuntu")
    emulator = StatefulEmulator(session_id="abc123", fingerprint_profile=profile)

    # Process command with full state tracking
    response = await emulator.process_command("ls -la")
"""

from .models import (
    FingerprintProfile,
    SessionState,
    FSMutation,
    EmulatedResponse,
    OperationType,
    TTP,
    TTPPrediction,
)
from .latency import LatencyModeler
from .fingerprint import FingerprintEngine
from .stateful import StatefulEmulator

__all__ = [
    # Models
    "FingerprintProfile",
    "SessionState",
    "FSMutation",
    "EmulatedResponse",
    "OperationType",
    "TTP",
    "TTPPrediction",
    # Engines
    "LatencyModeler",
    "FingerprintEngine",
    "StatefulEmulator",
]
