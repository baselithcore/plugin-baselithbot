"""Strings, entropy and IOC extraction helpers for the binary analyzer.

Pure stdlib. Designed to run on raw bytes without ever executing the
sample. Regex catalogue mirrors the patterns shared across modern
malware-analysis pipelines (CISA STIX guides, MITRE ATT&CK
indicator types, Volexity/Mandiant blogposts).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

# Minimum printable run length, matching the ``strings`` Unix utility default.
MIN_STRING_LEN = 6
ASCII_RANGE = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D}


def shannon_entropy(data: bytes) -> float:
    """Shannon entropy in bits/byte. 0 = constant, 8 = uniform random.

    Sections above 7.0 are typically packed/encrypted.
    """
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def extract_strings(data: bytes, *, min_len: int = MIN_STRING_LEN) -> list[str]:
    """Extract printable ASCII and UTF-16-LE string runs."""
    out: list[str] = []
    cur: list[int] = []
    for b in data:
        if b in ASCII_RANGE:
            cur.append(b)
        else:
            if len(cur) >= min_len:
                out.append(bytes(cur).decode("ascii", errors="replace"))
            cur = []
    if len(cur) >= min_len:
        out.append(bytes(cur).decode("ascii", errors="replace"))

    # UTF-16-LE: ascii byte followed by 0x00.
    cur = []
    i = 0
    n = len(data)
    while i + 1 < n:
        lo, hi = data[i], data[i + 1]
        if hi == 0 and lo in ASCII_RANGE:
            cur.append(lo)
            i += 2
            continue
        if len(cur) >= min_len:
            out.append(bytes(cur).decode("ascii", errors="replace"))
        cur = []
        i += 1
    if len(cur) >= min_len:
        out.append(bytes(cur).decode("ascii", errors="replace"))
    return out


# ──────────────────────────────────────────────────────────────────────
# IOC regex catalogue
#
# Patterns are anchored to common indicator shapes; each one maps to an
# IOC ``kind`` consumed by the graph layer (so the Finding renderer can
# pivot to "all targets sharing this domain" without re-parsing).

_IOC_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ipv4",
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
        ),
    ),
    (
        "ipv6",
        re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b"),
    ),
    (
        "url",
        re.compile(r"\bhttps?://[^\s\"'<>()]+", re.IGNORECASE),
    ),
    (
        "domain",
        re.compile(
            r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
            r"(?:[a-z]{2,24})\b",
            re.IGNORECASE,
        ),
    ),
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b"),
    ),
    (
        "btc",
        re.compile(r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,87}\b"),
    ),
    (
        "eth",
        re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    ),
    (
        "registry_key",
        re.compile(
            r"\b(?:HKEY_LOCAL_MACHINE|HKEY_CURRENT_USER|HKLM|HKCU)\\"
            r"[A-Za-z0-9_\\\-\.]+",
        ),
    ),
    (
        "unc_path",
        re.compile(r"\\\\[A-Za-z0-9_\-.]+\\[^\s\"'<>]+"),
    ),
    (
        "windows_path",
        re.compile(
            r"\b[A-Z]:\\(?:[^\\\s\"'<>]+\\)*[^\\\s\"'<>]+",
        ),
    ),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    ),
    (
        "aws_access_key",
        re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ),
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    ),
    (
        "mutex",
        re.compile(r"\b(?:Global|Local)\\[A-Za-z0-9_\-.{}]{4,}", re.IGNORECASE),
    ),
)

# Domains alone produce too much noise (every embedded version string
# matches "x.y.z" tokens). Reject obvious non-network suffixes so the
# resulting IOC list stays signal-heavy.
_DOMAIN_SUFFIX_DENY = {
    "dll",
    "exe",
    "sys",
    "so",
    "dylib",
    "lib",
    "obj",
    "txt",
    "json",
    "xml",
    "html",
    "css",
    "js",
    "py",
    "rb",
    "go",
    "rs",
    "md",
    "yml",
    "yaml",
    "log",
    "tmp",
    "bin",
    "dat",
}

# Reserved/private ranges that should not be reported as C2 candidates
# (they still get tracked but with severity downgraded by the caller).
_PRIVATE_IPV4_PREFIXES = (
    "0.",
    "10.",
    "127.",
    "169.254.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "192.168.",
    "224.",
    "255.255.255.255",
)


def is_routable_ipv4(addr: str) -> bool:
    return not any(addr.startswith(p) for p in _PRIVATE_IPV4_PREFIXES)


# ──────────────────────────────────────────────────────────────────────
# Indicator enrichment — pure-stdlib classifiers used in finding titles
# and descriptions so the operator sees actionable detail without ever
# expanding the raw evidence blob.

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


def extract_iocs(strings: Iterable[str]) -> dict[str, list[str]]:
    """Run every IOC rule across the joined string corpus.

    Returns a kind → unique-sorted-list map. Order within a list reflects
    first-seen order, which preserves source locality for triage.
    """
    blob = "\n".join(strings)
    out: dict[str, list[str]] = {}
    for kind, pattern in _IOC_RULES:
        seen: set[str] = set()
        hits: list[str] = []
        for m in pattern.finditer(blob):
            value = m.group(0)
            if kind == "domain":
                tld = value.rsplit(".", 1)[-1].lower()
                if tld in _DOMAIN_SUFFIX_DENY:
                    continue
                if value.lower() in seen:
                    continue
                seen.add(value.lower())
            else:
                if value in seen:
                    continue
                seen.add(value)
            hits.append(value)
        if hits:
            out[kind] = hits
    return out


def suspicious_imports(symbols: Iterable[str]) -> list[str]:
    """Return imported API names that are commonly abused by malware.

    Drawn from the Microsoft ATT&CK behaviour catalog and the capa rule
    headlines. The list is intentionally short — fine-grained capability
    detection lives in a dedicated capa pass when available.
    """
    watchlist = {
        # Process injection / execution
        "VirtualAllocEx",
        "WriteProcessMemory",
        "CreateRemoteThread",
        "NtCreateThreadEx",
        "QueueUserAPC",
        "SetWindowsHookExA",
        "SetWindowsHookExW",
        "NtMapViewOfSection",
        # Anti-analysis
        "IsDebuggerPresent",
        "CheckRemoteDebuggerPresent",
        "NtQueryInformationProcess",
        "OutputDebugStringA",
        "GetTickCount",
        "QueryPerformanceCounter",
        # Persistence
        "RegSetValueExA",
        "RegSetValueExW",
        "RegCreateKeyExA",
        "CreateServiceA",
        "CreateServiceW",
        "StartServiceA",
        # Credential access
        "LsaEnumerateLogonSessions",
        "SamConnect",
        "CryptUnprotectData",
        # Networking / C2
        "InternetOpenA",
        "InternetOpenUrlA",
        "WinHttpOpen",
        "WSAStartup",
        "connect",
        "socket",
        "send",
        "recv",
        # Discovery
        "GetAdaptersInfo",
        "NetWkstaUserEnum",
        "GetUserNameA",
        # Defense evasion
        "VirtualProtect",
        "NtUnmapViewOfSection",
        "DeleteFileA",
        "DeleteFileW",
    }
    hits: list[str] = []
    seen: set[str] = set()
    for sym in symbols:
        base = sym.split(".")[-1] if "." in sym else sym
        if base in watchlist and base not in seen:
            seen.add(base)
            hits.append(base)
    return hits
