"""The supervisor must never mistake a stranger's health for its own child's.

Regression cover for the restart storm observed in production: a worker that
``uvicorn`` replaced left its Node child orphaned on the fixed rendezvous port,
so every child the newly elected leader spawned died with ``EADDRINUSE`` while
the orphan kept answering ``/api/health``. The port-shaped health gate read
green, the keep-alive loop logged a successful restart and reset its backoff,
and the supervisor respawned a doomed child once a second — 142 attempts and
counting, none of them ever able to succeed.

Three seams keep that from recurring:

* :func:`~plugins.dbview.supervisor.portguard.wait_for_free_port` refuses to
  spawn into an occupied port (tolerating a predecessor's shutdown window);
* :func:`~plugins.dbview.supervisor.health.reject_foreign_listener` rejects a
  green probe our own child cannot have answered, should a listener appear
  after that check;
* :func:`~plugins.dbview.supervisor.launcher.build_launch_argv` ties the child
  to this process' lifetime so the orphan is not created in the first place.
"""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path

import pytest

from plugins.dbview.supervisor import NodeSupervisor, SupervisorConfig
from plugins.dbview.supervisor.health import (
    StartupTimeoutError,
    reject_foreign_listener,
)
from plugins.dbview.supervisor.portguard import (
    PortUnavailableError,
    is_port_taken,
    wait_for_free_port,
)


class _DeadChild:
    """A child that has already exited — what EADDRINUSE leaves behind."""

    returncode: int | None = 1
    pid = 4242


@pytest.fixture
def listener() -> socket.socket:
    """A bound loopback listener standing in for the orphaned child."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(5)
    yield sock
    sock.close()


def _supervisor(tmp_path: Path, **kwargs: float) -> NodeSupervisor:
    cfg = SupervisorConfig(
        plugin_dir=tmp_path,
        dbview_root=tmp_path / "dbview",
        **kwargs,  # type: ignore[arg-type]
    )
    return NodeSupervisor(cfg)


# ----------------------------------------------------------------------
# portguard
# ----------------------------------------------------------------------


def test_is_port_taken_sees_a_listener(listener: socket.socket) -> None:
    assert is_port_taken("127.0.0.1", listener.getsockname()[1]) is True


def test_is_port_taken_is_false_for_a_free_port(listener: socket.socket) -> None:
    port = listener.getsockname()[1]
    listener.close()
    assert is_port_taken("127.0.0.1", port) is False


async def test_wait_for_free_port_returns_at_once_when_nothing_listens(
    listener: socket.socket,
) -> None:
    port = listener.getsockname()[1]
    listener.close()
    await wait_for_free_port("127.0.0.1", port, timeout_s=5.0)


async def test_wait_for_free_port_raises_while_the_orphan_holds_it(
    listener: socket.socket,
) -> None:
    port = listener.getsockname()[1]
    with pytest.raises(PortUnavailableError) as excinfo:
        await wait_for_free_port("127.0.0.1", port, timeout_s=0.0)
    # The message has to carry the diagnosis: an operator reading the log must
    # not have to rediscover the orphan from a wall of EADDRINUSE lines.
    assert "orphaned" in str(excinfo.value)
    assert str(port) in str(excinfo.value)


async def test_wait_for_free_port_tolerates_a_predecessor_still_shutting_down(
    listener: socket.socket,
) -> None:
    """A leadership handover must not surface as an error."""
    port = listener.getsockname()[1]

    async def _release_soon() -> None:
        await asyncio.sleep(0.3)
        listener.close()

    releaser = asyncio.create_task(_release_soon())
    await wait_for_free_port("127.0.0.1", port, timeout_s=5.0)
    await releaser


# ----------------------------------------------------------------------
# spawn + health gate
# ----------------------------------------------------------------------


async def test_spawn_refuses_an_occupied_port(
    tmp_path: Path, listener: socket.socket
) -> None:
    api_dist = tmp_path / "dbview" / "apps" / "api" / "dist"
    api_dist.mkdir(parents=True)
    (api_dist / "main.js").write_text("// stand-in for the prod bundle\n")

    sup = _supervisor(tmp_path, port_release_timeout_s=0.0)
    sup._port = listener.getsockname()[1]
    with pytest.raises(PortUnavailableError):
        await sup._spawn()
    assert sup._process is None, "no child may be spawned into a held port"


_PROBE_URL = "http://127.0.0.1:8890/api/health"


def test_health_gate_rejects_a_probe_our_child_cannot_have_answered() -> None:
    with pytest.raises(StartupTimeoutError) as excinfo:
        reject_foreign_listener(_PROBE_URL, _DeadChild.returncode)
    assert "held by another process" in str(excinfo.value)


def test_health_gate_accepts_a_probe_while_our_child_runs() -> None:
    reject_foreign_listener(_PROBE_URL, None)


async def test_wait_for_health_fails_when_a_stranger_answers_for_a_dead_child(
    tmp_path: Path, listener: socket.socket
) -> None:
    """The whole bug in one assertion: green port, dead child, honest failure."""
    sup = _supervisor(tmp_path, startup_timeout_s=2.0, health_probe_interval_s=0.05)
    sup._port = listener.getsockname()[1]
    sup._process = _DeadChild()  # type: ignore[assignment]
    with pytest.raises(StartupTimeoutError):
        await sup._wait_for_health()
    assert sup.is_healthy() is False
