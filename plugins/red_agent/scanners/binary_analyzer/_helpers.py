"""Pure helpers and severity heuristics for the binary analyzer.

Hashing, size formatting, IOC/URL/YARA severity scaling, ATT&CK
mapping, and the optional YARA pass. No ``Finding`` construction here —
that lives in the finding-builder mixins.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from core.observability.logging import get_logger
from plugins.red_agent.models import Severity
from plugins.red_agent.scanners._binary_iocs import (
    is_routable_ipv4,
    shannon_entropy,
)

logger = get_logger(__name__)

# Cap the read so a malicious 10 GiB upload cannot exhaust the worker.
_MAX_BYTES = 256 * 1024 * 1024  # 256 MiB
_HIGH_ENTROPY_THRESHOLD = 7.2


def _human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.2f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


def _format_pe_timestamp(ts: int | None) -> str:
    if not ts:
        return "n/a"
    from datetime import datetime, timezone

    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except (OverflowError, OSError, ValueError):
        return f"raw={ts}"


def _url_severity(labels: list[str]) -> Severity:
    """Severity scaling for the URL classifier output."""
    high = {
        "tor_hidden_service",
        "ip_in_url",
        "dynamic_dns",
        "url_shortener",
        "punycode_idn",
    }
    if any(label.startswith("suspicious_tld_") for label in labels):
        return Severity.HIGH
    if any(label in high for label in labels):
        return Severity.HIGH
    if "deep_subdomain" in labels:
        return Severity.MEDIUM
    if "plaintext_http" in labels:
        return Severity.LOW
    return Severity.MEDIUM


def _hash_all(data: bytes) -> dict[str, str]:
    return {
        "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
        "sha1": hashlib.sha1(data, usedforsecurity=False).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha512": hashlib.sha512(data).hexdigest(),
        "shannon_entropy_full": f"{shannon_entropy(data):.4f}",
    }


def _ioc_severity(kind: str, values: list[str]) -> Severity:
    if kind in {"private_key", "aws_access_key"}:
        return Severity.CRITICAL
    if kind == "jwt":
        return Severity.HIGH
    if kind in {"url", "domain"}:
        return Severity.MEDIUM
    if kind == "ipv4":
        # Routable IPs in a binary are noteworthy; private/loopback are not.
        return (
            Severity.MEDIUM
            if any(is_routable_ipv4(v) for v in values)
            else Severity.LOW
        )
    if kind in {"btc", "eth"}:
        return Severity.HIGH
    if kind == "mutex":
        return Severity.MEDIUM
    return Severity.LOW


def _imports_to_attack(symbols: list[str]) -> list[str]:
    """Coarse mapping of imported APIs to MITRE ATT&CK technique IDs."""
    table: dict[str, str] = {
        "VirtualAllocEx": "T1055",
        "WriteProcessMemory": "T1055",
        "CreateRemoteThread": "T1055.001",
        "QueueUserAPC": "T1055.004",
        "SetWindowsHookExA": "T1056.004",
        "SetWindowsHookExW": "T1056.004",
        "IsDebuggerPresent": "T1622",
        "CheckRemoteDebuggerPresent": "T1622",
        "NtQueryInformationProcess": "T1622",
        "RegSetValueExA": "T1112",
        "RegSetValueExW": "T1112",
        "CreateServiceA": "T1543.003",
        "CreateServiceW": "T1543.003",
        "CryptUnprotectData": "T1555.004",
        "InternetOpenUrlA": "T1071.001",
        "WinHttpOpen": "T1071.001",
    }
    seen: set[str] = set()
    out: list[str] = []
    for sym in symbols:
        tid = table.get(sym)
        if tid and tid not in seen:
            seen.add(tid)
            out.append(tid)
    return out


def _yara_severity(tags: list[str]) -> Severity:
    joined = " ".join(t.lower() for t in tags)
    if any(k in joined for k in ("ransom", "rat", "stealer", "loader")):
        return Severity.CRITICAL
    if any(k in joined for k in ("malware", "trojan", "backdoor")):
        return Severity.HIGH
    if "suspicious" in joined:
        return Severity.MEDIUM
    return Severity.LOW


def _run_yara(path: Path, data: bytes) -> list[dict[str, Any]]:
    """Compile rules from ``RED_AGENT_YARA_RULES`` and scan the buffer."""
    rules_dir = os.environ.get("RED_AGENT_YARA_RULES")
    if not rules_dir:
        return []
    try:
        import yara  # type: ignore[import-untyped]
    except ImportError:
        return []
    try:
        sources: dict[str, str] = {}
        for rule_path in Path(rules_dir).rglob("*.yar*"):
            sources[rule_path.stem] = str(rule_path)
        if not sources:
            return []
        rules = yara.compile(filepaths=sources)
        matches = rules.match(data=data)
    except Exception as e:  # noqa: BLE001
        logger.warning("binary_analyzer.yara_failed", extra={"err": str(e)})
        return []
    out: list[dict[str, Any]] = []
    for m in matches:
        out.append(
            {
                "rule": m.rule,
                "tags": list(m.tags or []),
                "meta": dict(m.meta or {}),
                "strings": [
                    {"offset": s[0], "id": s[1]}
                    for s in (getattr(m, "strings", []) or [])[:32]
                ],
                "path": str(path),
            }
        )
    return out
