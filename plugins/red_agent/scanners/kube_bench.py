"""kube-bench Kubernetes CIS Benchmark scanner adapter.

Runs Aqua's kube-bench against a Kubernetes node / control-plane to
audit configuration against the CIS Kubernetes Benchmark (1.7+ as
shipped by the upstream image). Each FAIL entry produces a finding;
WARN entries are kept at LOW severity; PASS / INFO entries are dropped.

Authentication & filesystem access: kube-bench inspects local node
configs (``/etc/kubernetes``, kubelet, etcd …). The SandboxRunner mount
strategy must expose those paths via host bind mounts when scanning a
real node; for in-cluster execution the operator typically runs the
scanner as a DaemonSet pod and passes the JSON output back through this
adapter via ``Target.value`` pointing to the captured artifact.
"""

from __future__ import annotations

import json
from typing import Any

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

_STATUS_TO_SEVERITY: dict[str, Severity] = {
    "FAIL": Severity.HIGH,
    "WARN": Severity.LOW,
    "INFO": Severity.INFO,
    "PASS": Severity.INFO,
}


class KubeBenchScanner(Scanner):
    name = "kube_bench"
    kind = ScannerKind.CONFIG
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = "aquasec/kube-bench:latest"
    requires_network = False
    default_timeout = 600

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if target.type != TargetType.K8S_CLUSTER:
            return []
        argv = ["--json", "run"]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=False,
            scanner=self.name,
        )
        return self._parse(result.stdout, target)

    def _parse(self, json_text: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        try:
            doc = json.loads(json_text)
        except json.JSONDecodeError:
            return findings

        # kube-bench output: { "Controls": [ { "tests": [ { "results": [...] } ] } ] }
        controls = doc.get("Controls", []) if isinstance(doc, dict) else doc
        for ctl in controls or []:
            if not isinstance(ctl, dict):
                continue
            for test in ctl.get("tests", []) or []:
                if not isinstance(test, dict):
                    continue
                for r in test.get("results", []) or []:
                    if not isinstance(r, dict):
                        continue
                    status = str(r.get("status", "")).upper()
                    if status not in {"FAIL", "WARN"}:
                        continue
                    findings.append(_finding_from_result(r, ctl, target))
        return findings


def _finding_from_result(
    r: dict[str, Any], ctl: dict[str, Any], target: Target
) -> Finding:
    status = str(r.get("status", "")).upper()
    severity = _STATUS_TO_SEVERITY.get(status, Severity.MEDIUM)
    test_number = r.get("test_number") or r.get("test_id") or ""
    test_desc = r.get("test_desc") or ""
    return Finding(
        scanner="kube_bench",
        title=f"CIS-K8s {test_number}: {test_desc}",
        description=r.get("audit") or test_desc,
        severity=severity,
        target=target.value,
        evidence={
            "control_version": ctl.get("version"),
            "control_id": ctl.get("id"),
            "test_number": test_number,
            "scored": r.get("scored"),
            "expected_result": r.get("expected_result"),
            "actual_value": r.get("actual_value"),
            "status": status,
        },
        raw=r,
        remediation=r.get("remediation") or "Apply CIS Kubernetes Benchmark guidance.",
    )
