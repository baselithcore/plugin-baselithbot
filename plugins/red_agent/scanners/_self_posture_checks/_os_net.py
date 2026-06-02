"""OS/kernel posture and network-exposure checks (Linux).

Reads ``/etc/os-release``, ``/proc/sys`` and ``/proc/net/tcp*`` directly
— no subprocess, no network. Degrades gracefully on non-Linux hosts.
"""

from __future__ import annotations

import ipaddress
import platform
from pathlib import Path

from plugins.red_agent.models import Finding, Severity
from plugins.red_agent.scanners._self_posture_checks._helpers import (
    _new_finding,
    _read_text,
)


# ──────────────────────────────────────────────────────────────────────
# OS / kernel posture (Linux)


def check_os_release(target: str) -> list[Finding]:
    findings: list[Finding] = []
    text = _read_text("/etc/os-release") or ""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        fields[k.strip()] = v.strip().strip('"')
    pretty = fields.get("PRETTY_NAME") or fields.get("NAME") or platform.platform()
    findings.append(
        _new_finding(
            target=target,
            title=f"Operating system: {pretty}",
            severity=Severity.INFO,
            description=(
                f"Host runs {pretty}. The orchestrator inherits the kernel's "
                "security posture; review the CIS Benchmark applicable to "
                "this distribution."
            ),
            remediation=(
                "Map findings against the CIS Benchmark for this OS family "
                "and apply the Level 1 profile as a baseline."
            ),
            controls=["CIS-1.1", "NIST-CM-2"],
            evidence={"os_release": fields, "kernel": platform.release()},
        )
    )
    return findings


def check_kernel_hardening(target: str) -> list[Finding]:
    if platform.system() != "Linux":
        return []
    findings: list[Finding] = []
    sysctl = {
        "kernel.kptr_restrict": ("2", Severity.MEDIUM, "CIS-1.5.1", "CWE-200"),
        "kernel.dmesg_restrict": ("1", Severity.LOW, "CIS-1.5.2", "CWE-532"),
        "kernel.randomize_va_space": ("2", Severity.HIGH, "CIS-1.5.3", "CWE-119"),
        "kernel.yama.ptrace_scope": ("1", Severity.MEDIUM, "CIS-1.5.4", "CWE-732"),
        "fs.protected_hardlinks": ("1", Severity.MEDIUM, "CIS-1.6.1", "CWE-59"),
        "fs.protected_symlinks": ("1", Severity.MEDIUM, "CIS-1.6.2", "CWE-59"),
        "fs.suid_dumpable": ("0", Severity.MEDIUM, "CIS-1.5.5", "CWE-269"),
        "net.ipv4.conf.all.rp_filter": ("1", Severity.LOW, "CIS-3.2.7", "CWE-940"),
        "net.ipv4.tcp_syncookies": ("1", Severity.LOW, "CIS-3.2.8", "CWE-400"),
        "net.ipv4.ip_forward": ("0", Severity.MEDIUM, "CIS-3.1.1", "CWE-940"),
    }
    proc_sys = Path("/proc/sys")
    for key, (expected, severity, control, cwe) in sysctl.items():
        path = proc_sys.joinpath(*key.split("."))
        actual = _read_text(path, limit=64)
        if actual is None:
            continue
        actual = actual.strip()
        if actual == expected:
            continue
        findings.append(
            _new_finding(
                target=target,
                title=f"Kernel parameter weak: {key}={actual} (expected {expected})",
                severity=severity,
                description=(
                    f"Sysctl ``{key}`` is ``{actual}``. The CIS Benchmark "
                    f"requires ``{expected}`` to harden the host against the "
                    "associated attack class."
                ),
                remediation=(
                    f"Set ``{key} = {expected}`` in ``/etc/sysctl.d/99-cis.conf`` "
                    "and reload with ``sysctl --system``."
                ),
                cwe=cwe,
                controls=[control, "NIST-CM-6"],
                evidence={"key": key, "actual": actual, "expected": expected},
            )
        )
    return findings


# ──────────────────────────────────────────────────────────────────────
# Network exposure


_LISTEN_STATE = "0A"  # TCP_LISTEN


def _parse_proc_net(text: str, *, ipv6: bool) -> list[tuple[str, int, int]]:
    out: list[tuple[str, int, int]] = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4 or parts[3] != _LISTEN_STATE:
            continue
        local = parts[1]
        host_hex, _, port_hex = local.partition(":")
        try:
            port = int(port_hex, 16)
            inode = int(parts[9])
        except (ValueError, IndexError):
            continue
        host = _decode_hex_addr(host_hex, ipv6=ipv6)
        out.append((host, port, inode))
    return out


def _decode_hex_addr(hex_addr: str, *, ipv6: bool) -> str:
    try:
        if ipv6:
            raw = bytes.fromhex(hex_addr)
            # Linux stores IPv6 as little-endian 32-bit words.
            words = [raw[i : i + 4][::-1] for i in range(0, 16, 4)]
            return str(ipaddress.IPv6Address(b"".join(words)))
        raw = bytes.fromhex(hex_addr)[::-1]
        return str(ipaddress.IPv4Address(raw))
    except (ValueError, ipaddress.AddressValueError):
        return hex_addr


def check_listening_ports(target: str) -> list[Finding]:
    if platform.system() != "Linux":
        return []
    findings: list[Finding] = []
    seen: set[tuple[str, int]] = set()
    sources = [
        ("/proc/net/tcp", False),
        ("/proc/net/tcp6", True),
    ]
    listeners: list[tuple[str, int]] = []
    for path, ipv6 in sources:
        text = _read_text(path)
        if not text:
            continue
        for host, port, _ in _parse_proc_net(text, ipv6=ipv6):
            key = (host, port)
            if key in seen:
                continue
            seen.add(key)
            listeners.append(key)
    public_listeners = [(h, p) for h, p in listeners if _is_public_bind(h)]
    if listeners:
        findings.append(
            _new_finding(
                target=target,
                title=f"{len(listeners)} TCP listener(s) on host",
                severity=Severity.INFO,
                description=(
                    "Inventory of TCP listeners observed via ``/proc/net/tcp*``."
                ),
                remediation=(
                    "Reconcile against the asset register; close ports that "
                    "do not have a documented service owner."
                ),
                controls=["CIS-3.4.1", "NIST-SC-7"],
                evidence={"listeners": [{"addr": h, "port": p} for h, p in listeners]},
            )
        )
    if public_listeners:
        findings.append(
            _new_finding(
                target=target,
                title=f"{len(public_listeners)} service(s) bound to public interface",
                severity=Severity.HIGH,
                description=(
                    "Sockets listen on a non-loopback address — they are "
                    "reachable from the network. Each public listener "
                    "expands the host's attack surface."
                ),
                remediation=(
                    "Bind services to ``127.0.0.1`` / ``::1`` when only the "
                    "local machine consumes them, or place an authenticated "
                    "reverse proxy in front."
                ),
                cwe="CWE-668",
                controls=["CIS-3.4.1", "NIST-SC-7", "PCI-1.2"],
                evidence={
                    "public_listeners": [
                        {"addr": h, "port": p} for h, p in public_listeners
                    ],
                },
            )
        )
    return findings


def _is_public_bind(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    if ip.is_loopback or ip.is_link_local or ip.is_unspecified:
        # 0.0.0.0 / :: are explicitly listening on every interface, which
        # is more exposed than loopback — flag them as public.
        if ip.is_unspecified:
            return True
        return False
    return not ip.is_private
