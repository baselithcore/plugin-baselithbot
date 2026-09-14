"""Cross-pod rendezvous: one Node child, reachable from every replica.

The advisory lock already elected a single leader cluster-wide, but every
follower forwarded to ``http://127.0.0.1:<fixed port>`` — an address that
resolves to the leader's child only inside the leader's own network namespace.
With ``replicaCount: 2`` (the chart default) the pod that lost the election had
nothing on that port, so the console answered 404 from one replica and 200 from
the other, at random, for the same URL.

These tests cover the fix and, just as importantly, its silence: a single-pod
deployment must behave exactly as it did before.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from plugins.dbview import rendezvous
from plugins.dbview.rendezvous import (
    LEADER_KEY,
    LEADER_TTL_SECONDS,
    LeaderRendezvous,
    clear_leader_origin,
    lookup_leader_origin,
    publish_leader_origin,
    resolve_advertised_host,
    resolve_cross_pod_host,
)
from plugins.dbview.supervisor import NodeSupervisor, SupervisorConfig

pytestmark = pytest.mark.unit


class _FakeRedis:
    """Just enough Redis for set/get/delete with a TTL we can assert on."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.closed = False

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def aclose(self) -> None:
        self.closed = True


def _with_redis(monkeypatch, client: object | None) -> None:
    async def _factory():
        return client

    monkeypatch.setattr(rendezvous, "_client", _factory)


# --------------------------------------------------------------------------
# Advertised address
# --------------------------------------------------------------------------


def test_loopback_is_never_advertised(monkeypatch) -> None:
    """Publishing loopback would tell a peer to dial itself."""
    monkeypatch.setenv("DBVIEW_ADVERTISE_HOST", "127.0.0.1")
    monkeypatch.delenv("POD_IP", raising=False)
    assert resolve_advertised_host() is None


def test_explicit_advertise_host_wins_over_pod_ip(monkeypatch) -> None:
    monkeypatch.setenv("DBVIEW_ADVERTISE_HOST", "dbview.svc.cluster.local")
    monkeypatch.setenv("POD_IP", "10.1.2.3")
    assert resolve_advertised_host() == "dbview.svc.cluster.local"


def test_pod_ip_is_the_fallback(monkeypatch) -> None:
    monkeypatch.delenv("DBVIEW_ADVERTISE_HOST", raising=False)
    monkeypatch.setenv("POD_IP", "10.1.2.3")
    assert resolve_advertised_host() == "10.1.2.3"


def test_no_address_means_single_pod(monkeypatch) -> None:
    monkeypatch.delenv("DBVIEW_ADVERTISE_HOST", raising=False)
    monkeypatch.delenv("POD_IP", raising=False)
    assert resolve_advertised_host() is None


class _Storage:
    def __init__(self, cache_redis_url: str) -> None:
        self.cache_redis_url = cache_redis_url


def test_cross_pod_needs_redis_too(monkeypatch) -> None:
    """An address nobody can publish is not worth widening the bind for."""
    import core.config as config_module

    monkeypatch.setenv("POD_IP", "10.1.2.3")
    monkeypatch.setattr(config_module, "get_storage_config", lambda: _Storage(""))
    assert resolve_cross_pod_host() is None


def test_cross_pod_is_on_with_an_address_and_redis(monkeypatch) -> None:
    import core.config as config_module

    monkeypatch.setenv("POD_IP", "10.1.2.3")
    monkeypatch.setattr(
        config_module, "get_storage_config", lambda: _Storage("redis://r:6379/0")
    )
    assert resolve_cross_pod_host() == "10.1.2.3"


# --------------------------------------------------------------------------
# Publish / lookup
# --------------------------------------------------------------------------


async def test_published_origin_round_trips(monkeypatch) -> None:
    redis = _FakeRedis()
    _with_redis(monkeypatch, redis)

    assert await publish_leader_origin("http://10.1.2.3:43117") is True
    assert await lookup_leader_origin() == "http://10.1.2.3:43117"
    assert redis.store[LEADER_KEY] == "http://10.1.2.3:43117"


async def test_the_key_expires_so_a_dead_leader_stops_attracting_traffic(
    monkeypatch,
) -> None:
    redis = _FakeRedis()
    _with_redis(monkeypatch, redis)
    await publish_leader_origin("http://10.1.2.3:43117")
    assert redis.ttls[LEADER_KEY] == LEADER_TTL_SECONDS


async def test_no_redis_is_not_an_error(monkeypatch) -> None:
    """The single-pod deployment goes through this path on every boot."""
    _with_redis(monkeypatch, None)
    assert await publish_leader_origin("http://10.1.2.3:43117") is False
    assert await lookup_leader_origin() is None


async def test_an_unreachable_redis_degrades_to_loopback(monkeypatch) -> None:
    class _Broken:
        async def get(self, key: str) -> str:
            raise ConnectionError("redis down")

        async def aclose(self) -> None:
            return None

    _with_redis(monkeypatch, _Broken())
    assert await lookup_leader_origin() is None


