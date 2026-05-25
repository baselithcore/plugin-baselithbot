"""Report export: Markdown + JSON canonico. PDF rendering deferred to UI (jsPDF).

Server emits Markdown that UI converts to PDF. Avoids server-side LaTeX/wkhtmltopdf
dependency and keeps zero-egress posture.
"""

import json
from typing import Any


def report_to_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    doc = report.get("doc", {})
    lines.append(f"# doCheck Report — {doc.get('name', report.get('doc_id', '—'))}")
    lines.append("")
    lines.append(f"**Score:** {report.get('score', 0)}/100  ")
    lines.append(f"**Report ID:** `{report.get('report_id', '—')}`  ")
    lines.append(f"**Document SHA-256:** `{doc.get('sha256', '—')}`  ")
    lines.append(f"**Engine:** `{report.get('audit', {}).get('engine_version', '?')}`  ")
    lines.append(f"**Model:** `{report.get('audit', {}).get('model', '?')}`")
    lines.append("")

    by_sev = report.get("by_severity", {})
    lines.append("## Summary")
    lines.append(f"- ❌ FAIL: **{by_sev.get('FAIL', 0)}**")
    lines.append(f"- ⚠️  WARN: **{by_sev.get('WARN', 0)}**")
    lines.append(f"- ✅ PASS: **{by_sev.get('PASS', 0)}**")
    lines.append("")

    summary = report.get("summary")
    if summary:
        lines.append(f"> {summary}")
        lines.append("")

    lines.append("## Findings")
    for f in report.get("findings", []):
        lines.append(f"### `{f['rule_id']}` — {f['severity']}")
        ev = f.get("evidence", {})
        lines.append(
            f"- **Evidence:** page {ev.get('page')} · lines {ev.get('line_start')}–{ev.get('line_end')}"  # noqa: RUF001
        )
        lines.append(f"- **Confidence:** {f.get('confidence', 0):.2f}")
        ref = f.get("policy_ref", {})
        lines.append(f"- **Policy:** `{ref.get('policy_id')}@{ref.get('version')}` — {ref.get('title')}")
        lines.append("")
        lines.append("**Excerpt:**")
        lines.append(f"> {ref.get('excerpt', '')}")
        lines.append("")
        lines.append(f"**Explanation:** {f.get('explanation', '')}")
        if f.get("suggestion"):
            lines.append("")
            lines.append(f"**Suggestion:** {f['suggestion']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Signature")
    lines.append("")
    lines.append(f"```\n{report.get('signature', '')}\n```")
    return "\n".join(lines)


def report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
