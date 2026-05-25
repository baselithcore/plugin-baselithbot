"""Advanced PE/ELF static analysis primitives.

Pure-stdlib implementations of the classical reverse-engineering signals
that drive enterprise malware triage:

* **imphash** — Mandiant compiler-import fingerprint (clusters samples by
  import-table layout; widely used by VirusTotal, MISP, YARA rules).
* **Rich Header** — Microsoft compiler/linker fingerprint encoded between
  the DOS stub and the PE signature. Comp.id mismatches are a strong
  attribution signal (used by FireEye, ESET, Mandiant in APT reports).
* **DLL Characteristics** — exploit-mitigation posture
  (ASLR / DEP / CFG / SafeSEH / HighEntropyVA / NXCOMPAT).
* **Packer detection** — section-name signature catalogue
  (UPX, Themida, ASPack, VMProtect, MPRESS, PECompact, Enigma, Petite,
  Confuser, ConfuserEx, Obsidium, FSG).
* **Overlay analysis** — bytes appended after the last PE section, with
  Shannon entropy. Common malware staging trick.
* **Embedded PE / ELF carving** — additional MZ / ELF magic past offset 0.
* **Timestamp anomaly** — TimeDateStamp in the future, the Unix epoch, or
  the well-known "Reproducible Builds" sentinel (0x5DC4D000).
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from typing import Iterable

# Mandiant ordinal lookup for the imphash, matching the canonical pefile
# implementation. Trimmed to the entries we know are emitted by Windows
# loaders the analyst will encounter in practice.
_ORDINAL_LOOKUP: dict[str, dict[int, str]] = {
    "ws2_32": {
        1: "accept",
        2: "bind",
        3: "closesocket",
        4: "connect",
        5: "getpeername",
        6: "getsockname",
        7: "getsockopt",
        8: "htonl",
        9: "htons",
        10: "ioctlsocket",
        11: "inet_addr",
        12: "inet_ntoa",
        13: "listen",
        14: "ntohl",
        15: "ntohs",
        16: "recv",
        17: "recvfrom",
        18: "select",
        19: "send",
        20: "sendto",
        21: "setsockopt",
        22: "shutdown",
        23: "socket",
        115: "WSAStartup",
        116: "WSACleanup",
    },
    "wsock32": {
        1: "accept",
        2: "bind",
        3: "closesocket",
        4: "connect",
        13: "listen",
        16: "recv",
        19: "send",
        23: "socket",
    },
}


# Section-name signatures used by mainstream packers. Names are case-
# insensitive substrings — packers occasionally namespace via
# ``UPX0/UPX1`` so we match prefixes rather than exact equality.
_PACKER_SIGNATURES: tuple[tuple[str, str], ...] = (
    ("upx", "UPX"),
    (".vmp", "VMProtect"),
    (".themida", "Themida"),
    (".taz", "Themida"),
    (".aspack", "ASPack"),
    (".adata", "ASPack"),
    (".pec", "PECompact"),
    (".mpress", "MPRESS"),
    (".enigma", "Enigma Protector"),
    (".petite", "Petite"),
    (".nsp", "NsPack"),
    (".rlpack", "RLPack"),
    ("obsidium", "Obsidium"),
    (".fsg", "FSG"),
    (".y0da", "Yoda"),
    (".confuser", "ConfuserEx"),
    (".winlice", "WinLicense"),
    (".tls", ""),  # tls section is benign — placeholder so look-up table
    # has neutral hit
)


# IMAGE_DLLCHARACTERISTICS bits (winnt.h).
_DLL_CHARACTERISTICS: tuple[tuple[int, str], ...] = (
    (0x0020, "HIGH_ENTROPY_VA"),
    (0x0040, "DYNAMIC_BASE"),  # ASLR
    (0x0080, "FORCE_INTEGRITY"),
    (0x0100, "NX_COMPAT"),  # DEP
    (0x0200, "NO_ISOLATION"),
    (0x0400, "NO_SEH"),
    (0x0800, "NO_BIND"),
    (0x1000, "APPCONTAINER"),
    (0x2000, "WDM_DRIVER"),
    (0x4000, "GUARD_CF"),  # Control Flow Guard
    (0x8000, "TERMINAL_SERVER_AWARE"),
)

# Sentinel timestamps the linker uses when a real time is unavailable —
# distinct from anomalies, but still triage-noteworthy.
_REPRODUCIBLE_BUILD_TS = 0x5DC4D000


@dataclass
class RichHeaderEntry:
    comp_id: int
    build_id: int
    count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "comp_id": self.comp_id,
            "build_id": self.build_id,
            "count": self.count,
        }


@dataclass
class AdvancedPE:
    """Subset of advanced PE fields surfaced to the scanner."""

    imphash: str = ""
    rich_header: list[RichHeaderEntry] = field(default_factory=list)
    rich_xor_key: int = 0
    dll_characteristics: int = 0
    mitigations: list[str] = field(default_factory=list)
    overlay_offset: int = 0
    overlay_size: int = 0
    overlay_entropy: float = 0.0
    packer_hits: list[str] = field(default_factory=list)
    embedded_offsets: list[tuple[str, int]] = field(default_factory=list)
    timestamp_anomaly: str = ""
    pe_checksum_in_header: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "imphash": self.imphash,
            "rich_header": [e.to_dict() for e in self.rich_header],
            "rich_xor_key": self.rich_xor_key,
            "dll_characteristics": self.dll_characteristics,
            "mitigations": self.mitigations,
            "overlay_offset": self.overlay_offset,
            "overlay_size": self.overlay_size,
            "overlay_entropy": self.overlay_entropy,
            "packer_hits": self.packer_hits,
            "embedded_offsets": [
                {"format": k, "offset": o} for k, o in self.embedded_offsets
            ],
            "timestamp_anomaly": self.timestamp_anomaly,
            "pe_checksum_in_header": self.pe_checksum_in_header,
        }


# ──────────────────────────────────────────────────────────────────────
# Imphash


def _normalise_lib(name: str) -> str:
    n = name.lower()
    for ext in (".dll", ".ocx", ".sys"):
        if n.endswith(ext):
            n = n[: -len(ext)]
            break
    return n


def compute_imphash(import_pairs: Iterable[tuple[str, str | int]]) -> str:
    """MD5 of "dll.func" pairs joined with commas (Mandiant spec)."""
    parts: list[str] = []
    for lib, sym in import_pairs:
        lib_norm = _normalise_lib(lib)
        if isinstance(sym, int):
            table = _ORDINAL_LOOKUP.get(lib_norm)
            name = table.get(sym, f"ord{sym}") if table else f"ord{sym}"
        else:
            name = sym.lower()
        parts.append(f"{lib_norm}.{name}")
    if not parts:
        return ""
    return hashlib.md5(
        ",".join(parts).encode("ascii"), usedforsecurity=False
    ).hexdigest()


# ──────────────────────────────────────────────────────────────────────
# Rich Header
#
# Layout (between DOS stub end and PE\0\0):
#
#   ... DanS-XOR'd-block ... Rich <xor_key>
#
# We walk backwards from the "Rich" marker, dword-decrypt with the
# trailing 4-byte key until we find the "DanS" magic; the entries in
# between are (comp_id<<16 | build_id, count) DWORD pairs.


def parse_rich_header(data: bytes, e_lfanew: int) -> tuple[int, list[RichHeaderEntry]]:
    """Return ``(xor_key, entries)`` or ``(0, [])`` if absent / malformed."""
    if e_lfanew < 0x80 or e_lfanew > len(data):
        return 0, []
    blob = data[:e_lfanew]
    rich_idx = blob.rfind(b"Rich")
    if rich_idx < 0 or rich_idx + 8 > len(blob):
        return 0, []
    xor_key = struct.unpack_from("<I", blob, rich_idx + 4)[0]
    # Decrypt dword-by-dword backwards from rich_idx down to 0x80.
    entries: list[RichHeaderEntry] = []
    cursor = rich_idx - 8  # skip the trailing Rich+key pair itself
    while cursor >= 0x80:
        v1 = struct.unpack_from("<I", blob, cursor)[0] ^ xor_key
        v2 = struct.unpack_from("<I", blob, cursor + 4)[0] ^ xor_key
        if v1 == 0x536E6144:  # "DanS"
            break
        comp_id = (v1 >> 16) & 0xFFFF
        build_id = v1 & 0xFFFF
        count = v2
        entries.append(RichHeaderEntry(comp_id, build_id, count))
        cursor -= 8
    entries.reverse()
    return xor_key, entries


# ──────────────────────────────────────────────────────────────────────
# DLL characteristics → human-readable mitigation list


def decode_dll_characteristics(value: int) -> list[str]:
    return [name for bit, name in _DLL_CHARACTERISTICS if value & bit and name]


def missing_mitigations(value: int) -> list[str]:
    """Return mitigation flags an enterprise binary should carry."""
    required = {0x0040: "DYNAMIC_BASE", 0x0100: "NX_COMPAT", 0x4000: "GUARD_CF"}
    return [name for bit, name in required.items() if not (value & bit)]


# ──────────────────────────────────────────────────────────────────────
# Packer signatures + overlay + embedded PE/ELF carving


def detect_packers(section_names: Iterable[str]) -> list[str]:
    hits: set[str] = set()
    for name in section_names:
        lower = name.lower()
        for needle, label in _PACKER_SIGNATURES:
            if not label:
                continue
            if lower.startswith(needle):
                hits.add(label)
    return sorted(hits)


def compute_overlay(
    data: bytes, last_section_offset: int, last_section_size: int
) -> tuple[int, int, float]:
    """Detect bytes appended past the last section's raw end-of-file."""
    eof = last_section_offset + last_section_size
    if eof >= len(data):
        return 0, 0, 0.0
    overlay = data[eof:]
    from plugins.red_agent.scanners._binary_iocs import shannon_entropy

    return eof, len(overlay), round(shannon_entropy(overlay), 4)


