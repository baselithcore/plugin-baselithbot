"""Indicator enrichment classifiers used in finding titles/descriptions.

Pure-stdlib heuristics so the operator sees actionable detail without
ever expanding the raw evidence blob.
"""

from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────
# IPv4 classification

_RESERVED_RANGES_V4: tuple[tuple[str, str], ...] = (
    ("0.", "this network"),
    ("10.", "RFC1918 private"),
    ("100.64.", "RFC6598 carrier-grade NAT"),
    ("127.", "loopback"),
    ("169.254.", "link-local"),
    ("172.16.", "RFC1918 private"),
    ("172.17.", "RFC1918 private"),
    ("172.18.", "RFC1918 private"),
    ("172.19.", "RFC1918 private"),
    ("172.20.", "RFC1918 private"),
    ("172.21.", "RFC1918 private"),
    ("172.22.", "RFC1918 private"),
    ("172.23.", "RFC1918 private"),
    ("172.24.", "RFC1918 private"),
    ("172.25.", "RFC1918 private"),
    ("172.26.", "RFC1918 private"),
    ("172.27.", "RFC1918 private"),
    ("172.28.", "RFC1918 private"),
    ("172.29.", "RFC1918 private"),
    ("172.30.", "RFC1918 private"),
    ("172.31.", "RFC1918 private"),
    ("192.0.0.", "IETF protocol assignments"),
    ("192.0.2.", "TEST-NET-1 (RFC5737 documentation)"),
    ("192.168.", "RFC1918 private"),
    ("198.18.", "benchmarking (RFC2544)"),
    ("198.19.", "benchmarking (RFC2544)"),
    ("198.51.100.", "TEST-NET-2 (RFC5737 documentation)"),
    ("203.0.113.", "TEST-NET-3 (RFC5737 documentation)"),
    ("224.", "IPv4 multicast"),
    ("239.", "IPv4 multicast (administratively scoped)"),
    ("255.255.255.255", "limited broadcast"),
)


def classify_ipv4(addr: str) -> str:
    """Human-readable classification for a v4 address.

    Empty string means "ordinary public unicast". Values like ``"loopback"``
    or ``"TEST-NET-2"`` are surfaced verbatim in finding titles so an
    operator can dismiss false positives at a glance.
    """
    for prefix, label in _RESERVED_RANGES_V4:
        if addr.startswith(prefix):
            return label
    return ""


# ──────────────────────────────────────────────────────────────────────
# URL classification

# Suspicious top-level domains commonly abused for phishing / C2.
# Sources: Spamhaus DBL, Cloudflare Radar abuse reports, Recorded Future.
_SUSPICIOUS_TLDS = frozenset(
    {
        "tk",
        "top",
        "xyz",
        "ml",
        "ga",
        "cf",
        "gq",
        "buzz",
        "click",
        "country",
        "loan",
        "men",
        "stream",
        "trade",
        "win",
        "work",
        "review",
        "kim",
        "bid",
        "rest",
        "racing",
        "icu",
        "rocks",
        "monster",
        "fit",
        "online",
        "site",
        "live",
        "best",
        "cyou",
        "lol",
        "sbs",
        "world",
        "uno",
    }
)

_DYNAMIC_DNS_HOSTS = frozenset(
    {
        "duckdns.org",
        "no-ip.com",
        "noip.me",
        "dyndns.org",
        "dnsdynamic.com",
        "dynu.com",
        "ddns.net",
        "freedns.afraid.org",
        "now.im",
        "myftp.org",
        "myftp.biz",
        "servehttp.com",
        "serveftp.com",
        "hopto.org",
        "zapto.org",
        "redirectme.net",
        "sytes.net",
        "ngrok.io",
        "ngrok-free.app",
        "trycloudflare.com",
        "loca.lt",
        "serveo.net",
    }
)

_URL_SHORTENERS = frozenset(
    {
        "bit.ly",
        "t.co",
        "goo.gl",
        "ow.ly",
        "tinyurl.com",
        "is.gd",
        "buff.ly",
        "rebrand.ly",
        "shorte.st",
        "cutt.ly",
        "lnkd.in",
        "rb.gy",
        "tiny.cc",
        "shorturl.at",
        "qr.ae",
        "v.gd",
    }
)


def classify_url(url: str) -> list[str]:
    """Return zero-or-more indicator labels for a URL.

    Labels accumulate (e.g. an ``http://1.2.3.4.duckdns.org/`` URL gets
    ``["dynamic_dns", "ip_in_url"]``) so the caller can choose severity
    based on the worst hit.
    """
    labels: list[str] = []
    lower = url.lower()
    if lower.startswith("http://"):
        labels.append("plaintext_http")
    if ".onion" in lower:
        labels.append("tor_hidden_service")
    # IP-literal in URL.
    import re as _re

    ip_lit = _re.search(r"://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", lower)
    if ip_lit:
        labels.append("ip_in_url")
    # Hostname inspection.
    host_match = _re.search(r"://([^/:?#]+)", lower)
    if host_match:
        host = host_match.group(1)
        # Strip trailing port if present.
        host = host.split(":")[0]
        # Suspicious TLD.
        tld = host.rsplit(".", 1)[-1] if "." in host else ""
        if tld in _SUSPICIOUS_TLDS:
            labels.append(f"suspicious_tld_.{tld}")
        # Dynamic DNS.
        for ddns in _DYNAMIC_DNS_HOSTS:
            if host == ddns or host.endswith("." + ddns):
                labels.append("dynamic_dns")
                break
        # URL shortener.
        if host in _URL_SHORTENERS:
            labels.append("url_shortener")
        # Excessive subdomain depth (DGA-like).
        if host.count(".") >= 4:
            labels.append("deep_subdomain")
        # Punycode (homoglyph IDN).
        if "xn--" in host:
            labels.append("punycode_idn")
    return labels


def threat_intel_pivot_links(kind: str, value: str) -> dict[str, str]:
    """Return well-known threat-intel pivot URLs for an indicator.

    Operators can copy-paste rather than retyping. Limited to public,
    non-API-keyed surfaces so links open without authentication; deeper
    enrichers (VT API, MISP, OpenCTI) attach their own evidence blocks
    via the existing red_agent enricher chain.
    """
    from urllib.parse import quote

    encoded = quote(value, safe="")
    if kind == "ipv4" or kind == "ipv6":
        return {
            "VirusTotal": f"https://www.virustotal.com/gui/ip-address/{encoded}",
            "AbuseIPDB": f"https://www.abuseipdb.com/check/{encoded}",
            "Shodan": f"https://www.shodan.io/host/{encoded}",
            "GreyNoise": f"https://viz.greynoise.io/ip/{encoded}",
        }
    if kind == "domain":
        return {
            "VirusTotal": f"https://www.virustotal.com/gui/domain/{encoded}",
            "URLhaus": f"https://urlhaus.abuse.ch/browse.php?search={encoded}",
            "AlienVault OTX": f"https://otx.alienvault.com/indicator/domain/{encoded}",
            "crt.sh": f"https://crt.sh/?q={encoded}",
        }
    if kind == "url":
        return {
            "VirusTotal": f"https://www.virustotal.com/gui/search/{encoded}",
            "URLhaus": f"https://urlhaus.abuse.ch/browse.php?search={encoded}",
        }
    if kind == "sha256":
        return {
            "VirusTotal": f"https://www.virustotal.com/gui/file/{encoded}",
            "MalwareBazaar": f"https://bazaar.abuse.ch/sample/{encoded}/",
            "Hybrid Analysis": f"https://www.hybrid-analysis.com/search?query={encoded}",
        }
    return {}
