"""Cluster State Manager for Distributed Honeypot Coordination.

Provides Redis-backed state synchronization across honeypot nodes,
enabling consistent emulation during distributed attacks.

Key features:
- Session state replication via Redis pub/sub
- Event broadcasting for attack correlation
- Leader election for coordination tasks
- Health monitoring and failover
"""

import asyncio
import json
from core.observability.logging import get_logger
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ..config import ClusterConfig, get_honeypot_config
from ..emulation.models import FSMutation, SessionState

logger = get_logger(__name__)


class ClusterStateManager:
    """Manage distributed state across honeypot cluster.

    Uses Redis for:
    - Key-value storage of session state
    - Pub/sub for real-time state updates
    - Sorted sets for event ordering

    Example:
        >>> manager = ClusterStateManager()
        >>> await manager.connect()
        >>> await manager.sync_session(session)
        >>> await manager.subscribe_to_updates(callback)
    """

    def __init__(
        self,
        config: Optional[ClusterConfig] = None,
        redis_url: Optional[str] = None,
        node_id: Optional[str] = None,
    ):
        """Initialize cluster state manager.

        Args:
            config: Cluster configuration
            redis_url: Override Redis URL
            node_id: Override node identifier
        """
        self.config = config or get_honeypot_config().cluster
        self.redis_url = redis_url or self.config.redis_url
        self.node_id = node_id or self.config.node_id or str(uuid.uuid4())[:8]

        self._redis: Optional[Any] = None
        self._pubsub: Optional[Any] = None
        self._connected = False
        self._subscriptions: Dict[str, Callable] = {}
        self._listener_task: Optional[asyncio.Task] = None

        # Local cache of synced sessions
        self._session_cache: Dict[str, SessionState] = {}

        logger.debug(f"ClusterStateManager initialized: node_id={self.node_id}")

    async def connect(self) -> None:
        """Connect to Redis cluster backend.

        Raises:
            ConnectionError: If Redis connection fails
        """
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

            # Test connection
            await self._redis.ping()
            self._connected = True

            # Register this node
            await self._register_node()

            logger.info(
                f"Connected to cluster: node={self.node_id}, redis={self.redis_url}"
            )

        except ImportError:
            logger.warning("redis package not installed, cluster mode disabled")
            raise ConnectionError("redis package required for cluster mode")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(f"Redis connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Redis and cleanup."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()

        if self._redis:
            await self._unregister_node()
            await self._redis.close()

        self._connected = False
        logger.info(f"Disconnected from cluster: node={self.node_id}")

    async def _register_node(self) -> None:
        """Register this node in the cluster."""
        node_key = f"honeypot:cluster:nodes:{self.node_id}"
        node_data = {
            "node_id": self.node_id,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }

        await self._redis.hset(node_key, mapping=node_data)
        await self._redis.expire(node_key, self.config.session_ttl_minutes * 60)

        # Add to active nodes set
        await self._redis.sadd("honeypot:cluster:active_nodes", self.node_id)

    async def _unregister_node(self) -> None:
        """Unregister this node from the cluster."""
        await self._redis.delete(f"honeypot:cluster:nodes:{self.node_id}")
        await self._redis.srem("honeypot:cluster:active_nodes", self.node_id)

    async def heartbeat(self) -> None:
        """Send heartbeat to maintain node registration."""
        if not self._connected:
            return

        node_key = f"honeypot:cluster:nodes:{self.node_id}"
        await self._redis.hset(
            node_key, "last_heartbeat", datetime.now(timezone.utc).isoformat()
        )
        await self._redis.expire(node_key, self.config.session_ttl_minutes * 60)

    # ========== Session State Sync ==========

    async def sync_session(self, session: SessionState) -> None:
        """Sync session state to cluster.

        Args:
            session: Session state to sync
        """
        if not self._connected:
            return

        session_key = f"honeypot:sessions:{session.session_id}"

        # Serialize session
        session_data = session.model_dump_json()

        # Store in Redis
        await self._redis.set(
            session_key,
            session_data,
            ex=self.config.session_ttl_minutes * 60,
        )

        # Publish update notification
        await self._publish_state_update(session.session_id, "session_updated")

        # Update local cache
        self._session_cache[session.session_id] = session

        logger.debug(f"Session synced: {session.session_id}")

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session state from cluster.

        Args:
            session_id: Session identifier

        Returns:
            SessionState or None if not found
        """
        # Check local cache first
        if session_id in self._session_cache:
            return self._session_cache[session_id]

        if not self._connected:
            return None

        session_key = f"honeypot:sessions:{session_id}"
        data = await self._redis.get(session_key)

        if data:
            session = SessionState.model_validate_json(data)
            self._session_cache[session_id] = session
            return session

        return None

    async def delete_session(self, session_id: str) -> None:
        """Delete session from cluster.

        Args:
            session_id: Session to delete
        """
        if not self._connected:
            return

        session_key = f"honeypot:sessions:{session_id}"
        await self._redis.delete(session_key)

        self._session_cache.pop(session_id, None)

        await self._publish_state_update(session_id, "session_deleted")

    async def list_sessions(self) -> List[str]:
        """List all active session IDs in cluster.

        Returns:
            List of session IDs
        """
        if not self._connected:
            return list(self._session_cache.keys())

        keys = await self._redis.keys("honeypot:sessions:*")
        return [k.split(":")[-1] for k in keys]

    # ========== Mutation Sync ==========

    async def sync_mutation(
        self,
        session_id: str,
        mutation: FSMutation,
    ) -> None:
        """Sync filesystem mutation to cluster.

        Args:
            session_id: Session that generated mutation
            mutation: Filesystem mutation
        """
        if not self._connected:
            return

        mutations_key = f"honeypot:mutations:{session_id}"

        # Add to sorted set with timestamp score
        score = mutation.timestamp.timestamp()
        await self._redis.zadd(
            mutations_key,
            {mutation.model_dump_json(): score},
        )

        # Trim to limit
        await self._redis.zremrangebyrank(
            mutations_key,
            0,
            -(self.config.mutation_history_limit + 1),
        )

        # Set expiry
        await self._redis.expire(mutations_key, self.config.session_ttl_minutes * 60)

        # Publish mutation event
        await self._publish_event(
            "mutation",
            {
                "session_id": session_id,
                "mutation": mutation.model_dump_compact(),
            },
        )

    async def get_mutations(
        self,
        session_id: str,
        since: Optional[datetime] = None,
    ) -> List[FSMutation]:
        """Get mutations for session from cluster.

        Args:
            session_id: Session identifier
            since: Only get mutations after this time

        Returns:
            List of FSMutation objects
        """
        if not self._connected:
            return []

        mutations_key = f"honeypot:mutations:{session_id}"

        if since:
            min_score = since.timestamp()
            data = await self._redis.zrangebyscore(mutations_key, min_score, "+inf")
        else:
            data = await self._redis.zrange(mutations_key, 0, -1)

        mutations = []
        for item in data:
            try:
                mutation = FSMutation.model_validate_json(item)
                mutations.append(mutation)
            except Exception as e:
                logger.warning(f"Failed to parse mutation: {e}")

        return mutations

    # ========== Event Broadcasting ==========

    async def broadcast_event(
        self,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Broadcast event to all cluster nodes.

        Args:
            event_type: Type of event
            data: Event data
        """
        await self._publish_event(event_type, data)

    async def _publish_state_update(self, session_id: str, action: str) -> None:
        """Publish state update notification."""
        if not self._connected:
            return

        message = json.dumps(
            {
                "action": action,
                "session_id": session_id,
                "node_id": self.node_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        await self._redis.publish(self.config.state_channel, message)

    async def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish event to cluster."""
        if not self._connected:
            return

        message = json.dumps(
            {
                "type": event_type,
                "data": data,
                "node_id": self.node_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        await self._redis.publish(self.config.event_channel, message)

    # ========== Subscriptions ==========

    async def subscribe_to_updates(
        self,
        callback: Callable[[str, str, Dict[str, Any]], None],
    ) -> None:
        """Subscribe to state update notifications.

        Args:
            callback: Function(session_id, action, data) to call on updates
        """
        if not self._connected:
            return

        self._subscriptions["state"] = callback

        if not self._listener_task:
            self._start_listener()

    async def subscribe_to_events(
        self,
        callback: Callable[[str, Dict[str, Any]], None],
    ) -> None:
        """Subscribe to cluster events.

        Args:
            callback: Function(event_type, data) to call on events
        """
        if not self._connected:
            return

        self._subscriptions["events"] = callback

        if not self._listener_task:
            self._start_listener()

    def _start_listener(self) -> None:
        """Start background listener for pub/sub messages."""
        self._listener_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self) -> None:
        """Background loop listening for pub/sub messages."""

        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(
            self.config.state_channel,
            self.config.event_channel,
        )

        try:
            async for message in self._pubsub.listen():
                if message["type"] != "message":
                    continue

                try:
                    data = json.loads(message["data"])
                    channel = message["channel"]

                    # Skip our own messages
                    if data.get("node_id") == self.node_id:
                        continue

                    if channel == self.config.state_channel:
                        callback = self._subscriptions.get("state")
                        if callback:
                            await callback(
                                data.get("session_id"),
                                data.get("action"),
                                data,
                            )

                    elif channel == self.config.event_channel:
                        callback = self._subscriptions.get("events")
                        if callback:
                            await callback(data.get("type"), data.get("data", {}))

                except Exception as e:
                    logger.warning(f"Error processing pub/sub message: {e}")

        except asyncio.CancelledError:
            pass

    # ========== Cluster Info ==========

    async def get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster status information.

        Returns:
            Dict with cluster status
        """
        if not self._connected:
            return {
                "connected": False,
                "node_id": self.node_id,
            }

        active_nodes = await self._redis.smembers("honeypot:cluster:active_nodes")
        session_count = len(await self._redis.keys("honeypot:sessions:*"))

        return {
            "connected": True,
            "node_id": self.node_id,
            "active_nodes": list(active_nodes),
            "node_count": len(active_nodes),
            "session_count": session_count,
        }

    def is_connected(self) -> bool:
        """Check if connected to cluster.

        Returns:
            True if connected
        """
        return self._connected
