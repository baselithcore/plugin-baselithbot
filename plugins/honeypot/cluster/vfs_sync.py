"""Shared Filesystem State for Cross-Node VFS Synchronization.

Synchronizes virtual filesystem mutations across cluster nodes
to maintain consistent environment when attackers access
multiple honeypots.

Key capabilities:
- Real-time VFS mutation replication
- Mutation replay for session reconstruction
- Conflict resolution for concurrent mutations
"""

import asyncio
from core.observability.logging import get_logger
from datetime import datetime
from typing import Dict, List, Optional, Set

from ..emulation.models import FSMutation
from .state_manager import ClusterStateManager

logger = get_logger(__name__)


class SharedFilesystemState:
    """Synchronize VFS state across cluster nodes.

    When an attacker modifies the filesystem in one honeypot,
    the changes are replicated to ensure consistent state
    if they access the same session from another node.

    Example:
        >>> vfs_sync = SharedFilesystemState(cluster_manager)
        >>> await vfs_sync.publish_mutation(session_id, mutation)
        >>>
        >>> # On another node
        >>> mutations = await vfs_sync.get_pending_mutations(session_id)
        >>> for m in mutations:
        ...     vfs.apply_mutation(m)
    """

    def __init__(
        self,
        cluster_manager: ClusterStateManager,
        batch_interval_ms: int = 100,
        max_batch_size: int = 50,
    ):
        """Initialize shared filesystem state.

        Args:
            cluster_manager: Cluster state manager
            batch_interval_ms: Interval for batching mutations
            max_batch_size: Maximum mutations per batch
        """
        self.cluster = cluster_manager
        self.batch_interval_ms = batch_interval_ms
        self.max_batch_size = max_batch_size

        # Pending mutations to sync (batched)
        self._pending: Dict[str, List[FSMutation]] = {}

        # Applied mutations (to avoid duplicates)
        self._applied: Dict[str, Set[str]] = {}

        # Sync task
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start background mutation sync."""
        if self._running:
            return

        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop())

        logger.info("SharedFilesystemState sync started")

    async def stop(self) -> None:
        """Stop background mutation sync."""
        self._running = False

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Flush any remaining mutations
        await self._flush_all()

        logger.info("SharedFilesystemState sync stopped")

    async def _sync_loop(self) -> None:
        """Background loop for batched mutation sync."""
        try:
            while self._running:
                await asyncio.sleep(self.batch_interval_ms / 1000)
                await self._flush_all()
        except asyncio.CancelledError:
            pass

    async def _flush_all(self) -> None:
        """Flush all pending mutations to cluster."""
        for session_id, mutations in list(self._pending.items()):
            if mutations:
                await self._flush_session(session_id)

    async def _flush_session(self, session_id: str) -> None:
        """Flush pending mutations for a session."""
        mutations = self._pending.get(session_id, [])
        if not mutations:
            return

        for mutation in mutations:
            await self.cluster.sync_mutation(session_id, mutation)

        self._pending[session_id] = []

    async def publish_mutation(
        self,
        session_id: str,
        mutation: FSMutation,
    ) -> None:
        """Publish a filesystem mutation to cluster.

        Args:
            session_id: Session that generated mutation
            mutation: Filesystem mutation
        """
        if session_id not in self._pending:
            self._pending[session_id] = []

        self._pending[session_id].append(mutation)

        # Track as applied locally
        if session_id not in self._applied:
            self._applied[session_id] = set()
        self._applied[session_id].add(mutation.mutation_id)

        # Flush immediately if batch size reached
        if len(self._pending[session_id]) >= self.max_batch_size:
            await self._flush_session(session_id)

    async def get_pending_mutations(
        self,
        session_id: str,
        since: Optional[datetime] = None,
    ) -> List[FSMutation]:
        """Get mutations from cluster for a session.

        Filters out mutations already applied locally.

        Args:
            session_id: Session identifier
            since: Only get mutations after this time

        Returns:
            List of mutations to apply
        """
        all_mutations = await self.cluster.get_mutations(session_id, since)

        # Filter out already applied
        applied_ids = self._applied.get(session_id, set())

        return [m for m in all_mutations if m.mutation_id not in applied_ids]

    async def apply_remote_mutations(
        self,
        session_id: str,
        vfs: any,  # VirtualFilesystem
    ) -> int:
        """Apply remote mutations to local VFS.

        Args:
            session_id: Session identifier
            vfs: VirtualFilesystem instance

        Returns:
            Number of mutations applied
        """
        mutations = await self.get_pending_mutations(session_id)
        applied = 0

        for mutation in mutations:
            try:
                self._apply_mutation_to_vfs(vfs, mutation)

                # Mark as applied
                if session_id not in self._applied:
                    self._applied[session_id] = set()
                self._applied[session_id].add(mutation.mutation_id)

                applied += 1

            except Exception as e:
                logger.warning(f"Failed to apply mutation: {e}")

        return applied

    def _apply_mutation_to_vfs(self, vfs: any, mutation: FSMutation) -> None:
        """Apply a single mutation to VFS.

        Args:
            vfs: VirtualFilesystem instance
            mutation: Mutation to apply
        """
        if mutation.mutation_type == "create_file":
            vfs.touch(mutation.path)
            if mutation.content:
                vfs.write_file(mutation.path, mutation.content)

        elif mutation.mutation_type == "create_dir":
            vfs.mkdir(mutation.path)

        elif mutation.mutation_type == "modify_file":
            if mutation.content:
                vfs.write_file(mutation.path, mutation.content)

        elif mutation.mutation_type == "delete_file":
            vfs.rm(mutation.path, force=True)

        elif mutation.mutation_type == "delete_dir":
            vfs.rm(mutation.path, recursive=True, force=True)

        elif mutation.mutation_type == "chmod":
            if mutation.permissions:
                vfs.chmod(mutation.path, mutation.permissions)

        elif mutation.mutation_type == "chown":
            if mutation.owner:
                vfs.chown(mutation.path, mutation.owner)

    async def replay_mutations(
        self,
        session_id: str,
        vfs: any,
    ) -> int:
        """Replay all mutations for a session.

        Used when reconstructing VFS state for lateral movement.

        Args:
            session_id: Session to replay
            vfs: Target VirtualFilesystem

        Returns:
            Number of mutations replayed
        """
        all_mutations = await self.cluster.get_mutations(session_id)

        # Sort by timestamp
        all_mutations.sort(key=lambda m: m.timestamp)

        replayed = 0
        for mutation in all_mutations:
            try:
                self._apply_mutation_to_vfs(vfs, mutation)
                replayed += 1
            except Exception as e:
                logger.warning(f"Failed to replay mutation: {e}")

        logger.info(f"Replayed {replayed} mutations for session {session_id}")
        return replayed

    def clear_session(self, session_id: str) -> None:
        """Clear tracking for a session.

        Args:
            session_id: Session to clear
        """
        self._pending.pop(session_id, None)
        self._applied.pop(session_id, None)

    def get_stats(self) -> Dict[str, int]:
        """Get sync statistics.

        Returns:
            Dict with sync stats
        """
        return {
            "pending_sessions": len(self._pending),
            "pending_mutations": sum(len(m) for m in self._pending.values()),
            "tracked_sessions": len(self._applied),
            "total_applied": sum(len(a) for a in self._applied.values()),
        }
