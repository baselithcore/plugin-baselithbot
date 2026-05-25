"""Unit tests for the static binary analysis pipeline."""

from __future__ import annotations

import asyncio
import os
import struct
import tempfile

import pytest

from plugins.red_agent.models import ScanIntensity, Target, TargetType
from plugins.red_agent.mock_sandbox import MockSandboxRunner
from plugins.red_agent.scanners._binary_advanced import (
    carve_embedded,
    classify_timestamp,
    compute_imphash,
    decode_dll_characteristics,
    detect_packers,
    missing_mitigations,
    parse_rich_header,
)
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
from plugins.red_agent.scanners._binary_parser import detect_format, parse_binary
from plugins.red_agent.scanners.binary_analyzer import BinaryAnalyzerScanner


# ──────────────────────────────────────────────────────────────────────
# Helpers


def _build_pe_skeleton(
    *,
    section_name: bytes = b".text\x00\x00\x00",
    dll_chars: int = 0,
    timestamp: int = 0x65000000,
    extra: bytes = b"",
) -> bytes:
    """Build a minimal PE that the static parser can walk to completion.

    Layout: DOS header → e_lfanew → PE\\0\\0 → COFF → Optional → 1 section.
    Padded out to keep section raw_ptr offsets valid.
    """
    e_lfanew = 0x80
    coff = struct.pack(
        "<HHIIIHH",
        0x14C,  # machine: i386
        1,  # 1 section
        timestamp,  # TimeDateStamp
        0,  # symbol table
        0,  # symbol count
        0xE0,  # opt header size
        0x102,  # characteristics: executable + 32-bit
    )
    # Optional header (PE32, 224 bytes total).
    opt = bytearray(0xE0)
    struct.pack_into("<H", opt, 0, 0x10B)  # magic PE32
    struct.pack_into("<I", opt, 16, 0x1000)  # AddressOfEntryPoint
    struct.pack_into("<H", opt, 0x46, dll_chars)  # DllCharacteristics
    body = b"PE\x00\x00" + coff + bytes(opt)
    # 1 section (.text), 0x40 bytes long, raw_ptr pointing past header end.
    raw_ptr = 0x200
    raw_size = 0x40
    section = (
        section_name
        + struct.pack("<II", raw_size, 0)  # virtual size, virtual addr
        + struct.pack("<II", raw_size, raw_ptr)  # raw size, raw ptr
        + b"\x00" * 16
        + struct.pack("<I", 0x60000020)
    )
    blob = bytearray(b"MZ" + b"\x00" * (e_lfanew - 2))
    blob[0x3C:0x40] = struct.pack("<I", e_lfanew)
    blob.extend(body)
    blob.extend(section)
    if len(blob) < raw_ptr:
        blob.extend(b"\x00" * (raw_ptr - len(blob)))
    blob.extend(b"\x90" * raw_size)
    if extra:
        blob.extend(extra)
    return bytes(blob)


# ──────────────────────────────────────────────────────────────────────
# IOC + entropy primitives


def test_shannon_entropy_bounds() -> None:
    assert shannon_entropy(b"") == 0.0
    assert shannon_entropy(b"A" * 100) == 0.0
    high = shannon_entropy(bytes(range(256)) * 4)
    assert high > 7.9


def test_extract_strings_ascii_and_utf16() -> None:
    raw = b"hello world\x00plain ascii here\x00\xff"
    raw += "deadbeefcafe".encode("utf-16-le")
    s = extract_strings(raw)
    assert "hello world" in s
    assert "plain ascii here" in s
    assert any("deadbeef" in token for token in s)


def test_extract_iocs_routable_filtering() -> None:
    iocs = extract_iocs(["http://evil.example.com/c2 192.0.2.1 user@evil.com"])
    assert "url" in iocs
    assert "192.0.2.1" in iocs.get("ipv4", [])
    assert "user@evil.com" in iocs.get("email", [])


def test_is_routable_ipv4() -> None:
    assert is_routable_ipv4("8.8.8.8")
    assert not is_routable_ipv4("10.0.0.1")
    assert not is_routable_ipv4("127.0.0.1")
    assert not is_routable_ipv4("192.168.1.5")


def test_suspicious_imports_match() -> None:
    hits = suspicious_imports(
        ["kernel32.VirtualAllocEx", "kernel32.WriteProcessMemory", "msvcrt.printf"]
    )
    assert "VirtualAllocEx" in hits
    assert "WriteProcessMemory" in hits
    assert "printf" not in hits


