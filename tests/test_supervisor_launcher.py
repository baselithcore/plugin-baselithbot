"""The child launcher's two pre-exec guarantees, exercised for real.

Both are properties of an actual process tree, so these tests spawn one rather
than assert on mocks:

* descriptors above stdio are closed before ``execvp`` — the host's API
  listening socket is deliberately inheritable so ``uvicorn`` can hand it to
  forked workers, and libuv (``uvloop``) passes every such descriptor straight
  through to the Node child. An orphan holding it pins the *public* API port;
* the child dies with its parent (Linux ``PR_SET_PDEATHSIG``) — the only
  mechanism that still works when the parent is ``SIGKILL``ed and never gets
  to run the supervisor's shutdown.

The spawns use ``close_fds=False`` on purpose: that is what libuv effectively
does, and it is the condition the launcher has to repair.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import textwrap
import time

import pytest

from plugins.dbview.supervisor import launcher as _launcher
from plugins.dbview.supervisor.launcher import build_launch_argv

LAUNCHER = _launcher.__file__

_LINUX_ONLY = pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="PR_SET_PDEATHSIG is a Linux facility",
)


def test_build_launch_argv_wraps_the_command_behind_a_separator() -> None:
    argv = build_launch_argv(["node", "/srv/dist/main.js"])
    assert argv[0] == sys.executable
    assert argv[1].endswith("launcher.py")
    assert argv[2:] == [
        "--parent",
        str(os.getpid()),
        "--",
        "node",
        "/srv/dist/main.js",
    ]


def test_a_parent_of_pid_1_is_not_an_orphan(monkeypatch) -> None:
    """The bug this flag exists for.

    In a container the application is pid 1 — the image runs uvicorn as the
    entrypoint — so the launcher's parent legitimately *is* init. The old check
    read that as "I have been orphaned" and called ``os._exit(0)`` before exec:
    every dbview Node child died instantly, with exit code 0 and no output, in
    every containerised deployment, and the supervisor could only report "child
    exited during startup".
    """
    exits: list[int] = []
    monkeypatch.setattr(_launcher.os, "getppid", lambda: 1)
    monkeypatch.setattr(_launcher.os, "_exit", lambda code: exits.append(code))

    _launcher._exit_if_orphaned(1)
    assert exits == []


def test_a_parent_that_changed_is_an_orphan(monkeypatch) -> None:
    """The property the check is actually for: a parent that died before the
    death signal was armed leaves an orphan pinning the rendezvous port."""
    exits: list[int] = []
    monkeypatch.setattr(_launcher.os, "getppid", lambda: 1)
    monkeypatch.setattr(_launcher.os, "_exit", lambda code: exits.append(code))

    _launcher._exit_if_orphaned(4242)
    assert exits == [0]


def test_the_command_runs_under_its_real_parent() -> None:
    """End to end: the spawner's pid is what build_launch_argv passes."""
    result = subprocess.run(
        [
            sys.executable,
            LAUNCHER,
            "--parent",
            str(os.getpid()),
            "--",
            sys.executable,
            "-c",
            "print('exec happened')",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "exec happened" in result.stdout


def test_the_command_does_not_run_when_the_parent_is_gone() -> None:
    result = subprocess.run(
        [
            sys.executable,
            LAUNCHER,
            "--parent",
            "4242",
            "--",
            sys.executable,
            "-c",
            "print('exec happened')",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "exec happened" not in result.stdout


def test_a_launcher_run_by_hand_still_execs() -> None:
    """Without the flag the check is skipped, not guessed at."""
    result = subprocess.run(
        [sys.executable, LAUNCHER, "--", sys.executable, "-c", "print('by hand')"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "by hand" in result.stdout


def test_launcher_closes_descriptors_inherited_from_the_host() -> None:
    """An inheritable listening socket must not reach the command."""
    # A fixed, otherwise-unused descriptor makes the assertion exact: the probe
    # looks for *that* number rather than guessing which fd a socket landed on.
    leaked_fd = 60
    probe = textwrap.dedent(
        f"""
        import os, stat
        try:
            print(stat.S_ISSOCK(os.fstat({leaked_fd}).st_mode))
        except OSError:
            print(False)
        """
    )
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 0))
        sock.listen(5)
        os.dup2(sock.fileno(), leaked_fd, inheritable=True)
        direct = subprocess.run(  # noqa: S603 — fixed argv, no shell
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            close_fds=False,
            check=True,
        )
        wrapped = subprocess.run(  # noqa: S603 — fixed argv, no shell
            build_launch_argv([sys.executable, "-c", probe]),
            capture_output=True,
            text=True,
            close_fds=False,
            check=True,
        )
    finally:
        os.close(leaked_fd)
        sock.close()

    # The unwrapped spawn is the control: it proves this platform really does
    # leak the descriptor, so the wrapped assertion below means something.
    assert direct.stdout.strip() == "True", "control spawn did not leak the socket"
    assert wrapped.stdout.strip() == "False"


@_LINUX_ONLY
def test_launcher_kills_the_command_when_its_parent_is_killed() -> None:
    """A SIGKILLed parent must not leave the child holding the port."""
    parent_source = textwrap.dedent(
        f"""
        import subprocess, sys, time
        argv = {build_launch_argv([sys.executable, "-c", "import time; time.sleep(60)"])!r}
        child = subprocess.Popen(argv)
        print(child.pid, flush=True)
        time.sleep(60)
        """
    )
    parent = subprocess.Popen(  # noqa: S603 — fixed argv, no shell
        [sys.executable, "-c", parent_source], stdout=subprocess.PIPE, text=True
    )
    try:
        assert parent.stdout is not None
        grandchild_pid = int(parent.stdout.readline().strip())
        # Let the launcher reach its prctl() before the parent disappears.
        time.sleep(1.0)
        parent.kill()
        parent.wait(timeout=10)

        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if not os.path.exists(f"/proc/{grandchild_pid}"):
                return
            time.sleep(0.1)
        pytest.fail(f"pid {grandchild_pid} outlived the parent it was tied to")
    finally:
        if parent.poll() is None:  # pragma: no cover — defensive cleanup
            parent.kill()
