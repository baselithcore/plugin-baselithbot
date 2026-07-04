"""Tests for the dbview multi-worker single-child model.

Under ``WEB_CONCURRENCY>1`` every uvicorn worker used to spawn its own Node
child with a private in-memory store, so a connection created on one worker was
*"not found"* on the next request that round-robined to another. These tests
cover the fix:

* leader election degrades open when Postgres is unavailable;
* the gateway-signing secret is shared (deterministic) across workers so the
  single leader-owned child accepts follower-forwarded identity;
* the upstream port is pinned under coordinated leadership so followers know
  where to forward without any cross-worker publication;
* a follower supervisor tracks the shared child's health without ever spawning.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from plugins.dbview import leader
from plugins.dbview.leader import DBVIEW_LEADER_LOCK_KEY, acquire_dbview_leadership
from plugins.dbview.plugin import _DEFAULT_INTERNAL_PORT, DbviewPlugin
from plugins.dbview.supervisor import NodeSupervisor, SupervisorConfig

pytestmark = pytest.mark.unit


class _StorageStub:
    def __init__(self, enabled: bool) -> None:
        self.postgres_enabled = enabled
        self.conninfo = "postgresql://unused"


# --------------------------------------------------------------------------
# Leader election
# --------------------------------------------------------------------------


async def test_leadership_degrades_to_leader_when_postgres_disabled(monkeypatch):
    monkeypatch.setattr(leader, "get_storage_config", lambda: _StorageStub(False))
    result = await acquire_dbview_leadership()
    assert result.is_leader is True
    assert result.degraded is True


async def test_leadership_degrades_when_db_connect_fails(monkeypatch):
    monkeypatch.setattr(leader, "get_storage_config", lambda: _StorageStub(True))

    async def _boom(*_a, **_k):
        raise OSError("connection refused")

    monkeypatch.setattr(leader.AsyncConnection, "connect", _boom)
    result = await acquire_dbview_leadership()
    assert result.is_leader is True
    assert result.degraded is True


def test_lock_key_is_namespaced_away_from_siblings():
    # Distinct from auth's schema lock (0x41757468) and honeypot's listener
    # lock (0x48704C697374656E) so the three never collide.
    assert DBVIEW_LEADER_LOCK_KEY not in (0x41757468, 0x48704C697374656E)


# --------------------------------------------------------------------------
# Shared gateway secret
# --------------------------------------------------------------------------


def test_gateway_secret_is_deterministic_and_shared_across_workers():
    env = {"DBVIEW_SECRET": "s" * 24}
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("DBVIEW_GATEWAY_SECRET", None)
        a = DbviewPlugin()._resolve_gateway_secret()
        b = DbviewPlugin()._resolve_gateway_secret()
    # Two independently-initialised workers must derive the SAME secret, or the
    # single leader-owned child rejects follower-signed identity headers.
    assert a == b
    assert len(a) >= 16


def test_gateway_secret_prefers_explicit_operator_value():
    env = {"DBVIEW_SECRET": "s" * 24, "DBVIEW_GATEWAY_SECRET": "k" * 20}
    with patch.dict(os.environ, env, clear=False):
        secret = DbviewPlugin()._resolve_gateway_secret()
    assert secret == "k" * 20


def test_gateway_secret_ignores_too_short_explicit_value():
    env = {"DBVIEW_SECRET": "s" * 24, "DBVIEW_GATEWAY_SECRET": "short"}
    with patch.dict(os.environ, env, clear=False):
        secret = DbviewPlugin()._resolve_gateway_secret()
    # Falls back to the derived value (>= 16 chars) instead of the weak input.
    assert secret != "short"
    assert len(secret) >= 16


# --------------------------------------------------------------------------
# Shared rendezvous port
# --------------------------------------------------------------------------


def test_internal_port_pins_default_under_coordinated_leadership():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("DBVIEW_INTERNAL_PORT", None)
        port = DbviewPlugin()._resolve_internal_port(coordinated=True, config=None)
    assert port == _DEFAULT_INTERNAL_PORT


def test_internal_port_stays_ephemeral_when_degraded():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("DBVIEW_INTERNAL_PORT", None)
        port = DbviewPlugin()._resolve_internal_port(coordinated=False, config=None)
    assert port is None  # historical single-worker behaviour preserved


def test_internal_port_env_override_wins_in_both_modes():
    with patch.dict(os.environ, {"DBVIEW_INTERNAL_PORT": "51234"}, clear=False):
        plugin = DbviewPlugin()
        assert plugin._resolve_internal_port(coordinated=True, config=None) == 51234
        assert plugin._resolve_internal_port(coordinated=False, config=None) == 51234


def test_internal_port_explicit_config_beats_env():
    with patch.dict(os.environ, {"DBVIEW_INTERNAL_PORT": "51234"}, clear=False):
        port = DbviewPlugin()._resolve_internal_port(
            coordinated=True, config={"port": 6000}
        )
    assert port == 6000


# --------------------------------------------------------------------------
# Follower supervisor
# --------------------------------------------------------------------------


async def test_follower_tracks_health_without_spawning(tmp_path: Path):
    cfg = SupervisorConfig(
        plugin_dir=tmp_path, dbview_root=tmp_path / "dbview", port=43117
    )
    sup = NodeSupervisor(cfg)

    async def _probe_ok() -> bool:
        return True

    with patch.object(sup, "_probe_health", _probe_ok):
        await sup.start_follower()
        assert sup.is_healthy() is True
        # A follower NEVER spawns or restarts the child — the leader owns it.
        assert sup._process is None
        await sup.stop()


async def test_follower_requires_a_fixed_port(tmp_path: Path):
    cfg = SupervisorConfig(
        plugin_dir=tmp_path, dbview_root=tmp_path / "dbview", port=None
    )
    sup = NodeSupervisor(cfg)
    with pytest.raises(RuntimeError, match="fixed shared port"):
        await sup.start_follower()
