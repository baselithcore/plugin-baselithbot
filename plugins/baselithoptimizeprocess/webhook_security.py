"""SSRF guard for automation webhook targets.

Automation rules let an operator specify a ``webhook_url`` the server will POST
to when the rule fires. That URL is attacker-influenceable, so it is validated
both at rule-creation time (reject → HTTP 422, never persist a bad rule) and
again immediately before each POST (defence in depth, and DNS may have changed).

The guard: require an allowed scheme (``https`` by default), resolve every
address the hostname maps to, and reject any that is loopback/private/link-local/
reserved/multicast/unspecified — the ranges an SSRF payload would target (cloud
metadata at 169.254.169.254, ``localhost`` services, internal RFC-1918 hosts).
An operator allowlist and a dev-only escape hatch are both supported via env.
"""

from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTNAMES = frozenset({"localhost", "broadcasthost"})


class WebhookValidationError(ValueError):
    """Raised when a webhook URL is malformed or targets a blocked address."""


def _allowed_schemes() -> frozenset[str]:
    """Schemes permitted for webhooks (https always; http only in dev mode)."""
    return frozenset({"http", "https"}) if _guard_disabled() else frozenset({"https"})


def _guard_disabled() -> bool:
    """True when the SSRF guard is bypassed for trusted local development."""
    raw = os.environ.get("BASELITH_BOP_ALLOW_INTERNAL_WEBHOOKS", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _host_allowlist() -> frozenset[str]:
    """Operator-configured allowlist of webhook hostnames (optional)."""
    raw = os.environ.get("BOP_WEBHOOK_ALLOWED_HOSTS", "")
    return frozenset(h.strip().lower() for h in raw.split(",") if h.strip())


def _ip_is_blocked(ip: str) -> bool:
    """True when an IP literal falls in a range an SSRF payload would abuse."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _resolve(hostname: str, port: int) -> list[str]:
    """Resolve a hostname to its IP literals (blocking; call via to_thread)."""
    infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    return [str(info[4][0]) for info in infos]


async def validate_webhook_url(url: str) -> None:
    """Raise :class:`WebhookValidationError` if ``url`` is unsafe to call.

    Args:
        url: The webhook target to validate.

    Raises:
        WebhookValidationError: On a bad scheme, missing host, resolution
            failure, or any address resolving into a blocked range.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _allowed_schemes():
        raise WebhookValidationError(f"scheme '{scheme}' not allowed for webhooks")

    hostname = (parsed.hostname or "").lower().strip(".")
    if not hostname:
        raise WebhookValidationError("webhook url has no host")

    allowlist = _host_allowlist()
    if allowlist and hostname not in allowlist:
        raise WebhookValidationError(f"host '{hostname}' is not in the allowlist")

    if hostname in _BLOCKED_HOSTNAMES or hostname.endswith(".localhost"):
        raise WebhookValidationError(f"host '{hostname}' is blocked")

    if _guard_disabled():
        return

    port = parsed.port or (443 if scheme == "https" else 80)
    try:
        addresses = await asyncio.to_thread(_resolve, hostname, port)
    except socket.gaierror as exc:
        raise WebhookValidationError(f"cannot resolve host '{hostname}'") from exc

    blocked = [ip for ip in addresses if _ip_is_blocked(ip)]
    if blocked or not addresses:
        raise WebhookValidationError(
            f"host '{hostname}' resolves to a blocked address ({blocked or 'none'})"
        )


__all__ = ["validate_webhook_url", "WebhookValidationError"]
