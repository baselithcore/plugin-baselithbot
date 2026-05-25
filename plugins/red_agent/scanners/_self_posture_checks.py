"""Pure-Python posture checks for the host running the orchestrator.

Each check is a small function returning ``list[Finding]``. They read
``/proc``, ``/etc``, ``/var`` directly — no subprocess, no network — so
the same code works inside a sandbox, a container, or a stripped
read-only mount. Checks degrade gracefully on macOS / unsupported
platforms by returning an empty list.

Findings are tagged with:

* ``cwe`` — primary CWE identifier (e.g. ``CWE-732``).
* ``controls`` — CIS Benchmark + NIST 800-53 IDs that govern the issue.
* ``evidence`` — structured payload (file paths, parsed values,
  matching lines) the UI surfaces in the Finding detail modal.

Severity is calibrated against the CIS Benchmark Level 1 (workstation)
profile; operators tighten or relax via the standard triage flow.
"""

from __future__ import annotations

import ipaddress
import os
import platform
import re
import socket
import stat
from pathlib import Path
from typing import Any, Callable, Iterable

from plugins.red_agent.models import Finding, Severity

CheckFn = Callable[[str], list[Finding]]


# ──────────────────────────────────────────────────────────────────────
# Helpers


def _new_finding(
    *,
    target: str,
    title: str,
    severity: Severity,
    description: str,
    remediation: str,
    cwe: str | None = None,
    controls: list[str] | None = None,
    evidence: dict[str, Any] | None = None,
    endpoint: str | None = None,
) -> Finding:
    return Finding(
        scanner="self_posture",
        title=title,
        severity=severity,
        description=description,
        remediation=remediation,
        target=target,
        endpoint=endpoint,
        cwe=cwe,
        controls=controls or [],
        evidence=evidence or {},
    )


def _read_text(path: str | Path, *, limit: int = 512 * 1024) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return None


def _file_mode(path: str | Path) -> int | None:
    try:
        return os.stat(path).st_mode
    except OSError:
        return None


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


# ──────────────────────────────────────────────────────────────────────
# Filesystem hardening


_SYSTEM_PATH_DIRS = (
    "/usr/bin",
    "/usr/sbin",
    "/usr/local/bin",
    "/usr/local/sbin",
    "/bin",
    "/sbin",
)
_KNOWN_SUID_ALLOWLIST = {
    "sudo",
    "su",
    "mount",
    "umount",
    "passwd",
    "newgrp",
    "chsh",
    "chfn",
    "ping",
    "ping6",
    "pkexec",
    "doas",
}


def check_suid_binaries(target: str) -> list[Finding]:
    if platform.system() != "Linux":
        return []
    suspicious: list[dict[str, Any]] = []
    for d in _SYSTEM_PATH_DIRS:
        try:
            for entry in os.scandir(d):
                if not entry.is_file(follow_symlinks=False):
                    continue
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if not (st.st_mode & stat.S_ISUID):
                    continue
                if entry.name in _KNOWN_SUID_ALLOWLIST:
                    continue
                suspicious.append(
                    {
                        "path": entry.path,
                        "mode": oct(st.st_mode & 0o7777),
                        "uid": st.st_uid,
                    }
                )
        except OSError:
            continue
    if not suspicious:
        return []
    return [
        _new_finding(
            target=target,
            title=f"{len(suspicious)} unexpected SUID binary",
            severity=Severity.HIGH,
            description=(
                "SUID binaries outside the curated allowlist were found on "
                "PATH. Each is a potential local privilege escalation "
                "vector — review whether the SUID bit is required."
            ),
            remediation=(
                "If SUID is not strictly required, drop it with "
                "``chmod u-s <path>``. Otherwise file an exception in the "
                "asset register and constrain caller capabilities."
            ),
            cwe="CWE-269",
            controls=["CIS-6.1.10", "NIST-AC-6"],
            evidence={"binaries": suspicious[:128]},
        )
    ]


