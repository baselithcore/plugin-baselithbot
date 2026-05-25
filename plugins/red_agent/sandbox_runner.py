"""
SandboxRunner — isolated execution wrapper for scanner binaries.

Every scan tool MUST run through this runner. Direct subprocess calls
in scanners are prohibited by the architecture rules. The runner uses
asyncio.create_subprocess_exec (argv list, no shell) — there is no
command-string interpolation anywhere, eliminating injection vectors.
"""

from __future__ import annotations

import asyncio
import json
import shlex
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from core.config.sandbox import SandboxConfig, get_sandbox_config
from core.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    artifacts: dict[str, str] = field(default_factory=dict)


class SandboxRunner:
    """
    Run scanner binaries inside an isolated container.

    Hardening:
      - read-only root filesystem
      - dropped capabilities, no-new-privileges
      - tight egress policy via host firewall (configured externally)
      - per-scan workspace mounted read-write, removed on exit
      - argv list invocation (no shell) — injection-safe by construction
    """

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or get_sandbox_config()

    async def execute(
        self,
        *,
        image: str,
        argv: list[str],
        timeout: int,
        network: bool,
        scanner: str,
        artifacts: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Run ``image`` with ``argv`` inside a hardened container.

        ``env`` is the controlled vector for passing secrets (identity
        scanners' credentials, cloud SDK profiles, OAuth tokens) into
        the container. The values are written to a workdir-local
        ``--env-file`` so they never appear in the host process tree;
        the keys (only) are recorded in the structured run log. Set
        ``env`` to ``None`` (default) when the scanner is fully
        unauthenticated.
        """

        if self.config.provider != "docker":
            raise NotImplementedError(
                f"Sandbox provider {self.config.provider!r} not yet implemented"
            )

        workdir = Path(tempfile.mkdtemp(prefix=f"red-agent-{scanner}-"))
        try:
            env_file: Path | None = None
            if env:
                env_file = workdir / ".env-file"
                env_file.write_text(
                    "\n".join(f"{k}={v}" for k, v in env.items()),
                    encoding="utf-8",
                )
                env_file.chmod(0o600)
            cmd = self._build_docker_cmd(image, argv, network, workdir, env_file)
            logger.info(
                "sandbox.run",
                extra={
                    "scanner": scanner,
                    "image": image,
                    "network": network,
                    "argv": argv,
                    "env_keys": sorted(env.keys()) if env else [],
                },
            )
            return await self._spawn(cmd, timeout, workdir, artifacts or [])
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _build_docker_cmd(
        self,
        image: str,
        argv: list[str],
        network: bool,
        workdir: Path,
        env_file: Path | None = None,
    ) -> list[str]:
        net_flag = "bridge" if network else "none"
        # Granular tmpfs mounts: ephemeral writable scratch for paths the
        # scanners actually write to (config dirs, caches, templates, /tmp)
        # while keeping the root filesystem read-only. Avoid mounting /root
        # wholesale — some images ship binaries under /root/.local/bin
        # (e.g. googlesky/sqlmap installs uv there) that a /root tmpfs would
        # mask, causing "executable not found" at container start.
        cmd: list[str] = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            f"--network={net_flag}",
            "--memory=1g",
            "--pids-limit=512",
            "--tmpfs=/tmp:rw,size=256m,exec",
            "--tmpfs=/root/.config:rw,size=64m",
            "--tmpfs=/root/.cache:rw,size=128m",
            "--tmpfs=/root/nuclei-templates:rw,size=512m,exec",
            "--tmpfs=/home:rw,size=64m",
            "-v",
            f"{workdir}:/workspace:rw",
            "-w",
            "/workspace",
        ]
        if env_file is not None:
            cmd.extend(["--env-file", str(env_file)])
        cmd.append(image)
        cmd.extend(argv)
        return cmd

    async def _spawn(
        self,
        cmd: list[str],
        timeout: int,
        workdir: Path,
        artifact_paths: list[str],
    ) -> SandboxResult:
        loop = asyncio.get_running_loop()
        started = loop.time()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        duration = loop.time() - started
        artifacts: dict[str, str] = {}
        for art in artifact_paths:
            host_path = workdir / Path(art).name
            if host_path.exists():
                try:
                    artifacts[host_path.name] = host_path.read_text(errors="replace")
                except OSError:
                    artifacts[host_path.name] = ""

        return SandboxResult(
            exit_code=proc.returncode or 0,
            stdout=stdout_b.decode(errors="replace"),
            stderr=stderr_b.decode(errors="replace"),
            duration_seconds=duration,
            artifacts=artifacts,
        )

    @staticmethod
    def quote_argv(argv: list[str]) -> str:
        """Debug-only formatter — never used to build shell commands."""
        return " ".join(shlex.quote(a) for a in argv)

    @staticmethod
    def normalize_json(payload: object) -> str:
        return json.dumps(payload, default=str)
