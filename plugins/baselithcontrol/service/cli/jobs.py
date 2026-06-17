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
import sys
import time
import uuid
from asyncio import subprocess as aiosp
from collections import OrderedDict, deque
from pathlib import Path
from typing import Any

from ...cli_models import JobView

# Kind → CLI argv (after the ``baselith`` entrypoint).
_KINDS: dict[str, list[str]] = {
    "test": ["test", "-v"],
    "lint": ["lint"],
    "docs": ["docs", "generate"],
}
_MAX_LINES = 600
_MAX_JOBS = 20


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
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(Path.cwd()),
                stdout=aiosp.PIPE,
                stderr=aiosp.STDOUT,
            )
            stream = proc.stdout
            if stream is not None:
                async for raw in stream:
                    job.lines.append(raw.decode("utf-8", errors="replace").rstrip("\n"))
            return_code = await proc.wait()
            job.exit_code = return_code
            job.status = "succeeded" if return_code == 0 else "failed"
            if return_code != 0:
                hint = _missing_tool_hint(job.kind, list(job.lines))
                if hint:
                    job.lines.append(hint)
        except Exception as exc:  # noqa: BLE001 — record failure into the job
            job.status = "error"
            job.lines.append(f"[control] failed to run: {exc}")
        finally:
            job.ended_at = time.time()

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
