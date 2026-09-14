"""Where the single dbview Node child actually listens, across pods.

:mod:`plugins.dbview.leader` elects one owner of the Node child with a
PostgreSQL advisory lock, and that election is already cluster-wide: the lock
lives in the shared database, so exactly one *process* wins it no matter how
many pods are running. What was not cluster-wide is the address. Followers
forwarded to ``http://127.0.0.1:<fixed port>``, which resolves to the leader's
child only inside the leader's own network namespace. Across uvicorn workers in
one pod that is correct; across two pods it is not — the follower pod has no
child on that port, and every request to its replica of the console answered
404 while the other replica served the same URL happily.

This module is the missing half: the leader publishes the origin a *peer* can
dial, and followers read it. Redis carries it rather than Postgres because the
value is ephemeral cluster state with a TTL — the same reason the rate limiter
and the A2A nonce ledger live there — and because a plugin must not invent a
table (``core.db.ddl``: Alembic owns every table).

Degrades to the pre-existing behaviour, deliberately and quietly:

* no Redis configured → :func:`lookup_leader_origin` returns ``None`` and the
  follower keeps dialling loopback, which is exactly right for the
  single-pod/multi-worker deployment this module does not change;
* Redis unreachable → same, plus a warning. The console degrades to "only the
  leader's pod serves it", never to a crash.

The published value expires: a leader that is SIGKILLed stops refreshing, the
key lapses within :data:`LEADER_TTL_SECONDS`, and followers fall back instead of
forwarding into a black hole until someone notices.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Final, Protocol

from core.observability.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "LEADER_KEY",
    "LeaderRendezvous",
    "LEADER_REFRESH_SECONDS",
    "LEADER_TTL_SECONDS",
    "clear_leader_origin",
    "lookup_leader_origin",
    "publish_leader_origin",
    "resolve_advertised_host",
    "resolve_cross_pod_host",
]

#: Redis key holding the origin of the pod that owns the Node child.
LEADER_KEY: Final = "baselith:dbview:leader-origin"

#: How long a published origin stays valid without a refresh. Long enough to
#: ride out a slow tick, short enough that a dead leader stops attracting
#: traffic within one health-probe cycle.
LEADER_TTL_SECONDS: Final = 30

#: Refresh cadence. Comfortably below the TTL so a single missed tick — a GC
#: pause, a Redis blip — never expires a healthy leader.
LEADER_REFRESH_SECONDS: Final = 10


def resolve_advertised_host() -> str | None:
    """The host a *peer* should dial to reach this pod's Node child.

    Loopback is never the answer: the whole point is an address another pod can
    route to. ``DBVIEW_ADVERTISE_HOST`` wins for an operator who knows better
    (a Service DNS name, a stable IP); otherwise ``POD_IP``, which the Helm
    chart injects from the downward API.

    Returns:
        The advertised host, or ``None`` when this deployment has no
        cross-pod address to offer — in which case the plugin stays in its
        single-pod behaviour rather than publishing something undialable.
    """
    for name in ("DBVIEW_ADVERTISE_HOST", "POD_IP"):
        value = os.environ.get(name, "").strip()
        # nosec B104 - the wildcard is REJECTED here, never bound: a peer
        # cannot dial 0.0.0.0, so advertising it would be worse than silence.
        if value and value not in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):  # nosec B104
            return value
    return None


def resolve_cross_pod_host() -> str | None:
    """The host peers should dial, or ``None`` to stay single-pod.

    Cross-pod mode needs two things at once: an address worth advertising
    (:func:`resolve_advertised_host`) and somewhere to publish it. Without both,
    a published origin is either undialable or unreadable, and widening the
    child's bind would buy nothing but exposure — so the plugin keeps its
    loopback behaviour, which is correct for a single pod.

    Returns:
        The advertised host, or ``None``.
    """
    host = resolve_advertised_host()
    if host is None:
        return None
    try:
        from core.config import get_storage_config

        if not (getattr(get_storage_config(), "cache_redis_url", "") or ""):
            logger.info(
                "[dbview] %s is advertisable but no Redis is configured; "
                "staying on loopback (a second replica would answer 404 for "
                "the console).",
                host,
            )
            return None
    except Exception as exc:  # pragma: no cover - minimal envs
        logger.debug("[dbview] cache config unavailable: %s", exc)
        return None
    return host


async def _client():  # type: ignore[no-untyped-def]
    """Open a Redis client for the configured cache backend, or ``None``.

    Returns:
        A decoding Redis client, or ``None`` when the deployment declared no
        Redis — which is the ordinary single-node case, not an error.
    """
    from core.config import get_storage_config

    url = getattr(get_storage_config(), "cache_redis_url", "") or ""
    if not url:
        return None
    from core.cache.redis_cache import create_redis_client

    return create_redis_client(url, decode_responses=True)


async def publish_leader_origin(origin: str) -> bool:
    """Announce that this pod's Node child is reachable at ``origin``.

    Args:
        origin: A dialable ``http://host:port`` for a peer pod.

    Returns:
        ``True`` when the announcement landed. ``False`` means no Redis, or an
        unreachable one — the deployment then behaves as it did before this
        module existed.
    """
    client = None
    try:
        client = await _client()
        if client is None:
            return False
        await client.set(LEADER_KEY, origin, ex=LEADER_TTL_SECONDS)
        return True
    except Exception as exc:
        logger.warning(
            "[dbview] could not publish the leader origin (%s: %s); replicas "
            "other than this one will answer 404 for the console.",
            type(exc).__name__,
            exc,
        )
        return False
    finally:
        await _close(client)


async def lookup_leader_origin() -> str | None:
    """Read the origin of the pod that currently owns the Node child.

    Returns:
        The published origin, or ``None`` when nothing is published (no Redis,
        an expired key, or a single-pod deployment that never published).
    """
    client = None
    try:
        client = await _client()
        if client is None:
            return None
        value = await client.get(LEADER_KEY)
        return str(value) if value else None
    except Exception as exc:
        logger.warning(
            "[dbview] could not read the leader origin (%s: %s); falling back "
            "to loopback.",
            type(exc).__name__,
            exc,
        )
        return None
    finally:
        await _close(client)


async def clear_leader_origin(origin: str) -> None:
    """Withdraw ``origin`` on a clean shutdown, if it is still ours.

    Checked rather than unconditional: between this pod losing the advisory
    lock and running its shutdown, another pod may already have published its
    own origin, and deleting the key then would blank a healthy leader.

    Args:
        origin: The origin this pod published.
    """
    client = None
    try:
        client = await _client()
        if client is None:
            return
        current = await client.get(LEADER_KEY)
        if current and str(current) == origin:
            await client.delete(LEADER_KEY)
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        logger.debug("[dbview] leader-origin cleanup skipped: %s", exc)
    finally:
        await _close(client)


async def _close(client: object | None) -> None:
    """Release the client without touching the shared pool it borrowed from."""
    if client is None:
        return
    try:
        await client.aclose()  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        logger.debug("[dbview] redis client close skipped: %s", exc)


class _PeerAware(Protocol):
    """The slice of ``NodeSupervisor`` this module drives."""

    def set_peer_origin(self, origin: str | None) -> None: ...


class LeaderRendezvous:
    """Keeps this pod's view of "where the Node child is" current.

    One task, two behaviours, because the two roles have opposite jobs:

    * **leader** — re-publishes its own origin every
      :data:`LEADER_REFRESH_SECONDS`, so the key outlives a blip but not the
      process. Nothing it reads matters; it *is* the answer.
    * **follower** — re-reads the key on the same cadence and repoints the
      supervisor. Re-reading rather than resolving once is the difference
      between a rollout that moves the leader and a follower that forwards
      into a pod which no longer owns the child.

    Stopping is not symmetric either: a leader withdraws its key so the next
    request does not chase a pod that is shutting down; a follower has nothing
    to withdraw.
    """

    def __init__(
        self,
        supervisor: _PeerAware,
        *,
        is_leader: bool,
        origin: str | None,
    ) -> None:
        """
        Args:
            supervisor: The supervisor to repoint (followers only).
            is_leader: Whether this process owns the Node child.
            origin: This pod's dialable origin; ``None`` disables the whole
                mechanism, which is the single-pod default.
        """
        self._supervisor = supervisor
        self._is_leader = is_leader
        self._origin = origin
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    @property
    def active(self) -> bool:
        """Whether cross-pod rendezvous is running at all."""
        return self._task is not None

    async def start(self) -> None:
        """Publish or resolve once, then keep it fresh in the background."""
        if self._origin is None:
            return
        await self._tick()
        self._task = asyncio.create_task(self._loop(), name="dbview-rendezvous")

    async def _loop(self) -> None:
        while not self._stopped.is_set():
            try:
                await asyncio.wait_for(
                    self._stopped.wait(), timeout=LEADER_REFRESH_SECONDS
                )
                return
            except asyncio.TimeoutError:
                pass
            await self._tick()

    async def _tick(self) -> None:
        if self._is_leader:
            assert self._origin is not None
            await publish_leader_origin(self._origin)
            return
        peer = await lookup_leader_origin()
        # Our own origin means the key is stale (we just lost leadership):
        # loopback is then the honest answer, not a request back to ourselves.
        self._supervisor.set_peer_origin(None if peer == self._origin else peer)

    async def stop(self) -> None:
        """Cancel the refresh and, for a leader, withdraw the published key."""
        self._stopped.set()
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if self._is_leader and self._origin is not None:
            await clear_leader_origin(self._origin)
