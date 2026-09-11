"""Readiness and liveness probing for the dbview Node child.

The supervisor's only view of the child's health is an HTTP endpoint on a
port — which is a weaker signal than it looks. A port can be answered by a
process the supervisor does not own: when a worker is replaced without running
the plugin's shutdown, its Node child keeps the fixed rendezvous port, and the
replacement child dies with ``EADDRINUSE`` while the incumbent keeps serving
``/api/health``. Read naively, the gate then reports somebody else's health as
proof that our own doomed child came up.

So the gate takes a liveness callback alongside the URL and refuses any green
probe our own child cannot have answered. :mod:`.portguard` keeps the case
from arising at all; this is the backstop for a listener that appears between
that check and the first probe.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable

import httpx

logger = logging.getLogger(__name__)

# Generous for loopback, tight enough that a wedged listener cannot stall a
# probe long enough to matter against the startup deadline.
_PROBE_TIMEOUT_S = 2.0

__all__ = [
    "StartupTimeoutError",
    "await_health",
    "probe_health",
    "reject_foreign_listener",
]


class StartupTimeoutError(RuntimeError):
    """Raised when the child process never answers ``/api/health``."""


def reject_foreign_listener(url: str, child_returncode: int | None) -> None:
    """Refuse a green probe that our own child cannot have answered.

    Args:
        url: The probed endpoint, for the error message.
        child_returncode: ``None`` while the child this supervisor spawned is
            still running; its exit status once it is gone. A supervisor with
            no child of its own (follower mode) also passes ``None``.

    Raises:
        StartupTimeoutError: The child is already dead, so the response
            describes a different process holding the port. Left unchecked the
            keep-alive loop would log a successful restart and reset its
            backoff on every pass, respawning a doomed child forever.
    """
    if child_returncode is None:
        return
    raise StartupTimeoutError(
        f"{url} answered, but the child this supervisor spawned already exited "
        f"(returncode={child_returncode}) — the port is held by another "
        "process, so the probe describes somebody else's health."
    )


async def probe_health(url: str) -> bool:
    """One-shot liveness probe. Any transport error reads as unhealthy."""
    try:
        async with httpx.AsyncClient(timeout=_PROBE_TIMEOUT_S) as client:
            resp = await client.get(url)
            return resp.status_code < 500
    except httpx.HTTPError:
        return False


async def await_health(
    url: str,
    *,
    timeout_s: float,
    interval_s: float,
    child_returncode: Callable[[], int | None],
) -> None:
    """Poll ``url`` until the child is serving, or give up.

    Args:
        url: The child's health endpoint.
        timeout_s: Total budget for the child to come up.
        interval_s: Delay between probes.
        child_returncode: Reads the child's exit status, ``None`` while alive.

    Raises:
        StartupTimeoutError: The child exited during startup, the endpoint was
            answered by another process, or the budget expired.
    """
    deadline = time.monotonic() + timeout_s
    last_error: str | None = None
    async with httpx.AsyncClient(timeout=_PROBE_TIMEOUT_S) as client:
        while time.monotonic() < deadline:
            # Premature-exit detection: don't keep polling a dead child.
            exited = child_returncode()
            if exited is not None:
                raise StartupTimeoutError(
                    f"dbview child exited during startup (returncode={exited}) "
                    f"before answering {url}"
                )
            try:
                resp = await client.get(url)
                if resp.status_code < 500:
                    reject_foreign_listener(url, child_returncode())
                    logger.info(
                        "[dbview] health probe OK in %.2fs (status=%d)",
                        timeout_s - max(0.0, deadline - time.monotonic()),
                        resp.status_code,
                    )
                    return
                last_error = f"HTTP {resp.status_code}"
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            await asyncio.sleep(interval_s)
    raise StartupTimeoutError(
        f"dbview API did not become healthy within {timeout_s:.0f}s "
        f"(last_error={last_error})"
    )
