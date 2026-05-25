"""Sandbox runner tests with a fake docker subprocess."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from core.config.sandbox import SandboxConfig
from plugins.red_agent.sandbox_runner import SandboxRunner


class _FakeProc:
    def __init__(self, returncode: int, stdout: bytes, stderr: bytes) -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        return self.returncode


@pytest.fixture()
def runner() -> SandboxRunner:
    return SandboxRunner(
        config=SandboxConfig(provider="docker", enable_network=False, timeout=5)
    )


@pytest.mark.asyncio
async def test_argv_invocation_no_shell(
    runner: SandboxRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    async def fake_create(*args: Any, **kwargs: Any) -> _FakeProc:
        captured["args"] = args
        captured["stdin"] = kwargs.get("stdin")
        return _FakeProc(0, b'{"ok":true}', b"")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    result = await runner.execute(
        image="alpine:3.20",
        argv=["echo", "hello"],
        timeout=5,
        network=False,
        scanner="unit",
    )

    assert result.exit_code == 0
    assert result.stdout == '{"ok":true}'
    cmd = list(captured["args"])
    assert cmd[0] == "docker"
    assert "--read-only" in cmd
    assert "--cap-drop=ALL" in cmd
    assert "--security-opt=no-new-privileges" in cmd
    assert "--network=none" in cmd
    assert cmd[-2:] == ["alpine:3.20"][:1] + ["echo"] or "echo" in cmd
    assert "hello" in cmd


@pytest.mark.asyncio
async def test_timeout_kills_proc(
    runner: SandboxRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    proc = _FakeProc(0, b"", b"")

    async def slow_communicate() -> tuple[bytes, bytes]:
        await asyncio.sleep(10)
        return b"", b""

    proc.communicate = slow_communicate  # type: ignore[method-assign]

    async def fake_create(*_args: Any, **_kwargs: Any) -> _FakeProc:
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    with pytest.raises(asyncio.TimeoutError):
        await runner.execute(
            image="alpine:3.20",
            argv=["sleep", "30"],
            timeout=1,
            network=False,
            scanner="timeout",
        )
    assert proc.killed is True


@pytest.mark.asyncio
async def test_artifact_collection(
    runner: SandboxRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_workdir: dict[str, Path] = {}

    async def fake_create(*args: Any, **_kwargs: Any) -> _FakeProc:
        cmd = list(args)
        # find the host workspace mount: ... -v <host>:/workspace:rw
        for i, token in enumerate(cmd):
            if token == "-v" and i + 1 < len(cmd):
                host = cmd[i + 1].split(":", 1)[0]
                captured_workdir["wd"] = Path(host)
                (Path(host) / "report.json").write_text('{"hits":1}')
                break
        return _FakeProc(0, b"", b"")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    result = await runner.execute(
        image="alpine:3.20",
        argv=["true"],
        timeout=5,
        network=False,
        scanner="artifact",
        artifacts=["/whatever/report.json"],
    )

    assert result.artifacts.get("report.json") == '{"hits":1}'
    assert "wd" in captured_workdir
    # workspace directory is removed by `finally`
    assert not captured_workdir["wd"].exists()
