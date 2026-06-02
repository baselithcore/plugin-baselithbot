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

This package re-exports the same public surface previously exposed by
the ``_self_posture_checks`` module so existing import paths keep working.
"""

from __future__ import annotations

from typing import Iterable

from plugins.red_agent.models import Finding
from plugins.red_agent.scanners._self_posture_checks._fs_auth import (
    check_docker_socket,
    check_env_secrets,
    check_runtime_context,
    check_sshd_config,
    check_sudoers_nopasswd,
    check_suid_binaries,
    check_world_writable,
)
from plugins.red_agent.scanners._self_posture_checks._helpers import CheckFn
from plugins.red_agent.scanners._self_posture_checks._os_net import (
    check_kernel_hardening,
    check_listening_ports,
    check_os_release,
)


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


__all__ = [
    "ALL_CHECKS",
    "CheckFn",
    "check_docker_socket",
    "check_env_secrets",
    "check_kernel_hardening",
    "check_listening_ports",
    "check_os_release",
    "check_runtime_context",
    "check_sshd_config",
    "check_sudoers_nopasswd",
    "check_suid_binaries",
    "check_world_writable",
    "run_all",
]
