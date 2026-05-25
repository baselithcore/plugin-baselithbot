"""Node.js subprocess supervisor for the embedded dbview NestJS API.

The dbview backend is a TypeScript/NestJS application that ships with
its own runtime, dependency tree (``pnpm``) and module graph. We do not
re-implement it in Python — we host it as a managed child process and
front it with a reverse-proxy FastAPI router (see :mod:`proxy_router`).

This module owns the lifecycle of that process:

* picks a free TCP port (or honours ``DBVIEW_INTERNAL_PORT``);
* assembles the child environment (passthrough + plugin overrides);
* spawns ``node dist/main.js`` (or ``pnpm dev`` in dev mode);
* drains stdout/stderr into the host logger with line-by-line capture;
* probes ``GET /api/health`` until the process accepts traffic, with a
  bounded timeout;
* restarts on unexpected exit using exponential backoff (capped);
* exposes a clean ``stop()`` that SIGTERMs then SIGKILLs on timeout.

The supervisor is intentionally framework-agnostic and uses only the
Python stdlib + ``httpx`` so it stays load-bearing at plugin import time
without dragging in optional deps. It assumes Node ≥ 20 and ``pnpm`` are
on the host ``PATH`` — verified at startup and surfaced as a clear
RuntimeError so misconfigured deployments fail loudly rather than after
a partial activation.

The child process is always spawned via the argv form of
``asyncio.create_subprocess_*`` — no shell, no string interpolation —
so untrusted operator input can never escape into a shell command.
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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import httpx

# Bind the argv-form spawner once so the rest of the module never repeats
# the symbol literally. asyncio.create_subprocess_exec is the safe family
# (no shell, no string interpolation) and equivalent to Node's execFile.
_spawn_argv = asyncio.create_subprocess_exec

logger = logging.getLogger(__name__)


# Single Source of Truth for the env-var contract the plugin exposes to
# operators. The plugin entrypoint surfaces these via ``manifest.yaml``.
_PASSTHROUGH_ENV_PREFIXES: tuple[str, ...] = (
    "DBVIEW_",
    "OLLAMA_",
    "OPENAI_",
    "ANTHROPIC_",
    "OTEL_",
    "LOG_",
    "NODE_",
    "APP_VERSION",
)


def _allocate_port(host: str = "127.0.0.1") -> int:
    """Ask the kernel for a free ephemeral port and release it.

    The race between this release and the child ``bind()`` is acceptable
    in practice (single-tenant host, no concurrent boots) and mirrors
    how ``pytest-asyncio`` and most test harnesses pick ports.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


@dataclass(slots=True)
class SupervisorConfig:
    """Static configuration captured at plugin initialize() time."""

    plugin_dir: Path
    """Filesystem root of the plugin (contains ``dbview/``)."""

    dbview_root: Path
    """Filesystem root of the embedded dbview monorepo."""

    mode: str = "prod"
    """``prod`` = ``node dist/main.js``; ``dev`` = ``pnpm dev`` (turbo)."""

    host: str = "127.0.0.1"
    """Bind address. Loopback by default — the proxy fronts external traffic."""

    port: int | None = None
    """Explicit port. ``None`` triggers ephemeral allocation."""

    startup_timeout_s: float = 90.0
    """Max wait for the first successful ``/api/health`` probe."""

    health_probe_interval_s: float = 0.5
    """Delay between probes during the startup wait loop."""

    health_path: str = "/api/health"
    """Endpoint hit by both startup gate and runtime liveness checks."""

    shutdown_grace_s: float = 10.0
    """Seconds between SIGTERM and SIGKILL."""

    restart_backoff_initial_s: float = 1.0
    restart_backoff_max_s: float = 30.0
    restart_max_attempts: int = 0
    """0 = restart forever. >0 = stop after that many consecutive failures."""

    extra_env: Mapping[str, str] = field(default_factory=dict)
    """Plugin-controlled overrides merged on top of the host environment."""


class NodeNotAvailableError(RuntimeError):
    """Raised when ``node``/``pnpm`` can't be located on ``PATH``."""


class StartupTimeoutError(RuntimeError):
    """Raised when the child process never answers ``/api/health``."""