def check_world_writable(target: str) -> list[Finding]:
    if platform.system() != "Linux":
        return []
    risky: list[dict[str, Any]] = []
    candidates = ("/etc", "/etc/cron.d", "/var/log")
    for d in candidates:
        try:
            for entry in os.scandir(d):
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if st.st_mode & stat.S_IWOTH and not (st.st_mode & stat.S_ISVTX):
                    risky.append(
                        {
                            "path": entry.path,
                            "mode": oct(st.st_mode & 0o7777),
                        }
                    )
        except OSError:
            continue
    if not risky:
        return []
    return [
        _new_finding(
            target=target,
            title=f"{len(risky)} world-writable system file",
            severity=Severity.HIGH,
            description=(
                "Files inside system directories grant write to ``other``. "
                "An unprivileged user can replace configuration or crontab "
                "entries to escalate privileges or persist."
            ),
            remediation=(
                "Strip the world-writable bit with ``chmod o-w <path>`` and "
                "audit recent modifications to the file."
            ),
            cwe="CWE-732",
            controls=["CIS-6.1.4", "NIST-AC-3"],
            evidence={"files": risky[:128]},
        )
    ]


# ──────────────────────────────────────────────────────────────────────
# SSH / authentication


_SSHD_RULES = {
    "permitrootlogin": (
        ("yes", "without-password"),
        Severity.HIGH,
        "Root SSH login is enabled.",
        "CIS-5.3.7",
        "CWE-269",
    ),
    "passwordauthentication": (
        ("yes",),
        Severity.MEDIUM,
        "Password authentication is enabled — prefer key-based auth.",
        "CIS-5.3.4",
        "CWE-521",
    ),
    "permitemptypasswords": (
        ("yes",),
        Severity.CRITICAL,
        "Empty passwords are accepted.",
        "CIS-5.3.5",
        "CWE-258",
    ),
    "x11forwarding": (
        ("yes",),
        Severity.LOW,
        "X11 forwarding is enabled — broadens lateral-movement surface.",
        "CIS-5.3.6",
        "CWE-668",
    ),
    "permituserenvironment": (
        ("yes",),
        Severity.MEDIUM,
        "User environment files are honoured during SSH session setup.",
        "CIS-5.3.10",
        "CWE-732",
    ),
}


def check_sshd_config(target: str) -> list[Finding]:
    text = _read_text("/etc/ssh/sshd_config")
    if text is None:
        return []
    findings: list[Finding] = []
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if " " not in s:
            continue
        key, _, value = s.partition(" ")
        parsed[key.strip().lower()] = value.strip().split()[0].lower()

    for key, (bad, severity, msg, control, cwe) in _SSHD_RULES.items():
        actual = parsed.get(key)
        if actual is None or actual not in bad:
            continue
        findings.append(
            _new_finding(
                target=target,
                title=f"sshd_config weak: {key}={actual}",
                severity=severity,
                description=msg,
                remediation=(
                    f"Edit ``/etc/ssh/sshd_config`` to set a hardened value "
                    f"for ``{key}`` and reload sshd."
                ),
                cwe=cwe,
                controls=[control, "NIST-AC-7"],
                evidence={"directive": key, "value": actual},
            )
        )
    return findings


# ──────────────────────────────────────────────────────────────────────
# Sudo


def check_sudoers_nopasswd(target: str) -> list[Finding]:
    files = ["/etc/sudoers"]
    sudoers_d = Path("/etc/sudoers.d")
    if sudoers_d.is_dir():
        try:
            files.extend(str(p) for p in sudoers_d.iterdir() if p.is_file())
        except OSError:
            pass
    matches: list[dict[str, Any]] = []
    pattern = re.compile(r"^\s*[^#].*NOPASSWD", re.IGNORECASE | re.MULTILINE)
    for f in files:
        text = _read_text(f)
        if text is None:
            continue
        for m in pattern.finditer(text):
            matches.append({"file": f, "rule": m.group(0).strip()[:200]})
    if not matches:
        return []
    return [
        _new_finding(
            target=target,
            title=f"{len(matches)} sudo NOPASSWD rule",
            severity=Severity.HIGH,
            description=(
                "Sudo rules grant command execution without re-authentication. "
                "If any caller is compromised, lateral escalation to root is "
                "trivial."
            ),
            remediation=(
                "Replace ``NOPASSWD`` rules with explicit per-command grants "
                "and short ``timestamp_timeout``. Audit which automation "
                "still requires it."
            ),
            cwe="CWE-269",
            controls=["CIS-5.2.5", "NIST-AC-6"],
            evidence={"rules": matches[:64]},
        )
    ]


# ──────────────────────────────────────────────────────────────────────
# Container / docker exposure


