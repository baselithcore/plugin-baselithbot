"""IOC regex catalogue, extraction, and suspicious-import detection.

Pure stdlib. The regex catalogue mirrors the patterns shared across
modern malware-analysis pipelines (CISA STIX guides, MITRE ATT&CK
indicator types, Volexity/Mandiant blogposts).
"""

from __future__ import annotations

import re
from typing import Iterable

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
