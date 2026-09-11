"""Rendezvous-port ownership check run before every child spawn.

Under multi-worker leadership the Node child binds a *fixed* loopback port so
follower workers know where to forward without any cross-worker publication
(see :mod:`plugins.dbview.leader`). That makes the port — not the advisory
lock — the real mutex on the child: the lock is released the instant a leader
worker dies, while its child keeps the port for as long as it takes to exit.

Spawning into an occupied port is never useful. The child dies with
``EADDRINUSE`` while whatever already listens there keeps answering
``/api/health``, so a port-shaped health gate reads green and the supervisor
believes it restarted successfully. Checking ownership *before* spawning turns
that into one honest, actionable failure.

The check tolerates the short window in which a predecessor is still shutting
down, so an ordinary leadership handover does not surface as an error.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import time

logger = logging.getLogger(__name__)

# Long enough to see a refusal or an accept on loopback, short enough that a
# port held by a hung process does not stall the whole poll.
_CONNECT_TIMEOUT_S = 0.5

_POLL_INTERVAL_S = 0.25

__all__ = ["PortUnavailableError", "is_port_taken", "wait_for_free_port"]


class PortUnavailableError(RuntimeError):
    """Raised when the upstream port is still held by another process."""


def is_port_taken(host: str, port: int) -> bool:
    """Report whether *something* already accepts connections on the port.

    A successful connect is the only reliable signal available without
    inspecting other processes: it covers a listener on ``127.0.0.1`` and one
    on ``0.0.0.0`` alike, which matters because the embedded API binds all
    interfaces regardless of the ``HOST`` the supervisor passes it.
    """
    try:
        with socket.create_connection((host, port), timeout=_CONNECT_TIMEOUT_S):
            return True
    except OSError:
        return False


async def wait_for_free_port(host: str, port: int, *, timeout_s: float) -> None:
    """Block until nothing listens on ``host:port``.

    Args:
        host: Address the child will bind.
        port: Port the child will bind.
        timeout_s: How long a predecessor is allowed to keep the port while it
            shuts down. ``<= 0`` checks once and gives up immediately.

    Raises:
        PortUnavailableError: The port was still held when the window expired.
            The message names the usual cause so the operator does not have to
            rediscover it from a wall of ``EADDRINUSE`` restart lines.
    """
    deadline = time.monotonic() + max(timeout_s, 0.0)
    waited = False
    while True:
        if not await asyncio.to_thread(is_port_taken, host, port):
            if waited:
                logger.info("[dbview] upstream port %d released", port)
            return
        if time.monotonic() >= deadline:
            break
        if not waited:
            waited = True
            logger.info(
                "[dbview] upstream port %d still held — waiting up to %.1fs for "
                "the previous child to exit",
                port,
                timeout_s,
            )
        await asyncio.sleep(_POLL_INTERVAL_S)

    raise PortUnavailableError(
        f"{host}:{port} is still held by another process after {timeout_s:.1f}s "
        "— refusing to spawn a child that would only die with EADDRINUSE. The "
        "usual cause is a Node child orphaned by a worker that was killed "
        "without running the plugin's shutdown; terminate it (it is the "
        "'node .../apps/api/dist/main.js' process whose parent is init) or "
        "point DBVIEW_INTERNAL_PORT at a free port."
    )
