"""Lateral Movement Coherence for Cross-Node Session Tracking.

Provides mechanisms to detect and maintain coherent state when
attackers move laterally between honeypot nodes.

Key capabilities:
- Credential-based session correlation
- State hydration for lateral sessions
- Attack chain reconstruction
"""

from core.observability.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from ..emulation.models import SessionState
from .state_manager import ClusterStateManager

logger = get_logger(__name__)


class LateralMovementCoherence:
    """Track and correlate lateral movement across cluster nodes.

    When an attacker captures credentials in one honeypot and uses
    them to access another, this module ensures the new session
    has coherent state (same files, environment, etc).

    Example:
        >>> coherence = LateralMovementCoherence(cluster_manager)
        >>> related = await coherence.find_related_sessions(session)
        >>> if related:
        ...     await coherence.hydrate_session(session, related[0])
    """

    def __init__(
        self,
        cluster_manager: ClusterStateManager,
        correlation_window_minutes: int = 30,
    ):
        """Initialize lateral movement tracker.

        Args:
            cluster_manager: Cluster state manager for coordination
            correlation_window_minutes: Time window for session correlation
        """
        self.cluster = cluster_manager
        self.correlation_window = timedelta(minutes=correlation_window_minutes)

        # Credential -> session mapping
        self._credential_sessions: Dict[str, List[str]] = {}

        # IP -> sessions mapping
        self._ip_sessions: Dict[str, List[str]] = {}

        # Attack chain tracking
        self._attack_chains: Dict[str, List[str]] = {}

    async def register_session(self, session: SessionState) -> None:
        """Register a new session for correlation.

        Args:
            session: Session to register
        """
        # Index by source IP
        if session.source_ip:
            if session.source_ip not in self._ip_sessions:
                self._ip_sessions[session.source_ip] = []
            self._ip_sessions[session.source_ip].append(session.session_id)

        # Index by credentials used
        for attempt in session.auth_attempts:
            if attempt.success:
                cred_key = f"{attempt.username}:{attempt.password}"
                if cred_key not in self._credential_sessions:
                    self._credential_sessions[cred_key] = []
                self._credential_sessions[cred_key].append(session.session_id)

    async def find_related_sessions(
        self,
        session: SessionState,
    ) -> List[SessionState]:
        """Find sessions related to current session.

        Related sessions may share:
        - Same source IP
        - Same credentials
        - Extracted credentials used for new session

        Args:
            session: Current session

        Returns:
            List of related SessionState objects
        """
        related_ids: Set[str] = set()

        # Find by source IP
        if session.source_ip and session.source_ip in self._ip_sessions:
            for sid in self._ip_sessions[session.source_ip]:
                if sid != session.session_id:
                    related_ids.add(sid)

        # Find by credentials
        for attempt in session.auth_attempts:
            cred_key = f"{attempt.username}:{attempt.password}"
            if cred_key in self._credential_sessions:
                for sid in self._credential_sessions[cred_key]:
                    if sid != session.session_id:
                        related_ids.add(sid)

        # Fetch related sessions from cluster
        related_sessions = []
        for sid in related_ids:
            related_session = await self.cluster.get_session(sid)
            if related_session:
                # Check time window
                time_diff = abs(
                    (session.created_at - related_session.created_at).total_seconds()
                )
                if time_diff < self.correlation_window.total_seconds():
                    related_sessions.append(related_session)

        # Sort by creation time (most recent first)
        related_sessions.sort(key=lambda s: s.created_at, reverse=True)

        return related_sessions

    async def detect_lateral_movement(
        self,
        session: SessionState,
    ) -> Optional[Tuple[SessionState, str]]:
        """Detect if session is result of lateral movement.

        Checks if credentials used in this session were captured
        in a previous session, indicating lateral movement.

        Args:
            session: New session to check

        Returns:
            Tuple of (source_session, credential_used) or None
        """
        for attempt in session.auth_attempts:
            if attempt.success:
                cred_key = f"{attempt.username}:{attempt.password}"

                # Check if this credential was captured elsewhere
                source_sessions = self._credential_sessions.get(cred_key, [])

                for sid in source_sessions:
                    if sid == session.session_id:
                        continue

                    source = await self.cluster.get_session(sid)
                    if source:
                        # Verify the credential was captured (not used) in source
                        for src_attempt in source.auth_attempts:
                            if (
                                src_attempt.username == attempt.username
                                and src_attempt.password == attempt.password
                                and not src_attempt.success
                            ):
                                logger.info(
                                    f"Lateral movement detected: "
                                    f"{source.session_id} -> {session.session_id}"
                                )
                                return source, cred_key

        return None

    async def hydrate_session(
        self,
        target: SessionState,
        source: SessionState,
    ) -> None:
        """Hydrate target session with state from source session.

        Copies relevant state to make environment consistent
        as if attacker moved laterally.

        Args:
            target: Session to hydrate
            source: Source session with state
        """
        logger.info(f"Hydrating session {target.session_id} from {source.session_id}")

        # Copy command history context (last 5 commands)
        # This helps LLM maintain conversation awareness

        # Copy environment variables set by attacker
        for mutation in source.env_mutations:
            if mutation.action == "set":
                target.env_vars[mutation.var_name] = mutation.var_value or ""

        # Copy detected TTPs for context
        for ttp_pred in source.detected_ttps:
            if ttp_pred not in target.detected_ttps:
                target.detected_ttps.append(ttp_pred)

        # Sync mutations so VFS can be replayed
        mutations = await self.cluster.get_mutations(source.session_id)
        for mutation in mutations:
            target.fs_mutations.append(mutation)

        # Update cluster state
        await self.cluster.sync_session(target)

        # Record in attack chain
        chain_id = source.session_id.split("-")[0]
        if chain_id not in self._attack_chains:
            self._attack_chains[chain_id] = [source.session_id]
        self._attack_chains[chain_id].append(target.session_id)

    async def get_attack_chain(
        self,
        session_id: str,
    ) -> List[SessionState]:
        """Get full attack chain for a session.

        Returns all sessions in the attack chain, ordered
        chronologically.

        Args:
            session_id: Any session in the chain

        Returns:
            List of SessionState in chain order
        """
        # Find chain containing this session
        chain_ids = None
        for chain_key, chain in self._attack_chains.items():
            if session_id in chain:
                chain_ids = chain
                break

        if not chain_ids:
            # No chain, just return the single session
            session = await self.cluster.get_session(session_id)
            return [session] if session else []

        # Fetch all sessions in chain
        sessions = []
        for sid in chain_ids:
            session = await self.cluster.get_session(sid)
            if session:
                sessions.append(session)

        # Sort by creation time
        sessions.sort(key=lambda s: s.created_at)

        return sessions

    def get_correlation_stats(self) -> Dict[str, Any]:
        """Get correlation statistics.

        Returns:
            Dict with correlation stats
        """
        return {
            "tracked_ips": len(self._ip_sessions),
            "tracked_credentials": len(self._credential_sessions),
            "attack_chains": len(self._attack_chains),
            "total_chained_sessions": sum(
                len(chain) for chain in self._attack_chains.values()
            ),
        }

    async def cleanup_old_correlations(
        self,
        max_age_hours: int = 24,
    ) -> int:
        """Clean up old correlation data.

        Args:
            max_age_hours: Maximum age of data to keep

        Returns:
            Number of correlations cleaned
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cleaned = 0

        # Clean IP sessions
        for ip, sessions in list(self._ip_sessions.items()):
            valid_sessions = []
            for sid in sessions:
                session = await self.cluster.get_session(sid)
                if session and session.created_at > cutoff:
                    valid_sessions.append(sid)
                else:
                    cleaned += 1

            if valid_sessions:
                self._ip_sessions[ip] = valid_sessions
            else:
                del self._ip_sessions[ip]

        return cleaned