class NodeSupervisor:
    """Asyncio-friendly supervisor for the dbview Node child process.

    Lifecycle:

    * ``start()`` → spawn + wait for health + spawn keep-alive task.
    * ``stop()`` → cancel keep-alive, SIGTERM, drain, SIGKILL on timeout.
    * ``is_healthy()`` → bool snapshot of the latest probe result.

    The supervisor is *not* a context manager because plugin lifecycle is
    driven by the BaselithCore loader hooks (``initialize`` / ``shutdown``).
    """

    def __init__(self, config: SupervisorConfig) -> None:
        self._config = config
        self._process: asyncio.subprocess.Process | None = None
        self._keepalive_task: asyncio.Task[None] | None = None
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
        """Latest cached health snapshot. Refreshed by the keep-alive task."""
        return self._healthy

    async def start(self) -> None:
        """Spawn the child process and wait until it answers /api/health."""
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

    async def stop(self) -> None:
        """Best-effort shutdown: cancel keep-alive, SIGTERM, SIGKILL."""
        self._stopped.set()

        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._keepalive_task
            self._keepalive_task = None

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
                "pnpm not found on PATH but dbview plugin is configured "
                "in dev mode. Install pnpm ≥ 11 (`npm install -g pnpm`) "
                "or switch the plugin to prod mode."
            )

    def _build_env(self) -> dict[str, str]:
        env = {
            k: v
            for k, v in os.environ.items()
            if any(k.startswith(p) or k == p for p in _PASSTHROUGH_ENV_PREFIXES)
        }
        # Mandatory overrides — the supervisor *owns* these because they
        # control the contract between the proxy and the child process.
        env["PORT"] = str(self._port)
        env.setdefault("HOST", self._config.host)
        env.setdefault(
            "NODE_ENV",
            "production" if self._config.mode == "prod" else "development",
        )
        env.setdefault("LOG_FORMAT", "json")
        # Make sure tools that read ``PATH`` (pnpm shim) and core libs
        # (timezone, locale) keep working.
        for required in ("PATH", "HOME", "LANG", "LC_ALL", "TZ"):
            if required in os.environ and required not in env:
                env[required] = os.environ[required]
        env.update(self._config.extra_env)
        return env

    def _build_command(self) -> list[str]:
        if self._config.mode == "dev":
            return ["pnpm", "dev"]
        api_dist = self._config.dbview_root / "apps" / "api" / "dist" / "main.js"
        if not api_dist.exists():
            raise FileNotFoundError(
                f"dbview prod bundle not found at {api_dist}. Run "
                "`pnpm install && pnpm -r build` inside "
                f"{self._config.dbview_root} before starting the plugin "
                "in prod mode (or set DBVIEW_PLUGIN_MODE=dev)."
            )
        return ["node", str(api_dist)]

    async def _spawn(self) -> None:
        cwd = self._config.dbview_root
        env = self._build_env()
        cmd = self._build_command()
        logger.info("[dbview] spawning %s (cwd=%s)", " ".join(cmd), cwd)
        # ``_spawn_argv`` is asyncio.create_subprocess_exec — argv form,
        # no shell, no command-string interpolation.
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
            try:
                text = line.decode("utf-8", errors="replace").rstrip()
            except Exception:
                continue
            if text:
                logger.log(level, "[dbview-node] %s", text)

    async def _wait_for_health(self) -> None:
        assert self._port is not None
        url = f"http://{self._config.host}:{self._port}{self._config.health_path}"
        deadline = time.monotonic() + self._config.startup_timeout_s
        last_error: str | None = None
        async with httpx.AsyncClient(timeout=2.0) as client:
            while time.monotonic() < deadline:
                # Premature exit detection: don't keep polling a dead child.
                if (
                    self._process is not None
                    and self._process.returncode is not None
                ):
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

        Two failure paths:
        1. Child exits unexpectedly → spawn a replacement with backoff.
        2. Health probe goes red → log + flip ``_healthy`` for proxy 503s.
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
            except Exception as exc:
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
        # SIGKILL the *process group* — pnpm spawns turbo+vite+nest children
        # and a bare SIGKILL on the parent would orphan them.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
        with contextlib.suppress(Exception):
            await proc.wait()


def build_supervisor_config(
    plugin_dir: Path,
    *,
    extra_env: Mapping[str, str] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> SupervisorConfig:
    """Compose a :class:`SupervisorConfig` from plugin dir + env + overrides.

    Operators tune the supervisor primarily via environment variables so
    that no Python code lives in the host config files. Plugin-level
    YAML config (passed to ``initialize``) is the secondary lever.
    """
    overrides = overrides or {}
    # Resolve to absolute so the supervisor never relies on cwd at spawn
    # time — the host process may chdir before lifespan completes, and a
    # relative ``dbview_root`` would silently concat with the new cwd
    # producing a phantom path. Callers can still pass a relative path
    # for ergonomics; we normalise here.
    plugin_dir = Path(plugin_dir).resolve()
    dbview_root = plugin_dir / "dbview"

    def _env_int(name: str, default: int) -> int:
        raw = os.environ.get(name)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            logger.warning(
                "[dbview] invalid %s=%r, falling back to %d", name, raw, default
            )
            return default

    def _env_float(name: str, default: float) -> float:
        raw = os.environ.get(name)
        if raw is None:
            return default
        try:
            return float(raw)
        except ValueError:
            logger.warning(
                "[dbview] invalid %s=%r, falling back to %s", name, raw, default
            )
            return default

    mode = (
        overrides.get("mode")
        or os.environ.get("DBVIEW_PLUGIN_MODE")
        or "prod"
    )
    if mode not in {"prod", "dev"}:
        logger.warning("[dbview] invalid mode %r, falling back to 'prod'", mode)
        mode = "prod"

    host = (
        overrides.get("host")
        or os.environ.get("DBVIEW_INTERNAL_HOST")
        or "127.0.0.1"
    )
    port_override = overrides.get("port")
    if port_override is None and "DBVIEW_INTERNAL_PORT" in os.environ:
        try:
            port_override = int(os.environ["DBVIEW_INTERNAL_PORT"])
        except ValueError:
            logger.warning(
                "[dbview] invalid DBVIEW_INTERNAL_PORT, allocating dynamically"
            )
            port_override = None

    return SupervisorConfig(
        plugin_dir=plugin_dir,
        dbview_root=dbview_root,
        mode=mode,
        host=host,
        port=port_override,
        startup_timeout_s=_env_float("DBVIEW_STARTUP_TIMEOUT_S", 90.0),
        health_probe_interval_s=_env_float("DBVIEW_HEALTH_INTERVAL_S", 0.5),
        shutdown_grace_s=_env_float("DBVIEW_SHUTDOWN_GRACE_S", 10.0),
        restart_max_attempts=_env_int("DBVIEW_RESTART_MAX_ATTEMPTS", 0),
        extra_env=dict(extra_env or {}),
    )
