"""Built-in runtime tools for live ('operate') agent execution.

These are the concrete capabilities a synthesised agent can call inside the
ReAct loop: fetch a URL, send a Telegram message, read the clock. Each tool is
a plain async function returning a string (the loop feeds the string back as an
Observation), wrapped in a core :class:`ToolDefinition`.

Security posture:
    * ``http_get`` is SSRF-guarded — loopback/private/link-local hosts and
      non-http(s) schemes are refused unless ``allow_internal`` is set, mirroring
      the framework's BrowserAgent policy.
    * Telegram credentials are held as ``SecretStr`` and only unwrapped at the
      moment of the API call; they are never logged.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import SecretStr

from core.observability.logging import get_logger
from core.reasoning.react import ToolDefinition

logger = get_logger(__name__)

__all__ = ["ToolConfig", "build_runtime_tools", "available_tool_names"]

_HTTP_TIMEOUT = 15.0
_MAX_BODY_CHARS = 2000
_MAX_REDIRECTS = 3
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


@dataclass(slots=True)
class ToolConfig:
    """Credentials and policy for the runtime tools."""

    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None
    allow_internal: bool = False


def available_tool_names() -> list[str]:
    """Return the names of all built-in runtime tools."""
    return ["http_get", "send_telegram", "now"]


def _is_safe_url(url: str, allow_internal: bool) -> tuple[bool, str]:
    """Validate a URL against SSRF: scheme + resolved-host checks."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, f"scheme '{parsed.scheme}' not allowed (use http/https)"
    host = parsed.hostname
    if not host:
        return False, "missing host"
    if allow_internal:
        return True, ""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        return False, f"DNS resolution failed: {exc}"
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
        ):
            return False, f"host resolves to blocked address {addr}"
    return True, ""


def build_runtime_tools(allowed: list[str], config: ToolConfig) -> list[ToolDefinition]:
    """Build the ToolDefinition list for an operate run, filtered by scope.

    Args:
        allowed: Tool names the blueprint's scope permits.
        config: Credentials/policy for the tools.

    Returns:
        ToolDefinitions for every requested-and-known tool. Unknown names are
        silently dropped (the agent simply cannot call them).
    """
    allow = set(allowed)

    async def http_get(url: str) -> str:
        # Redirects are followed MANUALLY so every hop is re-validated against
        # the SSRF guard. Auto-following (follow_redirects=True) would let a
        # public URL bounce to a private/loopback host (e.g. cloud metadata)
        # without re-checking — the classic redirect-based SSRF bypass.
        current = url
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT, follow_redirects=False
            ) as client:
                for _ in range(_MAX_REDIRECTS + 1):
                    ok, reason = _is_safe_url(current, config.allow_internal)
                    if not ok:
                        return f"refused: {reason}"
                    resp = await client.get(current)
                    if resp.status_code in _REDIRECT_CODES:
                        location = resp.headers.get("location")
                        if not location:
                            break
                        current = urljoin(current, location)
                        continue
                    return f"HTTP {resp.status_code}\n{resp.text[:_MAX_BODY_CHARS]}"
                return "refused: too many redirects"
        except httpx.HTTPError as exc:
            return f"http error: {exc}"

    async def send_telegram(text: str, chat_id: str = "") -> str:
        if config.telegram_bot_token is None:
            return "refused: telegram_bot_token not configured"
        target = chat_id or config.telegram_chat_id
        if not target:
            return "refused: no chat_id (configure telegram_chat_id)"
        token = config.telegram_bot_token.get_secret_value()
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.post(
                    _TELEGRAM_API.format(token=token),
                    json={"chat_id": target, "text": text},
                )
        except httpx.HTTPError as exc:
            return f"telegram error: {exc}"
        if resp.status_code == 200:
            return "sent"
        return f"telegram failed: HTTP {resp.status_code} {resp.text[:200]}"

    async def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    catalogue: dict[str, ToolDefinition] = {
        "http_get": ToolDefinition(
            name="http_get",
            fn=http_get,
            description="Fetch a public URL (http/https). Args: url. Returns status + body.",
        ),
        "send_telegram": ToolDefinition(
            name="send_telegram",
            fn=send_telegram,
            description="Send a Telegram message. Args: text[, chat_id].",
        ),
        "now": ToolDefinition(
            name="now",
            fn=now,
            description="Return the current UTC time in ISO-8601. No args.",
        ),
    }
    return [tool for name, tool in catalogue.items() if name in allow]
