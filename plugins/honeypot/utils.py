"""Honeypot Utilities.

Utility functions for IP normalization and display.
"""

import ipaddress
from core.observability.logging import get_logger
from typing import Optional, Tuple

logger = get_logger(__name__)


def normalize_ip_display(ip: str) -> str:
    """Convert IP address to a human-friendly display format.

    Args:
        ip: Raw IP address string

    Returns:
        Normalized display string
    """
    if not ip or ip == "unknown":
        return "Unknown"

    # Handle localhost variants
    if is_localhost(ip):
        return "localhost"

    try:
        addr = ipaddress.ip_address(ip)

        # IPv6 addresses - show compressed form
        if isinstance(addr, ipaddress.IPv6Address):
            # Check for IPv4-mapped IPv6 (::ffff:192.168.1.1)
            if addr.ipv4_mapped:
                return str(addr.ipv4_mapped)
            # Return compressed IPv6
            return str(addr.compressed)

        # IPv4 - return as-is
        return str(addr)

    except ValueError:
        # Invalid IP, return as-is
        return ip


def is_localhost(ip: str) -> bool:
    """Check if IP address is any form of localhost.

    Args:
        ip: IP address string

    Returns:
        True if IP is localhost (IPv4 or IPv6)
    """
    if ip in ("localhost", "127.0.0.1", "::1"):
        return True

    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_loopback
    except ValueError:
        return ip.lower() == "localhost"


def is_private_or_local(ip: str) -> bool:
    """Check if IP is private, local, or non-routable.

    Args:
        ip: IP address string

    Returns:
        True if IP is private/local
    """
    if ip in ("localhost", "unknown", ""):
        return True

    try:
        addr = ipaddress.ip_address(ip)
        return (
            addr.is_loopback
            or addr.is_private
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        )
    except ValueError:
        return True


def get_ip_type(ip: str) -> str:
    """Get the type/classification of an IP address.

    Args:
        ip: IP address string

    Returns:
        String describing the IP type
    """
    if not ip or ip == "unknown":
        return "unknown"

    try:
        addr = ipaddress.ip_address(ip)

        if addr.is_loopback:
            return "loopback"
        if addr.is_private:
            return "private"
        if addr.is_link_local:
            return "link-local"
        if addr.is_reserved:
            return "reserved"
        if addr.is_multicast:
            return "multicast"

        return "public"

    except ValueError:
        return "invalid"


def parse_ip_with_port(address: str) -> Tuple[str, Optional[int]]:
    """Parse an address that may contain IP and port.

    Args:
        address: Address string like "192.168.1.1:8080" or "[::1]:8080"

    Returns:
        Tuple of (ip, port) where port may be None
    """
    if not address:
        return ("unknown", None)

    # Handle IPv6 with port: [::1]:8080
    if address.startswith("["):
        bracket_end = address.find("]")
        if bracket_end > 0:
            ip = address[1:bracket_end]
            if len(address) > bracket_end + 1 and address[bracket_end + 1] == ":":
                try:
                    port = int(address[bracket_end + 2 :])
                    return (ip, port)
                except ValueError:
                    pass
            return (ip, None)

    # Handle IPv4 with port: 192.168.1.1:8080
    if ":" in address and address.count(":") == 1:
        parts = address.rsplit(":", 1)
        try:
            port = int(parts[1])
            return (parts[0], port)
        except ValueError:
            pass

    # Just IP, no port
    return (address, None)


def format_ip_for_display(ip: str, include_type: bool = False) -> str:
    """Format an IP address for UI display with optional type indicator.

    Args:
        ip: IP address string
        include_type: Whether to include type label

    Returns:
        Formatted display string
    """
    normalized = normalize_ip_display(ip)

    if not include_type:
        return normalized

    ip_type = get_ip_type(ip)

    if ip_type == "loopback":
        return f"{normalized} (local)"
    elif ip_type == "private":
        return f"{normalized} (private)"
    elif ip_type == "public":
        return normalized
    else:
        return f"{normalized} ({ip_type})"