def carve_embedded(data: bytes, *, skip_offset: int = 0) -> list[tuple[str, int]]:
    """Find additional PE / ELF magic past ``skip_offset`` (defaults to 1).

    Returns ``(format, absolute_offset)`` pairs. The first occurrence of
    each magic is reported once per kilobyte to avoid repeating noise on
    sections full of zero-padded patterns.
    """
    found: list[tuple[str, int]] = []
    seen_buckets: set[tuple[str, int]] = set()
    start = max(skip_offset, 1)
    # PE: "MZ" then a valid e_lfanew pointing at "PE\0\0".
    idx = start
    while idx < len(data) - 0x40:
        i = data.find(b"MZ", idx)
        if i < 0:
            break
        try:
            e_lfanew = struct.unpack_from("<I", data, i + 0x3C)[0]
            if (
                0 < e_lfanew < len(data) - i - 4
                and data[i + e_lfanew : i + e_lfanew + 4] == b"PE\x00\x00"
            ):
                bucket = ("pe", i // 1024)
                if bucket not in seen_buckets:
                    seen_buckets.add(bucket)
                    found.append(("pe", i))
        except struct.error:
            pass
        idx = i + 2
    # ELF: 0x7F E L F.
    idx = start
    while idx < len(data) - 4:
        i = data.find(b"\x7fELF", idx)
        if i < 0:
            break
        bucket = ("elf", i // 1024)
        if bucket not in seen_buckets:
            seen_buckets.add(bucket)
            found.append(("elf", i))
        idx = i + 4
    return found


# ──────────────────────────────────────────────────────────────────────
# Timestamp anomaly


def classify_timestamp(ts: int | None, *, now_epoch: int) -> str:
    if ts is None:
        return ""
    if ts == 0:
        return "epoch_zero"
    if ts == _REPRODUCIBLE_BUILD_TS:
        return "reproducible_build_sentinel"
    if ts > now_epoch + 24 * 3600:
        return "future_timestamp"
    if ts < 946684800:  # before 2000-01-01
        return "pre_2000_timestamp"
    return ""


# ──────────────────────────────────────────────────────────────────────
# PE import-directory walker (used by imphash)
#
# Returns (lib, name | ordinal) pairs in iteration order.


def walk_pe_imports(data: bytes) -> list[tuple[str, str | int]]:
    pairs: list[tuple[str, str | int]] = []
    try:
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        coff_off = e_lfanew + 4
        opt_off = coff_off + 0x14
        opt_size = struct.unpack_from("<H", data, coff_off + 0x10)[0]
        magic = struct.unpack_from("<H", data, opt_off)[0]
        is_pe32_plus = magic == 0x20B
        # DataDirectory[1] = Import Table.
        dd_offset = opt_off + (0x70 if is_pe32_plus else 0x60)
        if dd_offset + 16 > len(data):
            return pairs
        import_rva = struct.unpack_from("<I", data, dd_offset + 8)[0]
        if not import_rva:
            return pairs
        # Build a section table to translate RVAs.
        n_sections = struct.unpack_from("<H", data, coff_off + 2)[0]
        sec_off = opt_off + opt_size
        sections: list[tuple[int, int, int, int]] = []  # va, vsize, raw_off, raw_size
        for i in range(n_sections):
            base = sec_off + i * 0x28
            if base + 0x28 > len(data):
                return pairs
            vsize = struct.unpack_from("<I", data, base + 8)[0]
            va = struct.unpack_from("<I", data, base + 12)[0]
            raw_size = struct.unpack_from("<I", data, base + 16)[0]
            raw_off = struct.unpack_from("<I", data, base + 20)[0]
            sections.append((va, vsize, raw_off, raw_size))

        def rva_to_off(rva: int) -> int:
            for va, vsize, raw_off, raw_size in sections:
                if va <= rva < va + max(vsize, raw_size):
                    return raw_off + (rva - va)
            return -1

        # Walk import descriptors (20 bytes each, terminator = all zero).
        import_off = rva_to_off(import_rva)
        if import_off < 0:
            return pairs
        ordinal_flag = (1 << 63) if is_pe32_plus else (1 << 31)
        thunk_size = 8 if is_pe32_plus else 4
        thunk_fmt = "<Q" if is_pe32_plus else "<I"
        cursor = import_off
        while cursor + 20 <= len(data):
            orig_first_thunk = struct.unpack_from("<I", data, cursor)[0]
            name_rva = struct.unpack_from("<I", data, cursor + 12)[0]
            first_thunk = struct.unpack_from("<I", data, cursor + 16)[0]
            if orig_first_thunk == 0 and name_rva == 0 and first_thunk == 0:
                break
            cursor += 20
            name_off = rva_to_off(name_rva)
            if name_off < 0:
                continue
            end = data.find(b"\x00", name_off)
            if end < 0:
                continue
            lib = data[name_off:end].decode("ascii", errors="replace")
            thunk_rva = orig_first_thunk or first_thunk
            thunk_off = rva_to_off(thunk_rva)
            if thunk_off < 0:
                continue
            t = thunk_off
            guard = 0
            while guard < 4096 and t + thunk_size <= len(data):
                guard += 1
                value = struct.unpack_from(thunk_fmt, data, t)[0]
                if value == 0:
                    break
                if value & ordinal_flag:
                    pairs.append((lib, value & 0xFFFF))
                else:
                    hint_off = rva_to_off(value & 0x7FFFFFFF)
                    if hint_off >= 0 and hint_off + 2 < len(data):
                        sym_end = data.find(b"\x00", hint_off + 2)
                        if sym_end > 0:
                            sym = data[hint_off + 2 : sym_end].decode(
                                "ascii", errors="replace"
                            )
                            pairs.append((lib, sym))
                t += thunk_size
    except (struct.error, IndexError):
        return pairs
    return pairs
