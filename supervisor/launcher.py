"""Pre-exec hardening for the dbview Node child.

Two properties the plain :mod:`asyncio` spawn cannot give the supervisor on
its own, both of which have to be applied between ``fork()`` and ``execve()``:

* **the child must not outlive its supervisor.** ``uvicorn`` replaces a worker
  that misses its health check (``SIGKILL``, no lifespan, no
  :meth:`~plugins.dbview.supervisor.process.NodeSupervisor.stop`). The Node
  child it had spawned is detached in its own session, so nothing reaps it: it
  keeps the fixed rendezvous port, and the worker elected leader in its place
  can then never bind — every replacement child dies with ``EADDRINUSE``
  forever. ``prctl(PR_SET_PDEATHSIG)`` makes the kernel signal the child the
  moment its parent goes away, which is the only mechanism that survives a
  ``SIGKILL``ed parent.
* **the child must not inherit the host's descriptors.** The hosted API's
  listening socket is deliberately marked inheritable so ``uvicorn`` can hand
  it to forked workers; leaking it into the Node child means an orphan pins
  the *public* API port too, and the next ``systemctl restart`` fails to bind.

``preexec_fn`` is the usual seam for both, but the host runs on ``uvloop``,
whose libuv-backed spawn rejects it — and libuv is also what leaks the
descriptors in the first place (it rewires stdio and leaves every other
inheritable fd open, where :mod:`subprocess`' ``close_fds`` would have closed
them). So the supervisor execs this module instead: it applies both properties
and then ``execvp``s the real command **in the same pid**, so the supervisor's
``Process`` handle, its ``wait()`` and its process-group teardown all keep
referring to Node exactly as before.

Runnable standalone (``python launcher.py -- node dist/main.js``) and
therefore importing nothing from the plugin package.
"""

from __future__ import annotations

import os
import signal
import sys

__all__ = ["build_launch_argv"]

# ``<linux/prctl.h>``: PR_SET_PDEATHSIG. Linux-only; a no-op elsewhere.
_PR_SET_PDEATHSIG = 1

# 0/1/2 are the stdio the supervisor wired up on purpose; everything above is
# inherited noise that only libuv would have left open.
_FIRST_INHERITED_FD = 3

# Ceiling for the descriptor sweep when ``sysconf`` reports something absurd
# (or nothing at all) — one ``close_range`` syscall either way on Linux.
_MAX_FD_SWEEP = 1 << 20

_USAGE = "dbview child launcher: expected '-- <command> [args...]'"


def build_launch_argv(command: list[str]) -> list[str]:
    """Wrap ``command`` so it is exec'd through this launcher.

    Args:
        command: The argv the supervisor actually wants to run, e.g.
            ``["node", "/…/apps/api/dist/main.js"]``.

    Returns:
        An argv for :func:`asyncio.create_subprocess_exec`. The launcher
        ``execvp``s ``command`` in the same pid, so the caller's process
        handle still tracks the real child.
    """
    return [sys.executable, os.path.abspath(__file__), "--", *command]


def _detach_into_own_session() -> None:
    """Become a session leader so the supervisor can kill the whole group.

    ``pnpm`` (dev mode) spawns turbo + nest below us, and the supervisor's
    escalation path is ``killpg`` — which needs this process to lead its own
    group. Already-a-leader raises ``PermissionError`` (the spawner may have
    asked for ``start_new_session`` too); that is the desired state anyway.
    """
    try:
        os.setsid()
    except (PermissionError, OSError):
        return


def _request_parent_death_signal() -> None:
    """Ask the kernel to ``SIGTERM`` us when our parent dies (Linux only)."""
    if not sys.platform.startswith("linux"):
        return
    try:
        import ctypes

        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.prctl(_PR_SET_PDEATHSIG, int(signal.SIGTERM), 0, 0, 0)
    except Exception:  # noqa: BLE001 — hardening is best-effort, never fatal
        return


def _exit_if_already_orphaned() -> None:
    """Close the window between ``fork()`` and the ``prctl`` above.

    A parent that died in that window has already been reported to the kernel,
    so the death signal will never be delivered. Re-parenting to init is the
    observable trace of it: exit rather than become the orphan this launcher
    exists to prevent.
    """
    if os.getppid() == 1:
        os._exit(0)


def _close_inherited_descriptors() -> None:
    """Drop every descriptor above stdio before handing over to the command."""
    try:
        limit = os.sysconf("SC_OPEN_MAX")
    except (AttributeError, ValueError, OSError):
        limit = -1
    if limit < _FIRST_INHERITED_FD:
        limit = _MAX_FD_SWEEP
    os.closerange(_FIRST_INHERITED_FD, min(int(limit), _MAX_FD_SWEEP))


def _main(argv: list[str]) -> None:
    try:
        separator = argv.index("--")
    except ValueError:
        raise SystemExit(_USAGE) from None
    command = argv[separator + 1 :]
    if not command:
        raise SystemExit(_USAGE)

    _detach_into_own_session()
    _request_parent_death_signal()
    _exit_if_already_orphaned()
    _close_inherited_descriptors()
    os.execvp(command[0], command)


if __name__ == "__main__":  # pragma: no cover — exercised as a subprocess
    _main(sys.argv[1:])
