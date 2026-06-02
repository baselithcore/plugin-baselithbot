"""Shared primitives for the self-posture checks.

Finding constructor, file readers, and the ``CheckFn`` alias used to
register each check.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from plugins.red_agent.models import Finding, Severity

CheckFn = Callable[[str], list[Finding]]


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
