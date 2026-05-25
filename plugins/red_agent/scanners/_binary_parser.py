"""Static structural parsers for executable formats.

Pure-stdlib minimal parsers for PE/ELF/Mach-O headers — enough to surface
sections, entropy and imports for triage. When the optional ``lief``
library is importable we delegate to it for richer detail (rich header,
TLS callbacks, signature, .NET CLR), but the scanner stays operational
in environments where ``lief`` is missing (e.g. minimal containers).
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
from typing import Any

from plugins.red_agent.scanners._binary_advanced import (
    AdvancedPE,
    carve_embedded,
    classify_timestamp,
    compute_imphash,
    compute_overlay,
    decode_dll_characteristics,
    detect_packers,
    parse_rich_header,
    walk_pe_imports,
)

# ──────────────────────────────────────────────────────────────────────
# Magic byte detection — covers everything the upload endpoint accepts.

_MAGIC_TABLE: tuple[tuple[bytes, str], ...] = (
    (b"MZ", "pe"),
    (b"\x7fELF", "elf"),
    (b"\xfe\xed\xfa\xce", "macho_32be"),
    (b"\xce\xfa\xed\xfe", "macho_32le"),
    (b"\xfe\xed\xfa\xcf", "macho_64be"),
    (b"\xcf\xfa\xed\xfe", "macho_64le"),
    (b"\xca\xfe\xba\xbe", "macho_fat"),
    (b"PK\x03\x04", "zip"),
    (b"%PDF", "pdf"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole"),
    (b"#!", "script"),
    (b"\x1f\x8b", "gzip"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"Rar!\x1a\x07", "rar"),
)


def detect_format(data: bytes) -> str:
    """Best-effort file-type identification by magic bytes."""
    head = data[:16]
    for magic, label in _MAGIC_TABLE:
        if head.startswith(magic):
            return label
    return "unknown"


# ──────────────────────────────────────────────────────────────────────
# Result dataclasses — kept JSON-serialisable.


@dataclass
class SectionInfo:
    name: str
    size: int
    entropy: float
    flags: str = ""


@dataclass
class ParseResult:
    file_format: str
    bitness: int = 0
    machine: str = ""
    entrypoint: int = 0
    timestamp: int | None = None
    sections: list[SectionInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    libraries: list[str] = field(default_factory=list)
    is_signed: bool = False
    is_dotnet: bool = False
    has_tls_callbacks: bool = False
    notes: list[str] = field(default_factory=list)
    advanced: AdvancedPE = field(default_factory=AdvancedPE)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_format": self.file_format,
            "bitness": self.bitness,
            "machine": self.machine,
            "entrypoint": self.entrypoint,
            "timestamp": self.timestamp,
            "sections": [s.__dict__ for s in self.sections],
            "imports": self.imports,
            "exports": self.exports,
            "libraries": self.libraries,
            "is_signed": self.is_signed,
            "is_dotnet": self.is_dotnet,
            "has_tls_callbacks": self.has_tls_callbacks,
            "notes": self.notes,
            "advanced": self.advanced.to_dict(),
        }


# ──────────────────────────────────────────────────────────────────────
# Pure-stdlib PE / ELF readers


def _entropy(buf: bytes) -> float:
    from plugins.red_agent.scanners._binary_iocs import shannon_entropy

    return shannon_entropy(buf)


def _parse_pe_minimal(data: bytes) -> ParseResult:
    res = ParseResult(file_format="pe")
    try:
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        if data[e_lfanew : e_lfanew + 4] != b"PE\x00\x00":
            res.notes.append("invalid_pe_signature")
            return res
        coff_off = e_lfanew + 4
        machine, n_sections, ts = struct.unpack_from("<HHI", data, coff_off)
        opt_size = struct.unpack_from("<H", data, coff_off + 0x10)[0]
        opt_off = coff_off + 0x14
        magic = struct.unpack_from("<H", data, opt_off)[0]
        res.bitness = 64 if magic == 0x20B else 32
        res.machine = {
            0x14C: "i386",
            0x8664: "amd64",
            0x1C0: "arm",
            0xAA64: "arm64",
        }.get(machine, hex(machine))
        res.timestamp = ts
        res.entrypoint = struct.unpack_from("<I", data, opt_off + 16)[0]

        # PE checksum (offset +64 from optional header start) and
        # DllCharacteristics (offset +70 PE32 / +70 PE32+).
        is_pe32_plus = magic == 0x20B
        if opt_off + 0x48 < len(data):
            res.advanced.pe_checksum_in_header = struct.unpack_from(
                "<I", data, opt_off + 0x40
            )[0]
        dll_char_off = opt_off + (0x46 if not is_pe32_plus else 0x46)
        if dll_char_off + 2 <= len(data):
            res.advanced.dll_characteristics = struct.unpack_from(
                "<H", data, dll_char_off
            )[0]
            res.advanced.mitigations = decode_dll_characteristics(
                res.advanced.dll_characteristics
            )

        sec_off = opt_off + opt_size
        last_raw_end = 0
        for i in range(n_sections):
            base = sec_off + i * 0x28
            if base + 0x28 > len(data):
                break
            name = (
                data[base : base + 8].rstrip(b"\x00").decode("ascii", errors="replace")
            )
            raw_size = struct.unpack_from("<I", data, base + 16)[0]
            raw_ptr = struct.unpack_from("<I", data, base + 20)[0]
            chars = struct.unpack_from("<I", data, base + 36)[0]
            buf = data[raw_ptr : raw_ptr + raw_size]
            flags = []
            if chars & 0x20000000:
                flags.append("X")
            if chars & 0x40000000:
                flags.append("R")
            if chars & 0x80000000:
                flags.append("W")
            res.sections.append(
                SectionInfo(
                    name=name,
                    size=raw_size,
                    entropy=_entropy(buf),
                    flags="".join(flags),
                )
            )
            last_raw_end = max(last_raw_end, raw_ptr + raw_size)

        # Imports + imphash via the standalone walker.
        import_pairs = walk_pe_imports(data)
        if import_pairs:
            res.advanced.imphash = compute_imphash(import_pairs)
            seen_libs: set[str] = set()
            for lib, sym in import_pairs:
                if lib not in seen_libs:
                    seen_libs.add(lib)
                    res.libraries.append(lib)
                if isinstance(sym, str):
                    res.imports.append(f"{lib}.{sym}")
                else:
                    res.imports.append(f"{lib}.ord{sym}")

        # Rich header (Microsoft compiler/linker fingerprint).
        xor_key, rich = parse_rich_header(data, e_lfanew)
        if rich:
            res.advanced.rich_xor_key = xor_key
            res.advanced.rich_header = rich

        # Overlay (data appended past the last section's raw end).
        if last_raw_end:
            offset, size, ent = compute_overlay(data, last_raw_end, 0)
            res.advanced.overlay_offset = offset
            res.advanced.overlay_size = size
            res.advanced.overlay_entropy = ent

        # Embedded PE/ELF headers (carved sub-binaries).
        res.advanced.embedded_offsets = carve_embedded(data, skip_offset=1)

        # Packer signature catalogue.
        res.advanced.packer_hits = detect_packers(s.name for s in res.sections)

        # Timestamp anomaly classification.
        res.advanced.timestamp_anomaly = classify_timestamp(
            res.timestamp, now_epoch=int(time.time())
        )
    except (struct.error, IndexError) as e:
        res.notes.append(f"pe_parse_error: {e}")
    return res


def _parse_elf_minimal(data: bytes) -> ParseResult:
    res = ParseResult(file_format="elf")
    try:
        ei_class = data[4]
        endian = "<" if data[5] == 1 else ">"
        res.bitness = 64 if ei_class == 2 else 32
        if res.bitness == 64:
            e_machine = struct.unpack_from(endian + "H", data, 0x12)[0]
            e_entry = struct.unpack_from(endian + "Q", data, 0x18)[0]
            e_shoff = struct.unpack_from(endian + "Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from(endian + "H", data, 0x3A)[0]
            e_shnum = struct.unpack_from(endian + "H", data, 0x3C)[0]
            e_shstrndx = struct.unpack_from(endian + "H", data, 0x3E)[0]
        else:
            e_machine = struct.unpack_from(endian + "H", data, 0x12)[0]
            e_entry = struct.unpack_from(endian + "I", data, 0x18)[0]
            e_shoff = struct.unpack_from(endian + "I", data, 0x20)[0]
            e_shentsize = struct.unpack_from(endian + "H", data, 0x2E)[0]
            e_shnum = struct.unpack_from(endian + "H", data, 0x30)[0]
            e_shstrndx = struct.unpack_from(endian + "H", data, 0x32)[0]
        res.machine = {0x03: "i386", 0x3E: "amd64", 0x28: "arm", 0xB7: "arm64"}.get(
            e_machine, hex(e_machine)
        )
        res.entrypoint = e_entry

        if e_shnum and e_shoff and e_shstrndx < e_shnum:
            shstr_hdr = e_shoff + e_shstrndx * e_shentsize
            if res.bitness == 64:
                shstr_off = struct.unpack_from(endian + "Q", data, shstr_hdr + 24)[0]
                shstr_size = struct.unpack_from(endian + "Q", data, shstr_hdr + 32)[0]
            else:
                shstr_off = struct.unpack_from(endian + "I", data, shstr_hdr + 16)[0]
                shstr_size = struct.unpack_from(endian + "I", data, shstr_hdr + 20)[0]
            shstrtab = data[shstr_off : shstr_off + shstr_size]
            for i in range(e_shnum):
                base = e_shoff + i * e_shentsize
                name_off = struct.unpack_from(endian + "I", data, base)[0]
                if res.bitness == 64:
                    sh_off = struct.unpack_from(endian + "Q", data, base + 24)[0]
                    sh_size = struct.unpack_from(endian + "Q", data, base + 32)[0]
                    sh_flags = struct.unpack_from(endian + "Q", data, base + 8)[0]
                else:
                    sh_off = struct.unpack_from(endian + "I", data, base + 16)[0]
                    sh_size = struct.unpack_from(endian + "I", data, base + 20)[0]
                    sh_flags = struct.unpack_from(endian + "I", data, base + 8)[0]
                end = shstrtab.find(b"\x00", name_off)
                name = shstrtab[name_off:end].decode("ascii", errors="replace")
                buf = data[sh_off : sh_off + sh_size] if sh_size < len(data) else b""
                flags = []
                if sh_flags & 0x4:
                    flags.append("X")
                if sh_flags & 0x2:
                    flags.append("A")
                if sh_flags & 0x1:
                    flags.append("W")
                res.sections.append(
                    SectionInfo(
                        name=name,
                        size=sh_size,
                        entropy=_entropy(buf),
                        flags="".join(flags),
                    )
                )
    except (struct.error, IndexError) as e:
        res.notes.append(f"elf_parse_error: {e}")
    return res


# ──────────────────────────────────────────────────────────────────────
# Public entry — try lief first, fall back to minimal parsers.


def parse_binary(data: bytes) -> ParseResult:
    fmt = detect_format(data)
    if fmt in {"pe", "elf"}:
        try:
            import lief  # type: ignore[import-untyped]
        except ImportError:
            lief = None
        if lief is not None:
            res = _parse_with_lief(data, fmt, lief)
        elif fmt == "pe":
            res = _parse_pe_minimal(data)
        else:
            res = _parse_elf_minimal(data)
        if fmt == "pe":
            _enrich_pe_advanced(data, res)
        return res
    return ParseResult(file_format=fmt)


def _enrich_pe_advanced(data: bytes, res: ParseResult) -> None:
    """Run the advanced PE pass even when LIEF supplied the basics.

    Idempotent — only fills fields the primary parse left empty so a
    pure-stdlib run and a LIEF run converge on the same answer.
    """
    if not res.advanced.imphash:
        pairs = walk_pe_imports(data)
        if pairs:
            res.advanced.imphash = compute_imphash(pairs)
    if not res.advanced.rich_header:
        try:
            e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        except struct.error:
            return
        xor_key, rich = parse_rich_header(data, e_lfanew)
        if rich:
            res.advanced.rich_xor_key = xor_key
            res.advanced.rich_header = rich
    if not res.advanced.packer_hits:
        res.advanced.packer_hits = detect_packers(s.name for s in res.sections)
    if not res.advanced.embedded_offsets:
        res.advanced.embedded_offsets = carve_embedded(data, skip_offset=1)
    if not res.advanced.timestamp_anomaly:
        res.advanced.timestamp_anomaly = classify_timestamp(
            res.timestamp, now_epoch=int(time.time())
        )


def _parse_with_lief(data: bytes, fmt: str, lief: Any) -> ParseResult:
    """Delegate to the upstream LIEF reader for richer detail."""
    res = ParseResult(file_format=fmt)
    try:
        binary = lief.parse(list(data))
        if binary is None:
            res.notes.append("lief_parse_returned_none")
            return res
        if fmt == "pe":
            res.bitness = (
                64 if binary.header.machine == lief.PE.MACHINE_TYPES.AMD64 else 32
            )
            res.machine = str(binary.header.machine).split(".")[-1]
            res.timestamp = int(binary.header.time_date_stamps)
            res.entrypoint = int(binary.optional_header.addressof_entrypoint)
            res.is_signed = bool(binary.has_signatures)
            res.is_dotnet = bool(
                binary.has_configuration
                and binary.has(lief.PE.DATA_DIRECTORY.CLR_RUNTIME_HEADER)
            )
            res.has_tls_callbacks = bool(binary.has_tls and binary.tls.callbacks)
            for s in binary.sections:
                res.sections.append(
                    SectionInfo(
                        name=s.name,
                        size=int(s.size),
                        entropy=float(getattr(s, "entropy", 0.0) or 0.0),
                        flags="",
                    )
                )
            for imp in getattr(binary, "imports", []) or []:
                lib = getattr(imp, "name", "") or ""
                res.libraries.append(lib)
                for entry in getattr(imp, "entries", []) or []:
                    name = getattr(entry, "name", None)
                    if name:
                        res.imports.append(f"{lib}.{name}")
            for exp in getattr(
                getattr(binary, "exported_functions", []), "__iter__", lambda: []
            )():
                name = getattr(exp, "name", None) or str(exp)
                if name:
                    res.exports.append(name)
        elif fmt == "elf":
            res.bitness = (
                64 if binary.header.identity_class == lief.ELF.ELF_CLASS.CLASS64 else 32
            )
            res.machine = str(binary.header.machine_type).split(".")[-1]
            res.entrypoint = int(binary.entrypoint)
            for s in binary.sections:
                res.sections.append(
                    SectionInfo(
                        name=s.name,
                        size=int(s.size),
                        entropy=float(getattr(s, "entropy", 0.0) or 0.0),
                    )
                )
            for sym in getattr(binary, "imported_functions", []) or []:
                n = getattr(sym, "name", None) or str(sym)
                if n:
                    res.imports.append(n)
            for sym in getattr(binary, "exported_functions", []) or []:
                n = getattr(sym, "name", None) or str(sym)
                if n:
                    res.exports.append(n)
            for lib in getattr(binary, "libraries", []) or []:
                res.libraries.append(str(lib))
    except Exception as e:  # noqa: BLE001
        res.notes.append(f"lief_error: {e}")
        # Fall back to the minimal parser so we still surface something.
        if fmt == "pe":
            mini = _parse_pe_minimal(data)
        else:
            mini = _parse_elf_minimal(data)
        if mini.sections and not res.sections:
            res.sections = mini.sections
        if mini.bitness and not res.bitness:
            res.bitness = mini.bitness
        if mini.machine and not res.machine:
            res.machine = mini.machine
    return res
