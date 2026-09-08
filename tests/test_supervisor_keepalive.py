"""Keep-alive loop behaviour of the dbview Node supervisor.

Focused on the exit-classification seam: a child killed by ``SIGTERM`` is the
signature of a *coordinated* shutdown (systemd's ``KillMode=control-group``,
``docker stop``, an operator ``kill``) reaching the whole process group before
the ASGI lifespan gets to ``plugin.shutdown()``. The loop must not mistake it
for a crash and respawn a child that is about to be killed too.

No Node process is spawned: the child is either a stand-in exposing the slice
of ``asyncio.subprocess.Process`` the loop actually touches (``wait()`` and
``returncode``), or — for the signal arithmetic itself — a real short-lived
Python process the test signals for real.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from plugins.dbview.supervisor import NodeSupervisor, SupervisorConfig

_SIGTERM_EXIT = -signal.SIGTERM


class _FakeChild:
    """Minimal stand-in for the pieces of the child the loop reads."""

    def __init__(self, exit_code: int | None = None, *, hang: bool = False) -> None:
        self.pid = 4242
        self.returncode: int | None = None
        self._exit_code = exit_code
        self._hang = hang

    async def wait(self) -> int:
        if self._hang:  # a child that stays up: the loop times out and probes
            await asyncio.Event().wait()
        assert self._exit_code is not None
        self.returncode = self._exit_code
        return self._exit_code


def _supervisor(tmp_path: Path, **kwargs: float) -> NodeSupervisor:
    timings: dict[str, float] = {
        "health_probe_interval_s": 0.05,
        "restart_backoff_initial_s": 0.01,
    }
    timings.update(kwargs)
    cfg = SupervisorConfig(
        plugin_dir=tmp_path,
        dbview_root=tmp_path / "dbview",
        **timings,  # type: ignore[arg-type]
    )
    sup = NodeSupervisor(cfg)
    sup._port = 4242
    sup._healthy = True
    return sup


async def test_keepalive_does_not_restart_when_sigterm_precedes_a_host_stop(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """SIGTERM + a stop() right after = coordinated shutdown, not a crash."""
    sup = _supervisor(tmp_path, sigterm_settle_s=1.0)
    sup._process = _FakeChild(_SIGTERM_EXIT)  # type: ignore[assignment]

    with (
        patch.object(sup, "_spawn", new=AsyncMock()) as spawn,
        patch.object(sup, "_wait_for_health", new=AsyncMock()),
    ):
        with caplog.at_level(logging.ERROR, logger="plugins.dbview.supervisor.process"):
            task = asyncio.create_task(sup._keepalive_loop())
            # Let the loop observe the exit and enter the settle window before
            # the lifespan's stop() lands — that ordering is the whole bug.
            await asyncio.sleep(0.1)
            sup._stopped.set()
            await asyncio.wait_for(task, timeout=2.0)

    assert spawn.await_count == 0, "a coordinated shutdown must not respawn the child"
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR], (
        "an orderly shutdown must not be reported as an unexpected exit"
    )
    assert sup.is_healthy() is False


async def test_keepalive_restarts_when_sigterm_is_not_a_host_stop(
    tmp_path: Path,
) -> None:
    """A stray SIGTERM with the host still running is still a restart case."""
    sup = _supervisor(tmp_path, sigterm_settle_s=0.05)
    sup._process = _FakeChild(_SIGTERM_EXIT)  # type: ignore[assignment]
    spawned = asyncio.Event()

    async def fake_spawn() -> None:
        sup._process = _FakeChild(hang=True)  # type: ignore[assignment]
        spawned.set()

    with (
        patch.object(sup, "_spawn", new=fake_spawn),
        patch.object(sup, "_wait_for_health", new=AsyncMock()),
        patch.object(sup, "_probe_health", new=AsyncMock(return_value=True)),
    ):
        task = asyncio.create_task(sup._keepalive_loop())
        try:
            await asyncio.wait_for(spawned.wait(), timeout=2.0)
        finally:
            sup._stopped.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    assert spawned.is_set()


async def test_keepalive_classifies_a_real_os_sigterm_as_a_coordinated_stop(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """End-to-end on the signal itself: a real child, a real ``SIGTERM``.

    The fake-child tests assert the branch; this one asserts the arithmetic —
    that the exit code the kernel reports for a ``SIGTERM``-ed child is the
    value the loop compares against.
    """
    sup = _supervisor(tmp_path, sigterm_settle_s=1.0)
    child = await asyncio.create_subprocess_exec(
        sys.executable, "-c", "import time; time.sleep(30)"
    )
    sup._process = child  # type: ignore[assignment]

    with (
        patch.object(sup, "_spawn", new=AsyncMock()) as spawn,
        patch.object(sup, "_wait_for_health", new=AsyncMock()),
        patch.object(sup, "_probe_health", new=AsyncMock(return_value=True)),
    ):
        with caplog.at_level(logging.ERROR, logger="plugins.dbview.supervisor.process"):
            task = asyncio.create_task(sup._keepalive_loop())
            await asyncio.sleep(0.05)
            child.terminate()  # what systemd/docker send to the whole group
            await asyncio.sleep(0.2)
            sup._stopped.set()  # the lifespan's shutdown, arriving late
            await asyncio.wait_for(task, timeout=3.0)

    assert child.returncode == _SIGTERM_EXIT
    assert spawn.await_count == 0
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


async def test_keepalive_skips_the_respawn_when_stop_lands_during_the_backoff(
    tmp_path: Path,
) -> None:
    """A crash (non-SIGTERM) racing a shutdown must not respawn either."""
    sup = _supervisor(tmp_path, restart_backoff_initial_s=0.3)
    sup._process = _FakeChild(1)  # type: ignore[assignment]

    with (
        patch.object(sup, "_spawn", new=AsyncMock()) as spawn,
        patch.object(sup, "_wait_for_health", new=AsyncMock()),
    ):
        task = asyncio.create_task(sup._keepalive_loop())
        await asyncio.sleep(0.05)  # loop is inside the backoff sleep
        sup._stopped.set()
        await asyncio.wait_for(task, timeout=2.0)

    assert spawn.await_count == 0, "stop() during the backoff must cancel the respawn"
