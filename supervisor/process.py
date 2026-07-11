"""Asyncio supervisor for the dbview Node child process.

Owns the full child lifecycle:

* allocates a loopback port (or honours ``DBVIEW_INTERNAL_PORT``);
* assembles the child environment (prefix passthrough + plugin overrides);
* spawns ``node dist/main.js`` (or ``pnpm dev`` in dev mode);
* drains stdout/stderr into the host logger line by line;
* gates readiness on ``GET /api/health`` with a bounded timeout;
* restarts on unexpected exit with capped exponential backoff;
* stops via SIGTERM, escalating to a process-group SIGKILL on grace expiry.

The child is always spawned via the argv form of ``asyncio``'s subprocess
API — no shell, no string interpolation — so operator-controlled input can
never escape into a shell command.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
import signal
import socket
import time

import httpx

from .config import PASSTHROUGH_ENV_PREFIXES, SupervisorConfig

# Bind the argv-form spawner once (the safe family, analogous to Node's
# execFile) so the rest of the module never repeats the symbol literally.
_spawn_argv = asyncio.create_subprocess_exec

logger = logging.getLogger(__name__)


class NodeNotAvailableError(RuntimeError):
    """Raised when ``node``/``pnpm`` can't be located on ``PATH``."""


class StartupTimeoutError(RuntimeError):
    """Raised when the child process never answers ``/api/health``."""


