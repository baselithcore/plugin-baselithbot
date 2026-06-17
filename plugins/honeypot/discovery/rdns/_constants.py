"""Constants and enums for RDNS resolver."""

import re
from enum import Enum

# Known malicious/suspicious ASN patterns
SUSPICIOUS_ASNS = frozenset(
    {
        "AS9009",  # M247 - Known for VPN/proxy abuse
        "AS16276",  # OVH - Frequently used for scanning
        "AS14061",  # DigitalOcean - High abuse volume
        "AS45102",  # Alibaba - Cloud abuse
        "AS398101",  # GoHost - Bulletproof hosting
        "AS49981",  # WorldStream - Bulletproof provider
        "AS206898",  # Stark Industries - Bulletproof hosting
        "AS44477",  # Stark Industries Solutions
        "AS202425",  # IP Volume - Known abuse
        "AS51852",  # Private Layer - Anonymous hosting
    }
)

# Known crawler/bot domain patterns
CRAWLER_PATTERNS = frozenset(
    {
        "googlebot.com",
        "search.msn.com",
        "crawl.baidu.com",
        "yandex.ru",
        "yandex.com",
        "sogou.com",
        "bingbot.com",
    }
)

VPN_PROXY_PATTERNS = frozenset(
    {
        "m247.com",
        "vultr.com",
        "linode.com",
        "digitalocean.com",
        "amazonaws.com",
        "azure.com",
        "cloudflare.com",
    }
)


class SignificanceLevel(str, Enum):
    """Significance level for RDNS results."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class IPCategory(str, Enum):
    """Category classification for IP addresses."""

    CRAWLER = "crawler"
    VPN_PROXY = "vpn_proxy"
    HOSTING = "hosting"
    ISP = "isp"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"


# Maximum hostname length to prevent memory exhaustion
MAX_HOSTNAME_LENGTH = 255

# Regex to validate hostname format (RFC 1123)
HOSTNAME_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
)