async def test_shutdown_only_withdraws_our_own_origin(monkeypatch) -> None:
    """A successor may have published already; blanking it would take the
    whole console down instead of one pod."""
    redis = _FakeRedis()
    _with_redis(monkeypatch, redis)
    await publish_leader_origin("http://10.1.2.4:43117")

    await clear_leader_origin("http://10.1.2.3:43117")
    assert redis.store[LEADER_KEY] == "http://10.1.2.4:43117"

    await clear_leader_origin("http://10.1.2.4:43117")
    assert LEADER_KEY not in redis.store


# --------------------------------------------------------------------------
# The supervisor seam
# --------------------------------------------------------------------------


def _supervisor(host: str = "127.0.0.1") -> NodeSupervisor:
    root = Path("/nonexistent")
    return NodeSupervisor(
        SupervisorConfig(
            plugin_dir=root, dbview_root=root / "dbview", host=host, port=43117
        )
    )


def test_a_wildcard_bind_is_dialled_on_loopback() -> None:
    """0.0.0.0 is where a child listens, never an address to connect to."""
    assert _supervisor("0.0.0.0").base_url == "http://127.0.0.1:43117"


def test_peer_origin_overrides_the_local_upstream() -> None:
    supervisor = _supervisor()
    assert supervisor.upstream_url == "http://127.0.0.1:43117"

    supervisor.set_peer_origin("http://10.1.2.3:43117")
    assert supervisor.upstream_url == "http://10.1.2.3:43117"

    supervisor.set_peer_origin(None)
    assert supervisor.upstream_url == "http://127.0.0.1:43117"


def test_the_health_probe_follows_the_upstream() -> None:
    """Probing our own empty loopback would report the console down while the
    leader's child is serving it."""
    supervisor = _supervisor()
    supervisor.set_peer_origin("http://10.1.2.3:43117")
    assert supervisor._health_url().startswith("http://10.1.2.3:43117")


# --------------------------------------------------------------------------
# The refresh task
# --------------------------------------------------------------------------


class _Spy:
    def __init__(self) -> None:
        self.origins: list[str | None] = []

    def set_peer_origin(self, origin: str | None) -> None:
        self.origins.append(origin)


async def test_a_leader_publishes_on_start_and_withdraws_on_stop(
    monkeypatch,
) -> None:
    redis = _FakeRedis()
    _with_redis(monkeypatch, redis)

    handle = LeaderRendezvous(_Spy(), is_leader=True, origin="http://10.1.2.3:43117")
    await handle.start()
    assert redis.store[LEADER_KEY] == "http://10.1.2.3:43117"

    await handle.stop()
    assert LEADER_KEY not in redis.store


async def test_a_follower_points_at_the_published_leader(monkeypatch) -> None:
    redis = _FakeRedis()
    _with_redis(monkeypatch, redis)
    await publish_leader_origin("http://10.1.2.3:43117")

    spy = _Spy()
    handle = LeaderRendezvous(spy, is_leader=False, origin="http://10.1.2.9:43117")
    await handle.start()
    await handle.stop()

    assert spy.origins == ["http://10.1.2.3:43117"]


async def test_a_follower_reading_its_own_origin_falls_back(monkeypatch) -> None:
    """A pod that just lost leadership must not forward to itself in a loop."""
    redis = _FakeRedis()
    _with_redis(monkeypatch, redis)
    await publish_leader_origin("http://10.1.2.3:43117")

    spy = _Spy()
    handle = LeaderRendezvous(spy, is_leader=False, origin="http://10.1.2.3:43117")
    await handle.start()
    await handle.stop()

    assert spy.origins == [None]


async def test_without_an_origin_nothing_runs(monkeypatch) -> None:
    """Single-pod: no task, no Redis call, no behaviour change."""
    _with_redis(monkeypatch, _FakeRedis())
    spy = _Spy()
    handle = LeaderRendezvous(spy, is_leader=False, origin=None)
    await handle.start()

    assert handle.active is False
    assert spy.origins == []
    await handle.stop()


async def test_the_follower_re_resolves_so_a_moved_leader_is_followed(
    monkeypatch,
) -> None:
    """A rollout moves the child to another pod; a follower that resolved once
    would forward into the drained one until it restarted."""
    redis = _FakeRedis()
    _with_redis(monkeypatch, redis)
    monkeypatch.setattr(rendezvous, "LEADER_REFRESH_SECONDS", 0.01)
    await publish_leader_origin("http://10.1.2.3:43117")

    spy = _Spy()
    handle = LeaderRendezvous(spy, is_leader=False, origin="http://10.1.2.9:43117")
    await handle.start()
    await publish_leader_origin("http://10.1.2.4:43117")
    for _ in range(50):
        await asyncio.sleep(0.01)
        if spy.origins[-1] == "http://10.1.2.4:43117":
            break
    await handle.stop()

    assert spy.origins[0] == "http://10.1.2.3:43117"
    assert spy.origins[-1] == "http://10.1.2.4:43117"
