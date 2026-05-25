"""Sandbox-provider selection helpers extracted from ``plugin.py``.

Keeps ``plugin.py`` under the 500-line file cap while letting each
sandbox provider (mock / docker / k8s) stay independently unit-testable.

All subprocess invocations use ``asyncio.create_subprocess_exec`` with
an explicit argv list (no shell) — injection-safe by construction.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from core.observability.logging import get_logger
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.sandbox_runner import SandboxRunner

logger = get_logger(__name__)


async def select_sandbox(
    config: RedAgentConfig,
    *,
    on_prepull_task: Callable[[asyncio.Task[None]], None] | None = None,
) -> Any:
    """Pick the right sandbox runner for the current environment.

    Resolution order:

    1. ``RED_AGENT_USE_MOCK_SCANNERS=true`` -> MockSandboxRunner
    2. ``RED_AGENT_SANDBOX_PROVIDER=k8s`` -> K8sJobSandbox
    3. docker images cached locally -> SandboxRunner
    4. fallback -> MockSandboxRunner with a loud warning

    ``on_prepull_task`` receives the prepull asyncio task so the caller
    can cancel it on plugin shutdown.
    """
    from plugins.red_agent.mock_sandbox import MockSandboxRunner

    if config.use_mock_scanners:
        logger.warning(
            "red_agent.sandbox.mock_enabled",
            extra={"reason": "RED_AGENT_USE_MOCK_SCANNERS=true"},
        )
        return MockSandboxRunner()

    if config.sandbox_provider == "k8s":
        return build_k8s_sandbox(config)

    present = await scanner_images_present(config.enabled_scanners)
    if not present:
        logger.warning(
            "red_agent.sandbox.auto_fallback_to_mock",
            extra={
                "reason": (
                    "no scanner docker images present locally; falling back "
                    "to MockSandboxRunner so scans complete fast in dev."
                ),
                "checked_scanners": config.enabled_scanners,
            },
        )
        return MockSandboxRunner()

    logger.info(
        "red_agent.sandbox.docker_active",
        extra={"images_present": sorted(present)},
    )
    sandbox = SandboxRunner()
    if config.prepull_scanner_images and on_prepull_task is not None:
        on_prepull_task(asyncio.create_task(prepull_images(config.enabled_scanners)))
    return sandbox


def build_k8s_sandbox(config: RedAgentConfig) -> Any:
    """Build the K8sJobSandbox provider; falls back to mock on import error."""
    from plugins.red_agent.mock_sandbox import MockSandboxRunner

    try:
        from plugins.red_agent.sandbox.k8s_job import (
            K8sJobSandbox,
            K8sSandboxUnavailable,
        )
    except ImportError as e:
        logger.warning(
            "red_agent.sandbox.k8s_unavailable",
            extra={
                "reason": (
                    "K8sJobSandbox could not be imported; install "
                    "baselith-core[k8s] to enable."
                ),
                "err": str(e),
            },
        )
        return MockSandboxRunner()
    try:
        sandbox = K8sJobSandbox(
            namespace=config.sandbox_k8s_namespace,
            cpu_limit=config.sandbox_k8s_cpu_limit,
            memory_limit=config.sandbox_k8s_memory_limit,
            service_account=config.sandbox_k8s_service_account,
        )
    except K8sSandboxUnavailable as e:
        logger.warning(
            "red_agent.sandbox.k8s_init_failed",
            extra={"err": str(e)},
        )
        return MockSandboxRunner()
    logger.info(
        "red_agent.sandbox.k8s_active",
        extra={"namespace": config.sandbox_k8s_namespace},
    )
    return sandbox


async def scanner_images_present(scanner_names: list[str]) -> set[str]:
    """Subset of scanner names whose docker image is cached locally.

    Uses ``docker image inspect`` (argv list; no shell). Missing docker
    binary -> empty set, same as a fresh dev box.
    """
    from plugins.red_agent.scanners import REGISTRY

    present: set[str] = set()
    for name in scanner_names:
        cls = REGISTRY.get(name)
        if cls is None or not cls.image:
            continue
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "image",
                "inspect",
                cls.image,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            rc = await proc.wait()
            if rc == 0:
                present.add(name)
        except FileNotFoundError:
            return set()
        except Exception:  # noqa: BLE001
            continue
    return present


async def prepull_images(scanner_names: list[str]) -> None:
    """Sequential best-effort docker pull of every enabled scanner image.

    Argv-list invocation (no shell). Each failure is logged once and
    ignored; the next real scan will retry naturally.
    """
    from plugins.red_agent.scanners import REGISTRY

    for name in scanner_names:
        cls = REGISTRY.get(name)
        if cls is None or not cls.image:
            continue
        image = cls.image
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "pull",
                image,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, err = await proc.communicate()
            if proc.returncode != 0:
                logger.warning(
                    "red_agent.prepull.failed",
                    extra={
                        "image": image,
                        "scanner": name,
                        "stderr": err.decode(errors="replace")[:500],
                    },
                )
            else:
                logger.info("red_agent.prepull.ready", extra={"image": image})
        except Exception:  # noqa: BLE001
            logger.exception("red_agent.prepull.exception", extra={"image": image})