# ──────────────────────────────────────────────────────────────────────
# Advanced PE primitives


def test_compute_imphash_matches_mandiant_spec() -> None:
    # The pefile/Mandiant reference: lowercase, strip .dll, "lib.fn"
    # joined by commas, MD5'd. Verify by recomputing the canonical form.
    import hashlib

    canonical = "kernel32.getprocaddress,user32.messageboxa"
    expected = hashlib.md5(canonical.encode("ascii"), usedforsecurity=False).hexdigest()
    imphash = compute_imphash(
        [("KERNEL32.dll", "GetProcAddress"), ("USER32.DLL", "MessageBoxA")]
    )
    assert imphash == expected
    assert compute_imphash([]) == ""


def test_compute_imphash_ordinals_use_lookup_table() -> None:
    # ws2_32 ordinal 23 is "socket" per the lookup table.
    imphash = compute_imphash([("ws2_32.dll", 23)])
    assert imphash == compute_imphash([("ws2_32.dll", "socket")])


def test_decode_dll_characteristics_and_missing_mitigations() -> None:
    # ASLR + DEP set, CFG missing.
    flags = decode_dll_characteristics(0x0140)
    assert "DYNAMIC_BASE" in flags
    assert "NX_COMPAT" in flags
    missing = missing_mitigations(0x0140)
    assert missing == ["GUARD_CF"]


def test_detect_packers_signature_match() -> None:
    assert detect_packers(["UPX0", "UPX1"]) == ["UPX"]
    assert detect_packers([".vmp0"]) == ["VMProtect"]
    assert detect_packers([".text", ".data"]) == []


def test_classify_timestamp_anomalies() -> None:
    now = 1_900_000_000  # somewhere mid-2030
    assert classify_timestamp(0, now_epoch=now) == "epoch_zero"
    assert classify_timestamp(now + 86_500, now_epoch=now) == "future_timestamp"
    assert classify_timestamp(900_000_000, now_epoch=now) == "pre_2000_timestamp"
    assert classify_timestamp(now - 1000, now_epoch=now) == ""


def test_carve_embedded_finds_inner_pe() -> None:
    inner = _build_pe_skeleton()
    haystack = b"\x00" * 1024 + inner
    found = carve_embedded(haystack, skip_offset=1)
    assert any(fmt == "pe" for fmt, _ in found)


def test_parse_rich_header_handles_absent_header() -> None:
    xor, entries = parse_rich_header(b"MZ" + b"\x00" * 200, e_lfanew=0x80)
    assert xor == 0
    assert entries == []


# ──────────────────────────────────────────────────────────────────────
# detect_format + parse_binary


def test_detect_format_magic_table() -> None:
    assert detect_format(b"MZ\x00\x00") == "pe"
    assert detect_format(b"\x7fELF\x02\x01") == "elf"
    assert detect_format(b"%PDF-1.7") == "pdf"
    assert detect_format(b"PK\x03\x04abc") == "zip"
    assert detect_format(b"unknown") == "unknown"


def test_parse_binary_pe_advanced_fields() -> None:
    pe = _build_pe_skeleton(section_name=b"UPX0\x00\x00\x00\x00")
    res = parse_binary(pe)
    assert res.file_format == "pe"
    assert res.sections, "section table must parse"
    assert res.sections[0].name.startswith("UPX0")
    assert "UPX" in res.advanced.packer_hits
    assert res.advanced.timestamp_anomaly == ""


def test_parse_binary_classifies_unknown() -> None:
    res = parse_binary(b"abcdefgh" * 8)
    assert res.file_format == "unknown"


# ──────────────────────────────────────────────────────────────────────
# End-to-end scanner


@pytest.fixture()
def scanner() -> BinaryAnalyzerScanner:
    return BinaryAnalyzerScanner(MockSandboxRunner())


def _run_scanner(scanner: BinaryAnalyzerScanner, path: str, filename: str):
    target = Target(
        type=TargetType.BINARY,
        value="0" * 64,
        metadata={"path": path, "filename": filename, "size": os.path.getsize(path)},
    )
    return asyncio.run(scanner.run(target, ScanIntensity.PASSIVE))


def test_scanner_emits_overview_and_iocs(scanner: BinaryAnalyzerScanner) -> None:
    pe = _build_pe_skeleton(extra=b"http://evil.example.com user@evil.com\x00")
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as t:
        t.write(pe)
        path = t.name
    try:
        findings = _run_scanner(scanner, path, "sample.exe")
    finally:
        os.unlink(path)
    titles = [f.title for f in findings]
    assert any("Binary overview" in t for t in titles)
    assert any(t.startswith("Embedded URL:") for t in titles)


