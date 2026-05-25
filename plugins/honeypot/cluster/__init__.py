"""Cluster Persistence Module for Multi-Node State Sync.

Provides distributed state management for honeypot clusters,
enabling coherent emulation during lateral movement simulation.

Components:
    - ClusterStateManager: Redis-backed state synchronization
    - LateralMovementCoherence: Cross-node session correlation
    - SharedFilesystemState: VFS mutation replication

Usage:
    from plugins.honeypot.cluster import (
        ClusterStateManager,
        LateralMovementCoherence,
    )

    # Initialize cluster manager
    manager = ClusterStateManager(redis_url="redis://localhost:6379/0")
    await manager.connect()

    # Sync session state
    await manager.sync_session(session)
"""

from .state_manager import ClusterStateManager
from .lateral import LateralMovementCoherence
from .vfs_sync import SharedFilesystemState

__all__ = [
    "ClusterStateManager",
    "LateralMovementCoherence",
    "SharedFilesystemState",
]
