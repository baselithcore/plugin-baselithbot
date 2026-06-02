"""The ``BinaryAnalyzerScanner`` class and its orchestration ``run`` loop.

Pulls together the parser, IOC sweep, and the finding-builder mixins to
produce the full finding set for an uploaded sample.
"""

from __future__ import annotations

from pathlib import Path

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners._binary_iocs import (
    extract_iocs,
    extract_strings,
    suspicious_imports,
)
from plugins.red_agent.scanners._binary_parser import parse_binary
from plugins.red_agent.scanners.base import Scanner, ScannerKind
from plugins.red_agent.scanners.binary_analyzer._helpers import (
    _MAX_BYTES,
    _hash_all,
    _run_yara,
)
from plugins.red_agent.scanners.binary_analyzer._ioc_findings import _IocFindingsMixin
from plugins.red_agent.scanners.binary_analyzer._pe_findings import _PeFindingsMixin


class BinaryAnalyzerScanner(_PeFindingsMixin, _IocFindingsMixin, Scanner):
    """Pure-Python static analysis pass over an uploaded binary."""

    name = "binary_analyzer"
    kind = ScannerKind.SAST
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = ""  # in-process; no sandbox image
    requires_network = False
    default_timeout = 300

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        del intensity
        if target.type != TargetType.BINARY:
            return []
        path_value = str(target.metadata.get("path") or "")
        if not path_value:
            return [self._infrastructure_finding(target, "missing_quarantine_path")]
        path = Path(path_value)
        if not path.is_file():
            return [self._infrastructure_finding(target, f"missing_file:{path}")]

        try:
            data = path.read_bytes()[:_MAX_BYTES]
        except OSError as e:
            return [self._infrastructure_finding(target, f"read_failed:{e}")]

        digests = _hash_all(data)
        parsed = parse_binary(data)
        strings = extract_strings(data)
        iocs = extract_iocs(strings)
        suspicious = suspicious_imports(parsed.imports)
        yara_hits = _run_yara(path, data)

        findings: list[Finding] = []
        # Always emit an "Overview" INFO finding so the report has a
        # canonical record even when no malicious indicators trip.
        findings.append(
            self._overview_finding(target, parsed, digests, len(data), iocs=iocs)
        )

        findings.extend(self._entropy_findings(target, parsed))
        findings.extend(self._ioc_findings(target, iocs))
        findings.extend(self._import_findings(target, suspicious))
        findings.extend(self._yara_findings(target, yara_hits))
        findings.extend(self._signature_findings(target, parsed))
        findings.extend(self._private_key_findings(target, iocs))
        findings.extend(self._mitigation_findings(target, parsed))
        findings.extend(self._packer_findings(target, parsed))
        findings.extend(self._overlay_findings(target, parsed))
        findings.extend(self._timestamp_findings(target, parsed))
        findings.extend(self._embedded_findings(target, parsed))
        findings.extend(self._mime_mismatch_findings(target, parsed))
        return findings