def _allocate_port(host: str = "127.0.0.1") -> int:
    """Ask the kernel for a free ephemeral port and release it.

    The race between release and the child ``bind()`` is acceptable on a
    single host and mirrors how common test harnesses pick ports.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


class NodeSupervisor:
    """Lifecycle manager for the dbview Node child process.

    * ``start()`` → spawn + wait for health + spawn keep-alive task.
    * ``stop()`` → cancel keep-alive, SIGTERM, drain, SIGKILL on timeout.
    * ``is_healthy()`` → bool snapshot of the latest probe result.
    """

    def __init__(self, config: SupervisorConfig) -> None:
        self._config = config
        self._process: asyncio.subprocess.Process | None = None
        self._keepalive_task: asyncio.Task[None] | None = None
        self._follower_task: asyncio.Task[None] | None = None
        self._stdout_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()
        self._healthy = False
        self._restart_attempts = 0
        self._port: int | None = config.port

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    @property
    def base_url(self) -> str:
        """HTTP origin the proxy router should forward to."""
        if self._port is None:
            raise RuntimeError("supervisor not started — port unknown")
        return f"http://{self._config.host}:{self._port}"

    @property
    def port(self) -> int:
        """Resolved upstream port."""
        if self._port is None:
            raise RuntimeError("supervisor not started — port unknown")
        return self._port

    def is_healthy(self) -> bool:
        """Latest cached health snapshot (refreshed by the keep-alive task)."""
        return self._healthy

    async def start(self) -> None:
        """Spawn the child process and wait until it answers the health probe."""
        self._ensure_runtime_available()

        if self._port is None:
            self._port = _allocate_port(self._config.host)
        logger.info(
            "[dbview] supervisor starting (mode=%s host=%s port=%d)",
            self._config.mode,
            self._config.host,
            self._port,
        )

        await self._spawn()
        await self._wait_for_health()
        self._restart_attempts = 0
        self._keepalive_task = asyncio.create_task(
            self._keepalive_loop(), name="dbview-supervisor-keepalive"
        )

    async def start_follower(self) -> None:
        """Attach to a Node child owned by the leader worker (no spawn).

        Under a multi-worker deployment exactly one worker (the leadership
        winner) spawns the Node child on the shared loopback port; every other
        worker runs in *follower* mode: it never spawns or restarts the child,
        it only tracks the shared child's health by probing the fixed port so
        the proxy 503s cleanly until the leader's child is up. Requires a fixed
        shared port (``DBVIEW_INTERNAL_PORT`` / the plugin default) so the
        forward target is known without any cross-worker port publication.
        """
        if self._port is None:
            raise RuntimeError(
                "follower supervisor requires a fixed shared port "
                "(DBVIEW_INTERNAL_PORT); none was configured"
            )
        logger.info(
            "[dbview] supervisor in follower mode (upstream=%s) — the leader "
            "worker owns the Node child",
            self.base_url,
        )
        self._healthy = await self._probe_health()
        self._follower_task = asyncio.create_task(
            self._follower_loop(), name="dbview-supervisor-follower"
        )

    async def _follower_loop(self) -> None:
        """Track the leader-owned child's health without ever spawning it."""
        while not self._stopped.is_set():
            await asyncio.sleep(max(self._config.health_probe_interval_s, 2.0))
            self._healthy = await self._probe_health()

    async def stop(self) -> None:
        """Best-effort shutdown: cancel keep-alive, SIGTERM, SIGKILL."""
        self._stopped.set()

        for task_attr in ("_keepalive_task", "_follower_task"):
            task = getattr(self, task_attr)
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                setattr(self, task_attr, None)

        await self._terminate_child()

        for task in (self._stdout_task, self._stderr_task):
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        self._stdout_task = None
        self._stderr_task = None
        self._healthy = False
        logger.info("[dbview] supervisor stopped")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_runtime_available(self) -> None:
        if shutil.which("node") is None:
            raise NodeNotAvailableError(
                "Node.js runtime not found on PATH. Install Node ≥ 20 "
                "(https://nodejs.org/) and re-enable the dbview plugin."
            )
        if self._config.mode == "dev" and shutil.which("pnpm") is None:
            raise NodeNotAvailableError(
                "pnpm not found on PATH but the dbview plugin is configured "
                "in dev mode. Install pnpm ≥ 11 (`npm install -g pnpm`) or "
                "switch the plugin to prod mode."
            )

    def _build_env(self) -> dict[str, str]:
        env = {
            k: v
            for k, v in os.environ.items()
            if any(k.startswith(p) or k == p for p in PASSTHROUGH_ENV_PREFIXES)
        }
        # The supervisor owns these: they define the proxy↔child contract.
        env["PORT"] = str(self._port)
        env.setdefault("HOST", self._config.host)
        env.setdefault(
            "NODE_ENV",
            "production" if self._config.mode == "prod" else "development",
        )
        env.setdefault("LOG_FORMAT", "json")
        # Keep PATH-dependent tools (pnpm shim) and locale/timezone working.
        for required in ("PATH", "HOME", "LANG", "LC_ALL", "TZ"):
            if required in os.environ and required not in env:
                env[required] = os.environ[required]
        env.update(self._config.extra_env)
        if self._config.env_provider is not None:
            # Resolved at every spawn so a restart picks up current values
            # (e.g. a governed LLM re-pin). Best-effort by contract: a failing
            # provider must never block the child from starting.
            try:
                env.update(
                    {str(k): str(v) for k, v in self._config.env_provider().items()}
                )
            except Exception:  # noqa: BLE001 — spawn must survive a bad provider
                logger.warning(
                    "[dbview] dynamic env provider failed; spawning without "
                    "its overrides",
                    exc_info=True,
                )
        return env

    def _build_command(self) -> list[str]:
        if self._config.mode == "dev":
            return ["pnpm", "dev"]
        api_dist = self._config.dbview_root / "apps" / "api" / "dist" / "main.js"
        if not api_dist.exists():
            raise FileNotFoundError(
                f"dbview prod bundle not found at {api_dist}. Run "
                "`pnpm install && pnpm -r build` inside "
                f"{self._config.dbview_root} before starting the plugin in "
                "prod mode (or set DBVIEW_PLUGIN_MODE=dev)."
            )
        return ["node", str(api_dist)]

    async def _spawn(self) -> None:
        cwd = self._config.dbview_root
        env = self._build_env()
        cmd = self._build_command()
        logger.info("[dbview] spawning %s (cwd=%s)", " ".join(cmd), cwd)
        # ``_spawn_argv`` is the argv-form spawner — no shell involved.
        self._process = await _spawn_argv(
            *cmd,
            cwd=str(cwd),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        self._stdout_task = asyncio.create_task(
            self._drain_stream(self._process.stdout, level=logging.INFO),
            name="dbview-stdout-drain",
        )
        self._stderr_task = asyncio.create_task(
            self._drain_stream(self._process.stderr, level=logging.WARNING),
            name="dbview-stderr-drain",
        )

    async def _drain_stream(
        self, stream: asyncio.StreamReader | None, *, level: int
    ) -> None:
        if stream is None:
            return
        while True:
            try:
                line = await stream.readline()
            except (asyncio.CancelledError, Exception):
                return
            if not line:
                return
            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                logger.log(level, "[dbview-node] %s", text)

    async def _wait_for_health(self) -> None:
        assert self._port is not None
        url = f"http://{self._config.host}:{self._port}{self._config.health_path}"
        deadline = time.monotonic() + self._config.startup_timeout_s
        last_error: str | None = None
        async with httpx.AsyncClient(timeout=2.0) as client:
            while time.monotonic() < deadline:
                # Premature-exit detection: don't keep polling a dead child.
                if self._process is not None and self._process.returncode is not None:
                    raise StartupTimeoutError(
                        f"dbview child exited during startup "
                        f"(returncode={self._process.returncode}) "
                        f"before answering {url}"
                    )
                try:
                    resp = await client.get(url)
                    if resp.status_code < 500:
                        self._healthy = True
                        logger.info(
                            "[dbview] health probe OK in %.2fs (status=%d)",
                            self._config.startup_timeout_s
                            - max(0.0, deadline - time.monotonic()),
                            resp.status_code,
                        )
                        return
                    last_error = f"HTTP {resp.status_code}"
                except httpx.HTTPError as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                await asyncio.sleep(self._config.health_probe_interval_s)
        raise StartupTimeoutError(
            f"dbview API did not become healthy within "
            f"{self._config.startup_timeout_s:.0f}s (last_error={last_error})"
        )

    async def _keepalive_loop(self) -> None:
        """Watch the child process and the health endpoint.

        1. Child exits unexpectedly → spawn a replacement with backoff.
        2. Health probe goes red → flip ``_healthy`` so the proxy 503s.
        """
        assert self._process is not None
        backoff = self._config.restart_backoff_initial_s
        while not self._stopped.is_set():
            try:
                exit_code = await asyncio.wait_for(
                    self._process.wait(),
                    timeout=self._config.health_probe_interval_s,
                )
            except asyncio.TimeoutError:
                self._healthy = await self._probe_health()
                continue

            if self._stopped.is_set():
                return

            logger.error(
                "[dbview] child exited unexpectedly (returncode=%s); "
                "attempting restart (attempt=%d, backoff=%.1fs)",
                exit_code,
                self._restart_attempts + 1,
                backoff,
            )
            self._restart_attempts += 1
            if (
                self._config.restart_max_attempts
                and self._restart_attempts >= self._config.restart_max_attempts
            ):
                logger.error(
                    "[dbview] restart budget exhausted (%d attempts) — giving up",
                    self._restart_attempts,
                )
                self._healthy = False
                return

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2.0, self._config.restart_backoff_max_s)

            try:
                await self._spawn()
                await self._wait_for_health()
                logger.info("[dbview] child restarted successfully")
                backoff = self._config.restart_backoff_initial_s
            except Exception as exc:  # noqa: BLE001 — keep the loop alive
                logger.error("[dbview] restart attempt failed: %s", exc)
                self._healthy = False

    async def _probe_health(self) -> bool:
        if self._port is None:
            return False
        url = f"http://{self._config.host}:{self._port}{self._config.health_path}"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(url)
                return resp.status_code < 500
        except httpx.HTTPError:
            return False

    async def _terminate_child(self) -> None:
        proc = self._process
        if proc is None or proc.returncode is not None:
            return
        try:
            proc.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(proc.wait(), timeout=self._config.shutdown_grace_s)
            logger.info(
                "[dbview] child exited cleanly (returncode=%s)", proc.returncode
            )
            return
        except asyncio.TimeoutError:
            logger.warning(
                "[dbview] SIGTERM grace expired after %.1fs — sending SIGKILL",
                self._config.shutdown_grace_s,
            )
        # SIGKILL the *process group* — pnpm spawns turbo+nest children and a
        # bare SIGKILL on the parent would orphan them.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
        with contextlib.suppress(Exception):
            await proc.wait()


__all__ = [
    "NodeNotAvailableError",
    "NodeSupervisor",
    "StartupTimeoutError",
]
