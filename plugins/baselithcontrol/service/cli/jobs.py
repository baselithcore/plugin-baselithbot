"""Dev-tool jobs: ``test`` / ``lint`` / ``docs`` as streamed subprocesses.

These CLI commands shell out to pytest / ruff+mypy / the OpenAPI exporter, so
they are run as isolated child processes (``python -m core.cli <cmd>``) rather
than imported in-process — that captures their full output cleanly and never
blocks the event loop. Output is streamed line-by-line into a bounded ring
buffer; the dashboard polls job state while a job runs.

One job per kind runs at a time; finished jobs are retained (bounded) so their
output stays inspectable.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import time
import uuid
from asyncio import subprocess as aiosp
from collections import OrderedDict, deque
from pathlib import Path
from typing import Any

from core.observability.logging import get_logger

from ...cli_models import JobView

logger = get_logger(__name__)

# Kind → CLI argv (after the ``baselith`` entrypoint).
_KINDS: dict[str, list[str]] = {
    "test": ["test", "-v"],
    "lint": ["lint"],
    "docs": ["docs", "generate"],
}
_MAX_LINES = 600
_MAX_JOBS = 20
# Hard wall-clock cap: a wedged tool (e.g. a hung pytest) must not run forever
# nor block its kind indefinitely. Generous — real test suites can be slow.
_JOB_TIMEOUT_SECONDS = 900.0
_READ_CHUNK = 65536
# A single output line this long is flushed as-is rather than buffered further,
# so a tool spewing one gigantic line can never balloon memory.
_MAX_LINE_BYTES = 64 * 1024


def _decode(raw: bytes) -> str:
    """Decode one output line, tolerant of invalid UTF-8 and trailing CR/LF."""
    return raw.decode("utf-8", errors="replace").rstrip("\r\n")


def _entrypoint(args: list[str]) -> list[str]:
    """Build the subprocess argv for the ``baselith`` CLI.

    Prefer the ``baselith`` console script that sits next to the running
    interpreter (canonical, no ``runpy`` warning); fall back to ``python -m
    core.cli`` with warnings silenced. Either way the CLI runs in the *same*
    environment as the server, so dev tools reflect the app's real deps.
    """
    script = Path(sys.executable).with_name("baselith")
    if script.exists():
        return [str(script), *args]
    return [sys.executable, "-W", "ignore", "-m", "core.cli", *args]


def _missing_tool_hint(kind: str, lines: list[str]) -> str | None:
    """Return a friendly hint if a job failed because a dev dep is absent."""
    if any("No module named" in line or "not installed" in line for line in lines):
        env = Path(sys.executable).parent.parent.name
        return (
            f"[control] hint: the '{kind}' tool is not installed in the server "
            f"environment ('{env}'). Install dev deps there "
            f'(e.g. uv pip install -e ".[dev]") or run the backend from a venv '
            f"that has pytest/ruff/mypy."
        )
    return None


class _Job:
    """In-memory record of a single dev-tool subprocess run."""

    def __init__(self, kind: str, command: str) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.command = command
        self.status = "running"
        self.exit_code: int | None = None
        self.started_at = time.time()
        self.ended_at: float | None = None
        self.lines: deque[str] = deque(maxlen=_MAX_LINES)
        self.task: asyncio.Task[None] | None = None

    def view(self) -> JobView:
        duration = (self.ended_at - self.started_at) if self.ended_at else None
        return JobView(
            id=self.id,
            kind=self.kind,
            status=self.status,
            running=self.status == "running",
            exit_code=self.exit_code,
            started_at=round(self.started_at, 3),
            ended_at=round(self.ended_at, 3) if self.ended_at else None,
            duration=round(duration, 3) if duration is not None else None,
            command=self.command,
            output="\n".join(self.lines),
        )


class JobManager:
    """Tracks dev-tool subprocess jobs for the lifetime of the process."""

    def __init__(self) -> None:
        self._jobs: "OrderedDict[str, _Job]" = OrderedDict()
        self._lock = asyncio.Lock()

    @staticmethod
    def kinds() -> tuple[str, ...]:
        return tuple(_KINDS)

    async def start(self, kind: str) -> JobView:
        """Start (or return the already-running) job for ``kind``."""
        if kind not in _KINDS:
            raise ValueError(f"unknown dev-tool kind: {kind}")
        async with self._lock:
            for job in self._jobs.values():
                if job.kind == kind and job.status == "running":
                    return job.view()
            argv = _entrypoint(_KINDS[kind])
            job = _Job(kind, "baselith " + " ".join(_KINDS[kind]))
            self._jobs[job.id] = job
            self._trim()
            job.task = asyncio.create_task(self._run(job, argv))
            return job.view()

    async def _run(self, job: _Job, argv: list[str]) -> None:
        proc: aiosp.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(Path.cwd()),
                stdout=aiosp.PIPE,
                stderr=aiosp.STDOUT,
                # Own process group so a timeout can kill the *whole* tree
                # (pytest spawns children); no-op flag on platforms lacking it.
                start_new_session=True,
            )
            # Bound the whole run: a wedged tool must not run forever or block
            # its kind. On timeout the tree is killed and the job marked so.
            await asyncio.wait_for(self._pump(proc, job), timeout=_JOB_TIMEOUT_SECONDS)
            return_code = proc.returncode if proc.returncode is not None else -1
            job.exit_code = return_code
            job.status = "succeeded" if return_code == 0 else "failed"
            if return_code != 0:
                hint = _missing_tool_hint(job.kind, list(job.lines))
                if hint:
                    job.lines.append(hint)
        except asyncio.TimeoutError:
            job.status = "timeout"
            job.lines.append(
                f"[control] aborted: exceeded {_JOB_TIMEOUT_SECONDS:.0f}s time limit"
            )
            await self._terminate(proc)
        except Exception as exc:  # noqa: BLE001 — record failure into the job
            job.status = "error"
            job.lines.append(f"[control] failed to run: {exc}")
            await self._terminate(proc)
        finally:
            job.ended_at = time.time()

    async def _pump(self, proc: aiosp.Process, job: _Job) -> None:
        """Stream combined output into the ring, then await process exit.

        Reads fixed-size chunks and splits on newlines rather than
        ``StreamReader.readline`` so a single very long line can never raise
        ``LimitOverrunError`` (which would abandon a still-running child).
        """
        stream = proc.stdout
        if stream is not None:
            buf = b""
            while True:
                chunk = await stream.read(_READ_CHUNK)
                if not chunk:
                    if buf:
                        job.lines.append(_decode(buf))
                    break
                buf += chunk
                while b"\n" in buf:
                    line, _, buf = buf.partition(b"\n")
                    job.lines.append(_decode(line))
                if len(buf) >= _MAX_LINE_BYTES:  # flush an unbounded single line
                    job.lines.append(_decode(buf))
                    buf = b""
        await proc.wait()

    @staticmethod
    async def _terminate(proc: aiosp.Process | None) -> None:
        """Best-effort kill of the subprocess tree (never raises)."""
        if proc is None or proc.returncode is not None:
            return
        try:
            killpg = getattr(os, "killpg", None)
            getpgid = getattr(os, "getpgid", None)
            if killpg is not None and getpgid is not None:
                killpg(getpgid(proc.pid), signal.SIGKILL)  # whole tree
            else:  # pragma: no cover — non-POSIX fallback
                proc.kill()
            await proc.wait()
        except (ProcessLookupError, PermissionError):
            pass
        except Exception as exc:  # noqa: BLE001 — cleanup must never raise
            logger.warning("dev-tool job kill failed: %s", exc)

    def _trim(self) -> None:
        """Drop the oldest finished jobs once over capacity."""
        while len(self._jobs) > _MAX_JOBS:
            for jid, job in list(self._jobs.items()):
                if job.status != "running":
                    del self._jobs[jid]
                    break
            else:
                break

    def get(self, job_id: str) -> JobView | None:
        job = self._jobs.get(job_id)
        return job.view() if job else None

    def list(self) -> list[JobView]:
        return [job.view() for job in reversed(self._jobs.values())]


def get_job_manager(app: Any) -> JobManager:
    """Return the process-wide job manager, creating it on first use."""
    manager = getattr(app.state, "baselithcontrol_jobs", None)
    if not isinstance(manager, JobManager):
        manager = JobManager()
        app.state.baselithcontrol_jobs = manager
    return manager


__all__ = ["JobManager", "get_job_manager"]
