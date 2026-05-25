"""Static auditor for GitHub Actions workflow files.

Network-free analysis of every ``.github/workflows/*.yml`` under a
``REPO``-typed target. Surfaces the classes of misconfiguration that
have produced real-world supply-chain compromises:

- ``pull_request_target`` triggers that check out the PR ref and
  then run code from it (``actions/checkout`` with
  ``ref: ${{ github.event.pull_request.head.ref }}`` is the canonical
  pattern). Anyone who can open a PR gets arbitrary code execution
  in the privileged workflow context.
- ``run`` steps that interpolate untrusted ``${{ github.event.* }}``
  fields directly into shell commands → script injection.
- Unpinned third-party actions (``uses: foo/bar@main``) where a
  commit-SHA pin is the only safe option for non-vetted authors.
- Explicit secret echoing into ``run`` commands.

The auditor is intentionally conservative — every rule has a clean
remediation suggestion and a CWE mapping so the existing compliance
mapper picks them up.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from core.observability.logging import get_logger
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)


_DANGEROUS_EVENT_FIELDS = re.compile(
    r"\$\{\{\s*github\.event\.("
    r"issue\.title|issue\.body|"
    r"pull_request\.title|pull_request\.body|"
    r"pull_request\.head\.ref|pull_request\.head\.label|"
    r"comment\.body|"
    r"head_commit\.message"
    r")\s*\}\}"
)

_SECRET_INTERPOLATION = re.compile(r"\$\{\{\s*secrets\.([A-Z0-9_]+)\s*\}\}")
_THIRD_PARTY_USES = re.compile(r"^\s*uses:\s*([^\s@]+)@(.+)$")
_SHA_PIN = re.compile(r"^[0-9a-f]{40}$")


class WorkflowAuditScanner(Scanner):
    name = "workflow_audit"
    kind = ScannerKind.CONFIG
    supports_intensity = (
        ScanIntensity.PASSIVE,
        ScanIntensity.ACTIVE,
        ScanIntensity.INTRUSIVE,
    )
    requires_network = False
    default_timeout = 60

    def __init__(self, sandbox: Any = None, timeout: int | None = None) -> None:
        # The auditor walks the local filesystem; no sandbox required.
        # Constructor signature stays compatible with the Scanner base.
        super().__init__(sandbox, timeout=timeout)  # type: ignore[arg-type]

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if target.type not in (TargetType.REPO, TargetType.IAC):
            return []
        repo_path = self._resolve_repo_path(target)
        if repo_path is None:
            return []
        workflow_dir = repo_path / ".github" / "workflows"
        if not workflow_dir.is_dir():
            return []

        findings: list[Finding] = []
        for path in sorted(workflow_dir.glob("*.y*ml")):
            findings.extend(self._audit_file(path, target))
        return findings

    def _resolve_repo_path(self, target: Target) -> Path | None:
        meta = target.metadata if isinstance(target.metadata, dict) else {}
        explicit = meta.get("repo_path")
        if isinstance(explicit, str) and explicit:
            return Path(explicit)
        if target.type in (TargetType.REPO, TargetType.IAC):
            candidate = Path(target.value)
            if candidate.is_dir():
                return candidate
        return None

    def _audit_file(self, path: Path, target: Target) -> list[Finding]:
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            logger.warning(
                "red_agent.workflow_audit.parse_failed",
                extra={"path": str(path), "err": str(exc)},
            )
            return []
        if not isinstance(doc, dict):
            return []

        findings: list[Finding] = []
        rel_path = self._relative(path, target)

        triggers = doc.get(True) or doc.get("on")
        findings.extend(
            self._check_pull_request_target(triggers, doc, rel_path, target)
        )
        findings.extend(self._check_steps(doc, rel_path, target))
        return findings

    def _relative(self, path: Path, target: Target) -> str:
        meta = target.metadata if isinstance(target.metadata, dict) else {}
        repo_path = meta.get("repo_path") or target.value
        try:
            return str(path.relative_to(repo_path))
        except (TypeError, ValueError):
            return str(path)

    def _check_pull_request_target(
        self,
        triggers: Any,
        doc: dict[str, Any],
        rel_path: str,
        target: Target,
    ) -> list[Finding]:
        if not self._has_trigger(triggers, "pull_request_target"):
            return []
        # Look for any job that checks out the PR head and runs.
        risky_jobs: list[str] = []
        jobs = doc.get("jobs") or {}
        if not isinstance(jobs, dict):
            return []
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            steps = job.get("steps") or []
            if not isinstance(steps, list):
                continue
            checks_out_pr = False
            runs_pr_code = False
            for step in steps:
                if not isinstance(step, dict):
                    continue
                uses = str(step.get("uses", ""))
                if uses.startswith("actions/checkout"):
                    with_ref = (step.get("with") or {}).get("ref", "")
                    if "pull_request.head" in str(with_ref):
                        checks_out_pr = True
                if "run" in step:
                    runs_pr_code = True
            if checks_out_pr and runs_pr_code:
                risky_jobs.append(str(job_name))

        if not risky_jobs:
            return []
        return [
            Finding(
                scanner=self.name,
                title=f"pull_request_target executes PR-supplied code ({rel_path})",
                description=(
                    "Workflow uses ``pull_request_target`` and checks "
                    "out the PR head ref before running code. Any "
                    "external contributor can hijack the privileged "
                    f"workflow context. Affected job(s): {', '.join(risky_jobs)}."
                ),
                severity=Severity.CRITICAL,
                target=target.value,
                endpoint=rel_path,
                evidence={"jobs": risky_jobs},
                cwe="CWE-913",
                remediation=(
                    "Switch to ``pull_request`` (untrusted context) or "
                    "split the workflow so privileged steps run only "
                    "after a label gate."
                ),
            )
        ]

    def _has_trigger(self, triggers: Any, event: str) -> bool:
        if isinstance(triggers, str):
            return triggers == event
        if isinstance(triggers, list):
            return event in triggers
        if isinstance(triggers, dict):
            return event in triggers
        return False

    def _check_steps(
        self, doc: dict[str, Any], rel_path: str, target: Target
    ) -> list[Finding]:
        findings: list[Finding] = []
        jobs = doc.get("jobs") or {}
        if not isinstance(jobs, dict):
            return findings

        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            steps = job.get("steps") or []
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                run_block = step.get("run")
                if isinstance(run_block, str):
                    findings.extend(
                        self._inspect_run(run_block, rel_path, str(job_name), target)
                    )
                uses = step.get("uses")
                if isinstance(uses, str):
                    finding = self._inspect_uses(uses, rel_path, str(job_name), target)
                    if finding:
                        findings.append(finding)
        return findings

    def _inspect_run(
        self, run: str, rel_path: str, job_name: str, target: Target
    ) -> list[Finding]:
        out: list[Finding] = []
        if _DANGEROUS_EVENT_FIELDS.search(run):
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Untrusted github.event.* interpolation in `run` ({rel_path}:{job_name})",
                    description=(
                        "Step interpolates a user-controlled "
                        "github.event.* field directly into the shell "
                        "command. Trivially exploitable as script "
                        "injection."
                    ),
                    severity=Severity.HIGH,
                    target=target.value,
                    endpoint=rel_path,
                    evidence={"job": job_name, "run_excerpt": run[:200]},
                    cwe="CWE-78",
                    remediation=(
                        "Capture the value into an env var first and "
                        "reference ``$VAR`` from the shell, or run a "
                        "script that parses stdin."
                    ),
                )
            )
        if _SECRET_INTERPOLATION.search(run):
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Secret echoed into `run` command ({rel_path}:{job_name})",
                    description=(
                        "Step interpolates a ``secrets.*`` value "
                        "directly into a shell command. Risk of leakage "
                        "via process listings, build logs, and "
                        "downstream tools."
                    ),
                    severity=Severity.MEDIUM,
                    target=target.value,
                    endpoint=rel_path,
                    evidence={"job": job_name, "run_excerpt": run[:200]},
                    cwe="CWE-532",
                    remediation=(
                        "Bind the secret to ``env:`` and reference the "
                        "env var inside the script."
                    ),
                )
            )
        return out

    def _inspect_uses(
        self, uses: str, rel_path: str, job_name: str, target: Target
    ) -> Finding | None:
        match = _THIRD_PARTY_USES.match("uses: " + uses)
        if not match:
            return None
        ref_name, ref_value = match.group(1), match.group(2).strip()
        # First-party actions ship in the ``actions/`` namespace —
        # those are pinned by GitHub and safe to take by tag.
        owner = ref_name.split("/", 1)[0]
        if owner in {"actions", "github"}:
            return None
        if _SHA_PIN.match(ref_value):
            return None
        return Finding(
            scanner=self.name,
            title=f"Third-party action not pinned to a SHA: {ref_name}@{ref_value}",
            description=(
                "Third-party action is referenced by tag/branch. A "
                "compromised maintainer can move the tag to malicious "
                "code. Pin to a 40-char commit SHA."
            ),
            severity=Severity.MEDIUM,
            target=target.value,
            endpoint=rel_path,
            evidence={"job": job_name, "uses": uses},
            cwe="CWE-829",
            remediation=(
                "Replace the tag with the full commit SHA, e.g. "
                "``uses: owner/repo@<sha>  # v1.2.3``."
            ),
        )