def test_scanner_flags_mime_mismatch(scanner: BinaryAnalyzerScanner) -> None:
    pe = _build_pe_skeleton()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as t:
        t.write(pe)
        path = t.name
    try:
        findings = _run_scanner(scanner, path, "lure.pdf")
    finally:
        os.unlink(path)
    assert any("Extension/content mismatch" in f.title for f in findings)


def test_scanner_flags_missing_mitigations(scanner: BinaryAnalyzerScanner) -> None:
    pe = _build_pe_skeleton(dll_chars=0)
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as t:
        t.write(pe)
        path = t.name
    try:
        findings = _run_scanner(scanner, path, "noaslr.exe")
    finally:
        os.unlink(path)
    assert any("Missing exploit mitigations" in f.title for f in findings)


def test_scanner_flags_packer(scanner: BinaryAnalyzerScanner) -> None:
    pe = _build_pe_skeleton(section_name=b"UPX0\x00\x00\x00\x00")
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as t:
        t.write(pe)
        path = t.name
    try:
        findings = _run_scanner(scanner, path, "packed.exe")
    finally:
        os.unlink(path)
    assert any("Packer signature" in f.title for f in findings)


def test_scanner_handles_missing_path(scanner: BinaryAnalyzerScanner) -> None:
    target = Target(type=TargetType.BINARY, value="0" * 64, metadata={})
    findings = asyncio.run(scanner.run(target, ScanIntensity.PASSIVE))
    assert len(findings) == 1
    assert "could not run" in findings[0].title


def test_scanner_skips_non_binary_targets(scanner: BinaryAnalyzerScanner) -> None:
    target = Target(type=TargetType.URL, value="https://example.com")
    findings = asyncio.run(scanner.run(target, ScanIntensity.PASSIVE))
    assert findings == []


def test_classify_ipv4_reserved_labels() -> None:
    assert classify_ipv4("8.8.8.8") == ""
    assert "loopback" in classify_ipv4("127.0.0.1")
    assert "RFC1918" in classify_ipv4("192.168.1.1")
    assert "TEST-NET-2" in classify_ipv4("198.51.100.5")
    assert "multicast" in classify_ipv4("224.0.0.1")


def test_classify_url_heuristics() -> None:
    labels = classify_url("http://1.2.3.4/x")
    assert "ip_in_url" in labels
    assert "plaintext_http" in labels
    assert any(
        label.startswith("suspicious_tld_")
        for label in classify_url("https://evil.tk/c2")
    )
    assert "dynamic_dns" in classify_url("http://attacker.duckdns.org/")
    assert "url_shortener" in classify_url("https://bit.ly/xxx")
    assert "tor_hidden_service" in classify_url("http://abc.onion/")
    assert "punycode_idn" in classify_url("https://xn--paypal-xxx.com/login")
    assert classify_url("https://example.com/x") == []


def test_threat_intel_pivot_links_for_ip_and_domain() -> None:
    ip_links = threat_intel_pivot_links("ipv4", "8.8.8.8")
    assert "VirusTotal" in ip_links
    assert "8.8.8.8" in ip_links["VirusTotal"]
    dom = threat_intel_pivot_links("domain", "example.com")
    assert any("crt.sh" in v for v in dom.values())
    assert threat_intel_pivot_links("unknown", "x") == {}


def test_filter_pins_binary_analyzer_for_binary_target() -> None:
    """Regression: user policy overrides excluding ``binary_analyzer`` must
    not silently swap in network scanners against a SHA-256 target."""
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from plugins.red_agent._agent_helpers import filter_request_scanners
    from plugins.red_agent.models import ScanRequest

    audit = AsyncMock()
    req = ScanRequest(
        target=Target(
            type=TargetType.BINARY,
            value="a" * 64,
            metadata={"path": "/tmp/x"},  # nosec B108
        ),
        scanners=["binary_analyzer"],
        intensity=ScanIntensity.PASSIVE,
        requested_by="test",
    )
    out = asyncio.run(
        filter_request_scanners(
            request=req,
            enabled_scanners=["nmap", "nuclei", "zap"],  # no binary_analyzer
            audit=audit,
            scan_id=uuid4(),
        )
    )
    assert out.scanners == ["binary_analyzer"]
