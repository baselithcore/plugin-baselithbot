"""Self-contained HTML report renderer for the evaluation harness (ADR-0016).

No external template engine, no JS dependency. Inline CSS for portability.
"""

from __future__ import annotations

from html import escape

from .models import CaseScore, EvalResult, GateOutcome

_CSS = """
:root { color-scheme: light dark; }
body { font: 14px/1.5 -apple-system, system-ui, sans-serif; margin: 2rem; max-width: 1100px; }
h1, h2 { margin: 1.2rem 0 0.4rem; }
.kpi { display: inline-block; padding: 0.6rem 1rem; margin-right: 0.5rem;
       border: 1px solid #ccc; border-radius: 6px; min-width: 120px; }
.kpi .v { font-size: 1.6rem; font-weight: 600; display: block; }
.kpi .l { color: #666; font-size: 0.85rem; }
table { border-collapse: collapse; margin: 0.8rem 0; }
th, td { border: 1px solid #ccc; padding: 0.35rem 0.7rem; text-align: left; }
th { background: rgba(0,0,0,0.04); }
.pass { color: #137333; font-weight: 600; }
.fail { color: #b3261e; font-weight: 600; }
.warn { color: #b06000; font-weight: 600; }
details { margin: 0.4rem 0; }
summary { cursor: pointer; }
.muted { color: #666; }
.matrix td.diag { background: rgba(19,115,51,0.08); font-weight: 600; }
.matrix td.off { background: rgba(179,38,30,0.05); }
"""


def _row(*cells: object) -> str:
    return "<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in cells) + "</tr>"


def _kpi(label: str, value: str) -> str:
    return f'<div class="kpi"><span class="v">{escape(value)}</span><span class="l">{escape(label)}</span></div>'


def _confusion_table(result: EvalResult) -> str:
    labels = result.confusion.labels
    head = "<tr><th>expected ↓ / predicted →</th>" + "".join(f"<th>{escape(lab)}</th>" for lab in labels) + "</tr>"
    body_rows: list[str] = []
    for exp in labels:
        cells = [f"<th>{escape(exp)}</th>"]
        row = result.confusion.cells.get(exp, {})
        for pred in labels:
            v = row.get(pred, 0)
            cls = "diag" if exp == pred else ("off" if v else "")
            cells.append(f'<td class="{cls}">{v}</td>')
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<table class="matrix">{head}{"".join(body_rows)}</table>'


def _per_rule_table(result: EvalResult) -> str:
    rows = [
        _row(r.rule_id, r.tp, r.fp, r.fn, f"{r.precision:.3f}", f"{r.recall:.3f}", f"{r.f1:.3f}")
        for r in result.per_rule
    ]
    head = "<tr><th>rule_id</th><th>TP</th><th>FP</th><th>FN</th><th>P</th><th>R</th><th>F1</th></tr>"
    return f"<table>{head}{''.join(rows) or '<tr><td colspan=7 class=muted>no rules scored</td></tr>'}</table>"


def _per_agent_table(result: EvalResult) -> str:
    rows = [_row(a.agent, a.findings_emitted, a.findings_matched) for a in result.per_agent]
    head = "<tr><th>agent</th><th>emitted</th><th>matched</th></tr>"
    return f"<table>{head}{''.join(rows) or '<tr><td colspan=3 class=muted>no agent attribution</td></tr>'}</table>"


def _case_block(case_score: CaseScore) -> str:
    head = (
        f"<summary><strong>{escape(case_score.case_id)}</strong> · "
        f"TP={case_score.tp} FP={case_score.fp} FN={case_score.fn} · "
        f"P={case_score.precision:.2f} R={case_score.recall:.2f} F1={case_score.f1:.2f} · "
        f"{case_score.latency_ms:.0f}ms"
        + (f" · <span class=fail>error: {escape(case_score.error)}</span>" if case_score.error else "")
        + "</summary>"
    )
    matched = "".join(
        _row(m.rule_id, m.severity, m.agent or "—", (m.matched_evidence or "")[:120]) for m in case_score.matched
    )
    spurious = "".join(
        _row(m.rule_id, m.severity, m.agent or "—", (m.matched_evidence or "")[:120]) for m in case_score.spurious
    )
    missed = "".join(
        _row(m.rule_id, m.severity, m.policy_id or "—", (m.evidence_contains or "")[:120]) for m in case_score.missed
    )

    def section(title: str, rows: str, cols: list[str]) -> str:
        head_cells = "".join(f"<th>{escape(c)}</th>" for c in cols)
        body = rows or f"<tr><td colspan={len(cols)} class=muted>none</td></tr>"
        return f"<h3>{escape(title)}</h3><table><tr>{head_cells}</tr>{body}</table>"

    body = (
        section("Matched", matched, ["rule_id", "severity", "agent", "evidence"])
        + section("Spurious (false positives)", spurious, ["rule_id", "severity", "agent", "evidence"])
        + section("Missed (false negatives)", missed, ["rule_id", "severity", "policy_id", "expected_text"])
    )
    return f"<details>{head}{body}</details>"


def render_html(result: EvalResult, gate: GateOutcome | None = None, title: str = "doCheck Eval Report") -> str:
    metric = result.metric_dict()
    gate_html = ""
    if gate is not None:
        status = "PASS" if gate.passed else "FAIL"
        cls = "pass" if gate.passed else "fail"
        deltas = ", ".join(f"{k} Δ{v:+.4f}" for k, v in gate.deltas.items()) or "—"
        failures = (
            "<ul>" + "".join(f"<li>{escape(f)}</li>" for f in gate.failures) + "</ul>"
            if gate.failures
            else "<p class=muted>no failures</p>"
        )
        gate_html = (
            f'<h2>Regression gate: <span class="{cls}">{status}</span></h2>'
            f"<p class=muted>{escape(deltas)}</p>{failures}"
        )

    cases_html = "".join(_case_block(cs) for cs in result.cases)

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title><style>{_CSS}</style></head><body>"
        f"<h1>{escape(title)}</h1>"
        f'<p class="muted">mode: {escape(result.mode)} · '
        f"started {escape(result.started_at)} · finished {escape(result.finished_at)}</p>"
        + _kpi("precision", f"{metric['precision']:.3f}")
        + _kpi("recall", f"{metric['recall']:.3f}")
        + _kpi("F1", f"{metric['f1']:.3f}")
        + _kpi("cases", str(len(result.cases)))
        + _kpi("TP / FP / FN", f"{result.tp} / {result.fp} / {result.fn}")
        + gate_html
        + "<h2>Confusion matrix (severity)</h2>"
        + _confusion_table(result)
        + "<h2>Per-rule metrics</h2>"
        + _per_rule_table(result)
        + "<h2>Per-agent attribution</h2>"
        + _per_agent_table(result)
        + "<h2>Cases</h2>"
        + cases_html
        + "</body></html>"
    )