def check_docker_socket(target: str) -> list[Finding]:
    sock = "/var/run/docker.sock"
    mode = _file_mode(sock)
    if mode is None:
        return []
    findings: list[Finding] = []
    if mode & stat.S_IROTH or mode & stat.S_IWOTH:
        findings.append(
            _new_finding(
                target=target,
                title="Docker socket world-readable/writable",
                severity=Severity.CRITICAL,
                description=(
                    "``/var/run/docker.sock`` is accessible to all users. "
                    "Any local user can trivially escalate to root by "
                    "spawning a privileged container that mounts the host "
                    "filesystem."
                ),
                remediation=(
                    "Restrict the socket to ``root:docker`` with ``660`` and "
                    "keep the ``docker`` group membership minimal. Prefer "
                    "rootless docker / podman where possible."
                ),
                cwe="CWE-732",
                controls=["CIS-Docker-2.1", "NIST-AC-3"],
                evidence={"path": sock, "mode": oct(mode & 0o7777)},
            )
        )
    return findings


# ──────────────────────────────────────────────────────────────────────
# Process environment secrets


_SECRET_ENV_PATTERNS = (
    re.compile(r"(?i)^(aws|gcp|azure|github|gh|gitlab|do|hetzner)_.*"),
    re.compile(r"(?i).*(secret|token|api[_-]?key|password|passwd|credential).*"),
)


def check_env_secrets(target: str) -> list[Finding]:
    leaks: list[dict[str, Any]] = []
    for k, v in os.environ.items():
        if not v:
            continue
        if any(p.match(k) for p in _SECRET_ENV_PATTERNS):
            leaks.append({"name": k, "length": len(v)})
    if not leaks:
        return []
    return [
        _new_finding(
            target=target,
            title=f"{len(leaks)} secret-shaped environment variable in process env",
            severity=Severity.MEDIUM,
            description=(
                "The orchestrator process inherits environment variables "
                "matching common secret naming conventions. They are visible "
                "to ``/proc/<pid>/environ`` (mode 600 on modern kernels) and "
                "appear in core dumps, crash reports and stack traces."
            ),
            remediation=(
                "Move credentials into a secret manager (Vault, AWS Secrets "
                "Manager, sealed-secrets) and load them only at the call "
                "site. Keep ``SecretStr`` wrappers around in-memory values."
            ),
            cwe="CWE-526",
            controls=["CIS-5.4.1", "NIST-IA-5"],
            evidence={"variables": leaks[:64]},
        )
    ]


# ──────────────────────────────────────────────────────────────────────
# Process / runtime context


def check_runtime_context(target: str) -> list[Finding]:
    findings: list[Finding] = []
    uid = os.geteuid() if hasattr(os, "geteuid") else None
    severity = Severity.HIGH if uid == 0 else Severity.INFO
    findings.append(
        _new_finding(
            target=target,
            title=(
                "Orchestrator running as root"
                if uid == 0
                else f"Orchestrator running as uid={uid}"
            ),
            severity=severity,
            description=(
                "The Red Agent process executed this scan with the listed "
                "uid. Running as root expands the blast radius of any "
                "deserialisation, command injection or path traversal bug."
            ),
            remediation=(
                "Run the backend under a dedicated low-privilege account "
                "(systemd ``DynamicUser=yes`` / ``User=baselith``)."
            )
            if uid == 0
            else (
                "No action — uid is non-root. Periodically verify the "
                "service unit pins the user."
            ),
            cwe="CWE-250" if uid == 0 else None,
            controls=["CIS-5.4.4", "NIST-AC-6"],
            evidence={
                "euid": uid,
                "pid": os.getpid(),
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
            },
        )
    )
    return findings


# ──────────────────────────────────────────────────────────────────────
# Aggregate registry


ALL_CHECKS: tuple[CheckFn, ...] = (
    check_os_release,
    check_runtime_context,
    check_kernel_hardening,
    check_listening_ports,
    check_suid_binaries,
    check_world_writable,
    check_sshd_config,
    check_sudoers_nopasswd,
    check_docker_socket,
    check_env_secrets,
)


def run_all(target: str, *, checks: Iterable[CheckFn] | None = None) -> list[Finding]:
    out: list[Finding] = []
    for fn in checks or ALL_CHECKS:
        try:
            out.extend(fn(target))
        except Exception:  # noqa: BLE001 - best-effort: a broken check must not abort the run
            continue
    return out
