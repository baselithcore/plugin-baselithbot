"""Self-posture scanner.

Audits the host running the orchestrator against a CIS-Benchmark-aligned
checklist. Pure-Python: no subprocess, no network. Findings are tagged
with CIS / NIST 800-53 control IDs so the existing compliance enricher
slots them into the framework dashboards without further mapping.

The scanner is opt-in via the ``self_posture`` adapter and accepts only
``Target`` records of type ``SYSTEM`` (kind ``host`` with the value
``system:local``). Other target types are skipped.

Why pure-Python:

* The orchestrator commonly runs in stripped containers without
  ``find`` / ``ss`` / ``lsof`` / ``ssh-audit`` available.
* Subprocess calls cross sandbox boundaries and complicate the audit
  chain — every byte of evidence here came from a file the process
  could read with its own credentials.
* Each check is independent and degrades gracefully on macOS / WSL.
"""

from __future__ import annotations

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding, ScanIntensity, Target, TargetType
from plugins.red_agent.scanners._self_posture_checks import run_all
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)


class SelfPostureScanner(Scanner):
    """Audit the host running the orchestrator."""

    name = "self_posture"
    kind = ScannerKind.CONFIG
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = ""  # in-process; no sandbox image
    requires_network = False
    default_timeout = 120

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        del intensity
        if target.type != TargetType.SYSTEM:
            return []
        target_value = target.value or "system:local"
        try:
            findings = run_all(target_value)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "self_posture.run_failed",
                extra={"err": str(exc), "target": target_value},
            )
            return []
        logger.info(
            "self_posture.completed",
            extra={"target": target_value, "findings": len(findings)},
        )
        return findings
