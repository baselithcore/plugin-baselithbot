"""Dev-tool job manager: streaming, completion, timeout-kill, overflow, dedup.

Exercises the real subprocess path via short ``python -c`` argv fed straight to
``JobManager._run`` (bypassing the fixed ``_KINDS`` map), so the robustness
logic — chunked reads, wall-clock timeout, process-group kill — is verified
against actual OS processes rather than mocks.
"""

from __future__ import annotations

import asyncio
import sys

import pytest

from plugins.baselithcontrol.service.cli import jobs as jobs_mod
from plugins.baselithcontrol.service.cli.jobs import JobManager, _Job


async def _drive(job: _Job, code: str) -> _Job:
    mgr = JobManager()
    await mgr._run(job, [sys.executable, "-c", code])
    return job


async def test_success_captures_output_and_exit_zero() -> None:
    job = _Job("test", "py")
    await _drive(job, "print('hello'); print('world')")
    assert job.status == "succeeded" and job.exit_code == 0
    assert "hello" in job.view().output and "world" in job.view().output


async def test_nonzero_exit_marks_failed() -> None:
    job = _Job("lint", "py")
    await _drive(job, "import sys; print('boom'); sys.exit(3)")
    assert job.status == "failed" and job.exit_code == 3
    assert "boom" in job.view().output


async def test_timeout_kills_tree_and_marks_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Shrink the wall-clock cap so a sleeping child trips it fast.
    monkeypatch.setattr(jobs_mod, "_JOB_TIMEOUT_SECONDS", 0.5)
    job = _Job("test", "py")
    started = asyncio.get_event_loop().time()
    await _drive(job, "import time; time.sleep(30)")
    elapsed = asyncio.get_event_loop().time() - started
    assert job.status == "timeout"
    assert elapsed < 10  # killed promptly, not after the full 30s sleep
    assert any("time limit" in ln for ln in job.lines)


async def test_huge_single_line_does_not_crash_or_balloon() -> None:
    # One line far larger than the read chunk must not raise LimitOverrunError
    # (the old readline path did) nor be dropped silently.
    job = _Job("docs", "py")
    await _drive(job, "print('x' * 500000)")
    assert job.status == "succeeded"
    assert len(job.view().output) > 0


async def test_start_dedups_running_job_by_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Two starts of the same kind while one runs → same job id (no double spawn).
    monkeypatch.setitem(jobs_mod._KINDS, "test", ["-c", "import time; time.sleep(1)"])
    monkeypatch.setattr(jobs_mod, "_entrypoint", lambda args: [sys.executable, *args])
    mgr = JobManager()
    first = await mgr.start("test")
    second = await mgr.start("test")
    assert first.id == second.id and first.running
    # let it finish so the loop doesn't leak a task
    await asyncio.sleep(1.5)
    assert mgr.get(first.id) is not None


async def test_trim_bounds_finished_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jobs_mod, "_MAX_JOBS", 3)
    monkeypatch.setattr(jobs_mod, "_entrypoint", lambda args: [sys.executable, *args])
    monkeypatch.setitem(jobs_mod._KINDS, "test", ["-c", "pass"])
    monkeypatch.setitem(jobs_mod._KINDS, "lint", ["-c", "pass"])
    monkeypatch.setitem(jobs_mod._KINDS, "docs", ["-c", "pass"])
    mgr = JobManager()
    for kind in ("test", "lint", "docs", "test", "lint"):
        await mgr.start(kind)
        await asyncio.sleep(0.15)  # let each finish before the next
    assert len(mgr.list()) <= 3


def test_unknown_kind_rejected() -> None:
    mgr = JobManager()
    with pytest.raises(ValueError):
        asyncio.get_event_loop().run_until_complete(mgr.start("nope"))
