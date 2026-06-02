"""Structural / PE-oriented finding builders for the binary analyzer.

Mixin providing the overview, entropy, YARA, signature, mitigation,
packer, overlay, timestamp, embedded-binary, MIME-mismatch and
infrastructure finding builders. Combined into ``BinaryAnalyzerScanner``.
"""

from __future__ import annotations

from typing import Any

from plugins.red_agent.models import Finding, Severity, Target
from plugins.red_agent.scanners._binary_advanced import missing_mitigations
from plugins.red_agent.scanners._binary_parser import ParseResult
from plugins.red_agent.scanners.binary_analyzer._helpers import (
    _HIGH_ENTROPY_THRESHOLD,
    _yara_severity,
)
from plugins.red_agent.scanners.binary_analyzer._render import (
    _render_overview_markdown,
)


class _PeFindingsMixin:
    """Structural finding builders mixed into ``BinaryAnalyzerScanner``."""

    name: str

    def _overview_finding(
        self,
        target: Target,
        parsed: ParseResult,
        digests: dict[str, str],
        size: int,
        iocs: dict[str, list[str]] | None = None,
    ) -> Finding:
        return Finding(
            scanner=self.name,
            title=f"Binary overview: {target.metadata.get('filename') or target.value}",
            description=_render_overview_markdown(
                target=target,
                parsed=parsed,
                digests=digests,
                size=size,
                iocs=iocs or {},
            ),
            severity=Severity.INFO,
            target=target.value,
            evidence={
                "filename": target.metadata.get("filename"),
                "format": parsed.file_format,
                "bitness": parsed.bitness,
                "machine": parsed.machine,
                "size": size,
                "digests": digests,
                "sections": [s.__dict__ for s in parsed.sections],
                "imports_count": len(parsed.imports),
                "exports_count": len(parsed.exports),
                "libraries": parsed.libraries[:64],
                "is_signed": parsed.is_signed,
                "is_dotnet": parsed.is_dotnet,
                "has_tls_callbacks": parsed.has_tls_callbacks,
                "imphash": parsed.advanced.imphash,
                "rich_header_xor_key": (
                    f"0x{parsed.advanced.rich_xor_key:08x}"
                    if parsed.advanced.rich_xor_key
                    else ""
                ),
                "rich_header_entries": [
                    e.to_dict() for e in parsed.advanced.rich_header
                ],
                "mitigations": parsed.advanced.mitigations,
                "missing_mitigations": missing_mitigations(
                    parsed.advanced.dll_characteristics
                )
                if parsed.file_format == "pe"
                else [],
                "overlay": {
                    "offset": parsed.advanced.overlay_offset,
                    "size": parsed.advanced.overlay_size,
                    "entropy": parsed.advanced.overlay_entropy,
                },
                "packer_hits": parsed.advanced.packer_hits,
                "embedded_offsets": [
                    {"format": k, "offset": o}
                    for k, o in parsed.advanced.embedded_offsets
                ],
                "timestamp_anomaly": parsed.advanced.timestamp_anomaly,
                "parser_notes": parsed.notes,
            },
            raw=parsed.to_dict(),
            remediation=(
                "Pivot the SHA-256 against your threat-intel store "
                "(MISP/OpenCTI/VT) and the imphash against historical "
                "campaigns before approving the binary."
            ),
        )

    def _entropy_findings(self, target: Target, parsed: ParseResult) -> list[Finding]:
        out: list[Finding] = []
        for section in parsed.sections:
            if section.entropy < _HIGH_ENTROPY_THRESHOLD:
                continue
            severity = Severity.HIGH if section.entropy >= 7.6 else Severity.MEDIUM
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"High-entropy section `{section.name}` (likely packed)",
                    description=(
                        f"Section `{section.name}` has Shannon entropy "
                        f"{section.entropy:.2f} ≥ {_HIGH_ENTROPY_THRESHOLD}. "
                        "This is consistent with packing, encryption, or "
                        "embedded compressed payload — common to "
                        "malware loaders and crypters."
                    ),
                    severity=severity,
                    cwe="CWE-506",
                    target=target.value,
                    evidence={
                        "section": section.name,
                        "size": section.size,
                        "entropy": round(section.entropy, 4),
                        "flags": section.flags,
                    },
                    remediation=(
                        "Detonate in an isolated sandbox to obtain the "
                        "unpacked payload, then re-run static analysis "
                        "and YARA on the dumped image."
                    ),
                )
            )
        return out

    def _yara_findings(
        self, target: Target, hits: list[dict[str, Any]]
    ) -> list[Finding]:
        out: list[Finding] = []
        for hit in hits:
            sev = _yara_severity(hit.get("tags") or [])
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"YARA match: {hit.get('rule')}",
                    description=(
                        f"Rule `{hit.get('rule')}` matched the sample. "
                        f"Tags: {', '.join(hit.get('tags') or []) or 'none'}."
                    ),
                    severity=sev,
                    target=target.value,
                    evidence=hit,
                    remediation=(
                        "Treat the sample as the threat described by the "
                        "matched rule until a human analyst confirms a "
                        "false positive."
                    ),
                )
            )
        return out

    def _signature_findings(self, target: Target, parsed: ParseResult) -> list[Finding]:
        if parsed.file_format != "pe":
            return []
        if parsed.is_signed:
            return []
        return [
            Finding(
                scanner=self.name,
                title="Unsigned PE binary",
                description=(
                    "PE has no Authenticode signature. Unsigned executables "
                    "cannot be attributed to a publisher and bypass "
                    "common allow-list controls only via exception."
                ),
                severity=Severity.LOW,
                cwe="CWE-345",
                target=target.value,
                evidence={"format": "pe", "signed": False},
                remediation=(
                    "Require the binary to be code-signed with a vetted "
                    "Authenticode certificate before deployment, or add "
                    "an explicit allow-list exception."
                ),
            )
        ]

    def _mitigation_findings(
        self, target: Target, parsed: ParseResult
    ) -> list[Finding]:
        if parsed.file_format != "pe":
            return []
        missing = missing_mitigations(parsed.advanced.dll_characteristics)
        if not missing:
            return []
        # Severity scales with which mitigations are missing — DEP/ASLR
        # absence on a 64-bit binary in 2026 is a hard fail.
        severity = (
            Severity.HIGH
            if any(m in missing for m in ("NX_COMPAT", "DYNAMIC_BASE"))
            else Severity.MEDIUM
        )
        return [
            Finding(
                scanner=self.name,
                title=f"Missing exploit mitigations: {', '.join(missing)}",
                description=(
                    "PE optional header lacks one or more modern "
                    "exploit-mitigation flags. Each missing flag widens "
                    "the attacker's primitive set: DYNAMIC_BASE → no "
                    "ASLR, NX_COMPAT → executable stack/heap, GUARD_CF → "
                    "no Control Flow Guard against indirect-call hijack."
                ),
                severity=severity,
                cwe="CWE-693",
                target=target.value,
                evidence={
                    "missing": missing,
                    "present": parsed.advanced.mitigations,
                    "dll_characteristics": (
                        f"0x{parsed.advanced.dll_characteristics:04x}"
                    ),
                    "d3fend": ["D3-EAL", "D3-PSEP"],
                },
                remediation=(
                    "Re-link with `/DYNAMICBASE /NXCOMPAT /HIGHENTROPYVA "
                    "/GUARD:CF` (MSVC) or `-fcf-protection=full -Wl,-z,"
                    "relro,-z,now -pie` (clang/gcc) before deployment."
                ),
            )
        ]

    def _packer_findings(self, target: Target, parsed: ParseResult) -> list[Finding]:
        hits = parsed.advanced.packer_hits
        if not hits:
            return []
        return [
            Finding(
                scanner=self.name,
                title=f"Packer signature: {', '.join(hits)}",
                description=(
                    "Section names match well-known packer/protector "
                    "fingerprints. Packed binaries hide their payload "
                    "until runtime; static analysis past this point is "
                    "structurally limited until the sample is unpacked."
                ),
                severity=Severity.HIGH,
                cwe="CWE-506",
                target=target.value,
                evidence={
                    "packers": hits,
                    "sections": [s.name for s in parsed.sections],
                    "attack": ["T1027.002"],  # Software Packing
                },
                remediation=(
                    "Run an unpacker (UPX -d, x64dbg + Scylla, unipacker) "
                    "and re-submit the dumped image for analysis."
                ),
            )
        ]

    def _overlay_findings(self, target: Target, parsed: ParseResult) -> list[Finding]:
        adv = parsed.advanced
        if adv.overlay_size <= 0:
            return []
        # Small overlays are usually Authenticode signatures or build-id
        # blobs and don't deserve a finding.
        if adv.overlay_size < 256 and adv.overlay_entropy < 6.0:
            return []
        severity = (
            Severity.HIGH
            if adv.overlay_entropy >= 7.5
            else Severity.MEDIUM
            if adv.overlay_entropy >= 6.5
            else Severity.LOW
        )
        return [
            Finding(
                scanner=self.name,
                title=(
                    f"Overlay {adv.overlay_size} bytes "
                    f"(entropy {adv.overlay_entropy:.2f})"
                ),
                description=(
                    "Bytes appended after the last PE section. Used by "
                    "loaders to stage encrypted payloads, configuration "
                    "blobs, or piggybacked secondary executables."
                ),
                severity=severity,
                cwe="CWE-506",
                target=target.value,
                evidence={
                    "offset": adv.overlay_offset,
                    "size": adv.overlay_size,
                    "entropy": adv.overlay_entropy,
                    "attack": ["T1027.009"],  # Embedded Payloads
                },
                remediation=(
                    "Extract the overlay (`dd skip=<offset>`) and "
                    "recursively re-scan; benign cases are Authenticode "
                    "signatures or installer manifests."
                ),
            )
        ]

    def _timestamp_findings(self, target: Target, parsed: ParseResult) -> list[Finding]:
        anomaly = parsed.advanced.timestamp_anomaly
        if not anomaly:
            return []
        return [
            Finding(
                scanner=self.name,
                title=f"PE timestamp anomaly: {anomaly}",
                description=(
                    "PE TimeDateStamp does not look like a real build "
                    "time. Common cause: deliberate compilation-time "
                    "spoofing to break threat-intel pivots, or a "
                    "reproducible-build sentinel."
                ),
                severity=Severity.LOW,
                cwe="CWE-345",
                target=target.value,
                evidence={
                    "raw_timestamp": parsed.timestamp,
                    "kind": anomaly,
                    "attack": ["T1070.006"],  # Timestomping (loose fit)
                },
                remediation=(
                    "Cross-check the Rich Header build IDs (when present) "
                    "against the declared timestamp before trusting it."
                ),
            )
        ]

    def _embedded_findings(self, target: Target, parsed: ParseResult) -> list[Finding]:
        offsets = parsed.advanced.embedded_offsets
        if not offsets:
            return []
        # Sample's own header is at 0; carve_embedded already skipped it.
        return [
            Finding(
                scanner=self.name,
                title=f"Embedded sub-binary headers ({len(offsets)})",
                description=(
                    "Found additional PE/ELF magic past the primary "
                    "header — common pattern for droppers, installers, "
                    "and steganographically wrapped payloads."
                ),
                severity=Severity.HIGH,
                cwe="CWE-506",
                target=target.value,
                evidence={
                    "offsets": [{"format": k, "offset": o} for k, o in offsets[:32]],
                    "attack": ["T1027.009"],
                },
                remediation=(
                    "Carve each sub-binary and analyse it independently; "
                    "track parent → child sample lineage in the case file."
                ),
            )
        ]

    def _mime_mismatch_findings(
        self, target: Target, parsed: ParseResult
    ) -> list[Finding]:
        filename = str(target.metadata.get("filename") or "").lower()
        if "." not in filename or parsed.file_format == "unknown":
            return []
        ext = filename.rsplit(".", 1)[-1]
        # Map extensions to expected detected formats.
        expected = {
            "exe": {"pe"},
            "dll": {"pe"},
            "sys": {"pe"},
            "ocx": {"pe"},
            "scr": {"pe"},
            "cpl": {"pe"},
            "so": {"elf"},
            "elf": {"elf"},
            "out": {"elf"},
            "dylib": {
                "macho_32le",
                "macho_64le",
                "macho_32be",
                "macho_64be",
                "macho_fat",
            },
            "macho": {
                "macho_32le",
                "macho_64le",
                "macho_32be",
                "macho_64be",
                "macho_fat",
            },
            "pdf": {"pdf"},
            "doc": {"ole"},
            "xls": {"ole"},
            "ppt": {"ole"},
            "docx": {"zip"},
            "xlsx": {"zip"},
            "pptx": {"zip"},
            "apk": {"zip"},
            "jar": {"zip"},
            "zip": {"zip"},
            "7z": {"7z"},
            "rar": {"rar"},
            "gz": {"gzip"},
        }
        valid = expected.get(ext)
        if not valid or parsed.file_format in valid:
            return []
        return [
            Finding(
                scanner=self.name,
                title=(
                    f"Extension/content mismatch: .{ext} declared, "
                    f"{parsed.file_format} detected"
                ),
                description=(
                    "Magic-byte detection disagrees with the filename "
                    "extension. Frequently used to bypass naïve allow "
                    "lists — e.g. a PE renamed `.pdf` smuggled past an "
                    "email gateway."
                ),
                severity=Severity.HIGH,
                cwe="CWE-345",
                target=target.value,
                evidence={
                    "declared_extension": ext,
                    "detected_format": parsed.file_format,
                    "attack": ["T1036.005"],  # Match Legitimate Name
                },
                remediation=(
                    "Reject the upload at the perimeter — accept only "
                    "files whose magic bytes match their declared MIME "
                    "and extension."
                ),
            )
        ]

    def _infrastructure_finding(self, target: Target, reason: str) -> Finding:
        return Finding(
            scanner=self.name,
            title="Binary analyzer could not run",
            description=(
                f"Pre-flight check failed before parsing: {reason}. "
                "No static findings produced."
            ),
            severity=Severity.INFO,
            target=target.value,
            evidence={"reason": reason},
        )
