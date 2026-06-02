"""Filesystem, authentication, container and runtime posture checks.

SUID binaries, world-writable system files, sshd config, sudo NOPASSWD
rules, docker-socket exposure, secret-shaped env vars, and the
orchestrator's own runtime context.
"""

from __future__ import annotations

import os
import platform
import re
import socket
import stat
from pathlib import Path
from typing import Any

from plugins.red_agent.models import Finding, Severity
from plugins.red_agent.scanners._self_posture_checks._helpers import (
    _file_mode,
    _new_finding,
    _read_text,
)


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
