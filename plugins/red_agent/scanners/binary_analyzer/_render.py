"""Markdown renderers for binary-analyzer finding descriptions.

Operator-friendly markdown bodies for the overview finding and the
per-indicator finding descriptions.
"""

from __future__ import annotations

from plugins.red_agent.models import Target
from plugins.red_agent.scanners._binary_advanced import missing_mitigations
from plugins.red_agent.scanners._binary_iocs import threat_intel_pivot_links
from plugins.red_agent.scanners._binary_parser import ParseResult
from plugins.red_agent.scanners.binary_analyzer._helpers import (
    _format_pe_timestamp,
    _human_size,
)


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
