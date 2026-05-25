"""Static binary / file analysis scanner.

Reverse-engineers an uploaded sample without executing it. Produces
findings for: high-entropy (packed) sections, embedded IOCs (IPs, URLs,
domains, JWT, AWS keys, BTC wallets, registry keys, mutex names),
suspicious Win32 imports, missing Authenticode signature, embedded
private keys, and (when ``yara-python`` is available) custom YARA hits.

The scanner never spawns a child process for the sample — every parser
runs in-process on the bytes already quarantined under
``runtime/quarantine/<sha256>/``. The path is read from
``Target.metadata['path']`` set by ``routers/file_scan.py``.

Format coverage by default (pure stdlib):
  • PE / EXE / DLL / SYS / OCX
  • ELF (Linux .so, .out)
  • Mach-O (single-arch and FAT)
  • PDF, OLE/Office, ZIP/JAR/APK (entropy + IOC scan only)

Optional dependencies improve detail without changing the contract:
  • ``lief``       — rich PE/ELF parsing (signatures, TLS, .NET)
  • ``yara-python``— custom rule packs (rules dir env: ``RED_AGENT_YARA_RULES``)
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from core.observability.logging import get_logger
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners._binary_advanced import missing_mitigations
from plugins.red_agent.scanners._binary_iocs import (
    classify_ipv4,
    classify_url,
    extract_iocs,
    extract_strings,
    is_routable_ipv4,
    shannon_entropy,
    suspicious_imports,
    threat_intel_pivot_links,
)
from plugins.red_agent.scanners._binary_parser import ParseResult, parse_binary
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)

# Cap the read so a malicious 10 GiB upload cannot exhaust the worker.
_MAX_BYTES = 256 * 1024 * 1024  # 256 MiB
_HIGH_ENTROPY_THRESHOLD = 7.2


class BinaryAnalyzerScanner(Scanner):
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

    # ──────────────────────────────────────────────────────────────
    # Finding builders

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

    def _ioc_findings(
        self, target: Target, iocs: dict[str, list[str]]
    ) -> list[Finding]:
        out: list[Finding] = []
        for kind, values in iocs.items():
            if not values:
                continue
            if kind == "ipv4":
                out.extend(self._ipv4_findings(target, values))
                continue
            if kind == "ipv6":
                out.extend(self._ipv6_findings(target, values))
                continue
            if kind == "url":
                out.extend(self._url_findings(target, values))
                continue
            if kind == "domain":
                out.append(self._domain_bulk_finding(target, values))
                continue
            severity = _ioc_severity(kind, values)
            sample = values[:16]
            out.append(
                Finding(
                    scanner=self.name,
                    title=(
                        f"Embedded {kind} IOC: {sample[0]}"
                        if len(values) == 1
                        else f"Embedded {kind} IOCs ({len(values)}): {', '.join(sample[:3])}…"
                    ),
                    description=_render_indicator_list(kind, values),
                    severity=severity,
                    cwe="CWE-200",
                    target=target.value,
                    evidence={
                        "kind": kind,
                        "indicators": values[:200],
                        "truncated": len(values) > 200,
                    },
                    remediation=(
                        "Cross-reference indicators against threat-intel "
                        "feeds (MISP, GreyNoise, AlienVault OTX) and add "
                        "high-confidence matches to the deny lists."
                    ),
                )
            )
        return out

    def _ipv4_findings(self, target: Target, values: list[str]) -> list[Finding]:
        """One finding per routable IPv4 — title carries the address.

        Reserved / private IPs collapse into a single LOW finding so the
        operator's queue is not flooded by every embedded ``127.0.0.1``.
        """
        routable: list[str] = []
        reserved: list[tuple[str, str]] = []
        for ip in values:
            klass = classify_ipv4(ip)
            if klass:
                reserved.append((ip, klass))
            elif is_routable_ipv4(ip):
                routable.append(ip)
            else:
                reserved.append((ip, "non-routable"))
        out: list[Finding] = []
        for ip in routable:
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded routable IPv4: {ip}",
                    description=_render_ip_indicator(ip, kind="ipv4"),
                    severity=Severity.MEDIUM,
                    cwe="CWE-200",
                    target=target.value,
                    evidence={
                        "kind": "ipv4",
                        "value": ip,
                        "classification": "routable",
                        "pivots": threat_intel_pivot_links("ipv4", ip),
                    },
                    remediation=(
                        "Pivot the IP against VirusTotal/AbuseIPDB/GreyNoise. "
                        "If malicious, add to perimeter blocklists and hunt "
                        "for prior connections in firewall/proxy logs."
                    ),
                )
            )
        if reserved:
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded reserved IPv4 ({len(reserved)})",
                    description=_render_reserved_ips(reserved),
                    severity=Severity.LOW,
                    cwe="CWE-200",
                    target=target.value,
                    evidence={
                        "kind": "ipv4_reserved",
                        "indicators": [
                            {"value": v, "classification": k} for v, k in reserved[:200]
                        ],
                        "truncated": len(reserved) > 200,
                    },
                    remediation=(
                        "Reserved/private addresses are usually default "
                        "config or test fixtures. Confirm none reveal "
                        "internal infrastructure topology before shipping."
                    ),
                )
            )
        return out

    def _ipv6_findings(self, target: Target, values: list[str]) -> list[Finding]:
        return [
            Finding(
                scanner=self.name,
                title=(
                    f"Embedded IPv6: {values[0]}"
                    if len(values) == 1
                    else f"Embedded IPv6 indicators ({len(values)})"
                ),
                description=_render_indicator_list("ipv6", values),
                severity=Severity.MEDIUM,
                cwe="CWE-200",
                target=target.value,
                evidence={
                    "kind": "ipv6",
                    "indicators": values[:200],
                    "truncated": len(values) > 200,
                },
                remediation=(
                    "Resolve each address against threat-intel feeds and "
                    "the corporate IPv6 allocation map."
                ),
            )
        ]

    def _url_findings(self, target: Target, values: list[str]) -> list[Finding]:
        """Per-URL findings, escalated when the URL trips a heuristic."""
        out: list[Finding] = []
        for url in values:
            labels = classify_url(url)
            severity = _url_severity(labels)
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded URL: {url[:96]}",
                    description=_render_url_indicator(url, labels),
                    severity=severity,
                    cwe="CWE-200",
                    target=target.value,
                    evidence={
                        "kind": "url",
                        "value": url,
                        "labels": labels,
                        "pivots": threat_intel_pivot_links("url", url),
                    },
                    remediation=(
                        "If the URL is unfamiliar, sandbox-detonate it and "
                        "check WHOIS / passive DNS for the parent domain."
                    ),
                )
            )
        return out

    def _domain_bulk_finding(self, target: Target, values: list[str]) -> Finding:
        return Finding(
            scanner=self.name,
            title=(
                f"Embedded domain: {values[0]}"
                if len(values) == 1
                else f"Embedded domains ({len(values)})"
            ),
            description=_render_indicator_list("domain", values),
            severity=Severity.MEDIUM,
            cwe="CWE-200",
            target=target.value,
            evidence={
                "kind": "domain",
                "indicators": values[:200],
                "truncated": len(values) > 200,
                "pivots": {
                    v: threat_intel_pivot_links("domain", v) for v in values[:5]
                },
            },
            remediation=(
                "Compare against the corporate DNS allow-list and historical "
                "passive-DNS records (RiskIQ, DomainTools)."
            ),
        )

    def _import_findings(self, target: Target, suspicious: list[str]) -> list[Finding]:
        if not suspicious:
            return []
        return [
            Finding(
                scanner=self.name,
                title=f"Suspicious Win32 imports ({len(suspicious)})",
                description=(
                    "Sample imports APIs commonly abused by malware for "
                    "process injection, anti-analysis, or credential "
                    "access: " + ", ".join(suspicious[:32]) + "."
                ),
                severity=Severity.HIGH if len(suspicious) >= 4 else Severity.MEDIUM,
                cwe="CWE-506",
                target=target.value,
                evidence={
                    "imports": suspicious,
                    "attack_techniques": _imports_to_attack(suspicious),
                },
                remediation=(
                    "Review the call sites of each highlighted API; "
                    "legitimate uses should be documented in the binary's "
                    "design notes before approval."
                ),
            )
        ]

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

    def _private_key_findings(
        self, target: Target, iocs: dict[str, list[str]]
    ) -> list[Finding]:
        keys = iocs.get("private_key") or []
        aws = iocs.get("aws_access_key") or []
        jwt = iocs.get("jwt") or []
        out: list[Finding] = []
        if keys:
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded private key material ({len(keys)})",
                    description=("Sample contains PEM-encoded private key headers."),
                    severity=Severity.CRITICAL,
                    cwe="CWE-798",
                    target=target.value,
                    evidence={"matches": keys[:8]},
                    remediation="Rotate the key and remove it from the binary.",
                )
            )
        if aws:
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded AWS access keys ({len(aws)})",
                    description="AWS access-key IDs detected in the binary.",
                    severity=Severity.CRITICAL,
                    cwe="CWE-798",
                    target=target.value,
                    evidence={"keys": aws[:16]},
                    remediation="Disable the IAM key and rotate credentials.",
                )
            )
        if jwt:
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded JWTs ({len(jwt)})",
                    description="Sample carries JSON Web Tokens.",
                    severity=Severity.HIGH,
                    cwe="CWE-798",
                    target=target.value,
                    evidence={"tokens": jwt[:8]},
                    remediation="Revoke the token at the issuer.",
                )
            )
        return out

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


# ──────────────────────────────────────────────────────────────────────
# Helpers


def _human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.2f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


def _format_pe_timestamp(ts: int | None) -> str:
    if not ts:
        return "n/a"
    from datetime import datetime, timezone

    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except (OverflowError, OSError, ValueError):
        return f"raw={ts}"


def _url_severity(labels: list[str]) -> Severity:
    """Severity scaling for the URL classifier output."""
    high = {
        "tor_hidden_service",
        "ip_in_url",
        "dynamic_dns",
        "url_shortener",
        "punycode_idn",
    }
    if any(label.startswith("suspicious_tld_") for label in labels):
        return Severity.HIGH
    if any(label in high for label in labels):
        return Severity.HIGH
    if "deep_subdomain" in labels:
        return Severity.MEDIUM
    if "plaintext_http" in labels:
        return Severity.LOW
    return Severity.MEDIUM


def _render_overview_markdown(
    *,
    target: Target,
    parsed: ParseResult,
    digests: dict[str, str],
    size: int,
    iocs: dict[str, list[str]],
) -> str:
    """Operator-friendly overview that renders as markdown in the UI.

    Surfaces the signals an analyst checks first — file type, hashes,
    imphash, sections (with entropy heatmap-style emoji), exploit
    mitigations, packer fingerprints, IOC counts — without forcing a
    drill-down into the raw evidence JSON.
    """
    fmt_label = parsed.file_format.upper() if parsed.file_format else "UNKNOWN"
    bitness = f"{parsed.bitness}-bit" if parsed.bitness else "unknown bitness"
    machine = parsed.machine or "unknown arch"
    filename = target.metadata.get("filename") or target.value

    lines: list[str] = []
    lines.append("### Sample")
    lines.append(f"- **Filename**: `{filename}`")
    lines.append(f"- **Format**: {fmt_label} · {bitness} · {machine}")
    lines.append(f"- **Size**: {_human_size(size)}")
    if parsed.timestamp is not None:
        lines.append(f"- **TimeDateStamp**: {_format_pe_timestamp(parsed.timestamp)}")
    if parsed.advanced.timestamp_anomaly:
        lines.append(f"- **Timestamp anomaly**: `{parsed.advanced.timestamp_anomaly}`")

    lines.append("")
    lines.append("### Hashes")
    lines.append(f"- **SHA-256**: `{digests.get('sha256', '')}`")
    lines.append(f"- **SHA-1**: `{digests.get('sha1', '')}`")
    lines.append(f"- **MD5**: `{digests.get('md5', '')}`")
    if parsed.advanced.imphash:
        lines.append(f"- **Imphash**: `{parsed.advanced.imphash}`")
    lines.append(
        f"- **Full-file Shannon entropy**: {digests.get('shannon_entropy_full', 'n/a')}"
    )

    if parsed.file_format == "pe":
        lines.append("")
        lines.append("### Exploit mitigations")
        present = parsed.advanced.mitigations or []
        missing = missing_mitigations(parsed.advanced.dll_characteristics)
        if present:
            lines.append(f"- ✅ **Present**: {', '.join(f'`{m}`' for m in present)}")
        if missing:
            lines.append(f"- ❌ **Missing**: {', '.join(f'`{m}`' for m in missing)}")
        if not present and not missing:
            lines.append("- _no DllCharacteristics flags parsed_")
        lines.append(
            f"- **Authenticode signature**: "
            f"{'present' if parsed.is_signed else 'absent'}"
        )
        if parsed.is_dotnet:
            lines.append("- **.NET CLR header**: present")
        if parsed.has_tls_callbacks:
            lines.append("- **TLS callbacks**: present (anti-debug primitive)")

    if parsed.advanced.packer_hits:
        lines.append("")
        lines.append("### Packer / protector signatures")
        for hit in parsed.advanced.packer_hits:
            lines.append(f"- 🛡️ `{hit}`")

    if parsed.sections:
        lines.append("")
        lines.append(f"### Sections ({len(parsed.sections)})")
        lines.append("| Name | Size | Entropy | Flags |")
        lines.append("|------|------|---------|-------|")
        for s in parsed.sections[:24]:
            mark = "🔴" if s.entropy >= 7.5 else "🟡" if s.entropy >= 6.5 else "🟢"
            lines.append(
                f"| `{s.name}` | {_human_size(s.size)} | {mark} {s.entropy:.2f} | "
                f"`{s.flags or '-'}` |"
            )
        if len(parsed.sections) > 24:
            lines.append(f"| _…{len(parsed.sections) - 24} more_ |  |  |  |")

    if parsed.advanced.overlay_size:
        lines.append("")
        lines.append("### Overlay")
        lines.append(
            f"- **Offset**: `0x{parsed.advanced.overlay_offset:x}` · "
            f"**Size**: {_human_size(parsed.advanced.overlay_size)} · "
            f"**Entropy**: {parsed.advanced.overlay_entropy:.2f}"
        )

    if parsed.advanced.embedded_offsets:
        lines.append("")
        lines.append("### Embedded sub-binaries")
        for fmt_name, off in parsed.advanced.embedded_offsets[:8]:
            lines.append(f"- `{fmt_name}` at offset `0x{off:x}`")

    if parsed.advanced.rich_header:
        lines.append("")
        lines.append(f"### Rich Header ({len(parsed.advanced.rich_header)} entries)")
        lines.append(
            f"- **XOR key**: `0x{parsed.advanced.rich_xor_key:08x}` "
            f"(Microsoft compiler/linker fingerprint — pivot for sample "
            f"clustering)"
        )

    if parsed.libraries or parsed.imports or parsed.exports:
        lines.append("")
        lines.append("### Imports / exports")
        lines.append(f"- **Libraries**: {len(parsed.libraries)}")
        if parsed.libraries:
            preview = ", ".join(f"`{lib}`" for lib in parsed.libraries[:6])
            extra = (
                f" + {len(parsed.libraries) - 6} more"
                if len(parsed.libraries) > 6
                else ""
            )
            lines.append(f"  - {preview}{extra}")
        lines.append(f"- **Imported functions**: {len(parsed.imports)}")
        lines.append(f"- **Exported functions**: {len(parsed.exports)}")

    if iocs:
        lines.append("")
        lines.append("### Embedded indicators (string sweep)")
        for kind in sorted(iocs.keys()):
            count = len(iocs[kind])
            sample = ", ".join(f"`{v}`" for v in iocs[kind][:3])
            extra = f", +{count - 3} more" if count > 3 else ""
            lines.append(f"- **{kind}** ({count}): {sample}{extra}")

    if parsed.notes:
        lines.append("")
        lines.append("### Parser notes")
        for n in parsed.notes:
            lines.append(f"- {n}")

    return "\n".join(lines)


def _render_indicator_list(kind: str, values: list[str]) -> str:
    head = values[:32]
    body = "\n".join(f"- `{v}`" for v in head)
    if len(values) > 32:
        body += f"\n- _…{len(values) - 32} more in evidence_"
    return (
        f"Static IOC sweep extracted **{len(values)}** unique `{kind}` "
        f"indicator(s) from the sample's strings.\n\n"
        f"#### Indicators\n{body}"
    )


def _render_ip_indicator(ip: str, *, kind: str) -> str:
    pivots = threat_intel_pivot_links(kind, ip)
    pivot_md = "\n".join(f"- [{name}]({url})" for name, url in pivots.items())
    return (
        f"**Routable {kind} address embedded in the sample.**\n\n"
        f"- **Address**: `{ip}`\n"
        f"- **Classification**: routable public unicast — treat as a C2 "
        f"candidate until cleared.\n\n"
        f"#### Pivot to threat-intel\n{pivot_md}\n"
    )


def _render_reserved_ips(reserved: list[tuple[str, str]]) -> str:
    rows = "\n".join(f"- `{ip}` — _{label}_" for ip, label in reserved[:48])
    extra = (
        f"\n- _…{len(reserved) - 48} more in evidence_" if len(reserved) > 48 else ""
    )
    return (
        f"Reserved / private IPv4 addresses found ({len(reserved)}). "
        f"Useful as leak signals (internal topology) but not C2 candidates.\n\n"
        f"#### Addresses\n{rows}{extra}"
    )


def _render_url_indicator(url: str, labels: list[str]) -> str:
    pivots = threat_intel_pivot_links("url", url)
    pivot_md = "\n".join(f"- [{name}]({u})" for name, u in pivots.items())
    label_md = (
        "\n".join(f"- 🚩 `{label}`" for label in labels)
        if labels
        else "- _no heuristic match — treat as ordinary external link_"
    )
    return (
        f"**URL embedded in sample.**\n\n"
        f"- **Value**: `{url}`\n\n"
        f"#### Heuristic flags\n{label_md}\n\n"
        f"#### Pivot to threat-intel\n{pivot_md}\n"
    )


def _hash_all(data: bytes) -> dict[str, str]:
    return {
        "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
        "sha1": hashlib.sha1(data, usedforsecurity=False).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha512": hashlib.sha512(data).hexdigest(),
        "shannon_entropy_full": f"{shannon_entropy(data):.4f}",
    }


def _ioc_severity(kind: str, values: list[str]) -> Severity:
    if kind in {"private_key", "aws_access_key"}:
        return Severity.CRITICAL
    if kind == "jwt":
        return Severity.HIGH
    if kind in {"url", "domain"}:
        return Severity.MEDIUM
    if kind == "ipv4":
        # Routable IPs in a binary are noteworthy; private/loopback are not.
        return (
            Severity.MEDIUM
            if any(is_routable_ipv4(v) for v in values)
            else Severity.LOW
        )
    if kind in {"btc", "eth"}:
        return Severity.HIGH
    if kind == "mutex":
        return Severity.MEDIUM
    return Severity.LOW


def _imports_to_attack(symbols: list[str]) -> list[str]:
    """Coarse mapping of imported APIs to MITRE ATT&CK technique IDs."""
    table: dict[str, str] = {
        "VirtualAllocEx": "T1055",
        "WriteProcessMemory": "T1055",
        "CreateRemoteThread": "T1055.001",
        "QueueUserAPC": "T1055.004",
        "SetWindowsHookExA": "T1056.004",
        "SetWindowsHookExW": "T1056.004",
        "IsDebuggerPresent": "T1622",
        "CheckRemoteDebuggerPresent": "T1622",
        "NtQueryInformationProcess": "T1622",
        "RegSetValueExA": "T1112",
        "RegSetValueExW": "T1112",
        "CreateServiceA": "T1543.003",
        "CreateServiceW": "T1543.003",
        "CryptUnprotectData": "T1555.004",
        "InternetOpenUrlA": "T1071.001",
        "WinHttpOpen": "T1071.001",
    }
    seen: set[str] = set()
    out: list[str] = []
    for sym in symbols:
        tid = table.get(sym)
        if tid and tid not in seen:
            seen.add(tid)
            out.append(tid)
    return out


def _yara_severity(tags: list[str]) -> Severity:
    joined = " ".join(t.lower() for t in tags)
    if any(k in joined for k in ("ransom", "rat", "stealer", "loader")):
        return Severity.CRITICAL
    if any(k in joined for k in ("malware", "trojan", "backdoor")):
        return Severity.HIGH
    if "suspicious" in joined:
        return Severity.MEDIUM
    return Severity.LOW


def _run_yara(path: Path, data: bytes) -> list[dict[str, Any]]:
    """Compile rules from ``RED_AGENT_YARA_RULES`` and scan the buffer."""
    rules_dir = os.environ.get("RED_AGENT_YARA_RULES")
    if not rules_dir:
        return []
    try:
        import yara  # type: ignore[import-untyped]
    except ImportError:
        return []
    try:
        sources: dict[str, str] = {}
        for rule_path in Path(rules_dir).rglob("*.yar*"):
            sources[rule_path.stem] = str(rule_path)
        if not sources:
            return []
        rules = yara.compile(filepaths=sources)
        matches = rules.match(data=data)
    except Exception as e:  # noqa: BLE001
        logger.warning("binary_analyzer.yara_failed", extra={"err": str(e)})
        return []
    out: list[dict[str, Any]] = []
    for m in matches:
        out.append(
            {
                "rule": m.rule,
                "tags": list(m.tags or []),
                "meta": dict(m.meta or {}),
                "strings": [
                    {"offset": s[0], "id": s[1]}
                    for s in (getattr(m, "strings", []) or [])[:32]
                ],
                "path": str(path),
            }
        )
    return out
