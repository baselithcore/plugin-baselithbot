"""
Deterministic clinical intake-report renderer.

Builds a Markdown intake report from the live :class:`SymptomMatrix` using
the appoint-ready template (Primary concern / HPI / Pertinent negatives /
Relevant medical history / Medications / Red flags). The renderer is
intentionally LLM-free so it always produces a stable, validator-friendly
artifact, even when the model is offline or schema-non-conforming.

Used by the interview flow to ship a live preview after every turn, and by
the triage flow to attach a final report to ``TriageReport.intake_report``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models.clinical import DifferentialDiagnosis, SymptomMatrix


def render_intake_report(
    matrix: SymptomMatrix,
    *,
    medications: list[str] | None = None,
    risk_factors: list[str] | None = None,
    allergies: list[str] | None = None,
    differential: DifferentialDiagnosis | None = None,
    triage: dict | None = None,
    discriminator_answers: list[dict[str, str]] | None = None,
    patient_pseudonym: str | None = None,
    session_id: str | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Return a Markdown intake report. Empty sections collapse to "—".

    When ``differential`` and/or ``triage`` are supplied, an additional
    "Valutazione clinica" section is appended so the document doubles as a
    complete pre-triage handoff. The renderer stays LLM-free.
    """

    when = generated_at or datetime.now(timezone.utc)
    primary = _format_primary_concern(matrix)
    hpi = _format_hpi(matrix)
    negatives = _format_list(matrix.denied_symptoms)
    # Caller-provided lists take precedence; fall back to matrix fields so
    # the renderer is usable from both interview_flow (snap-aware) and
    # triage_flow (matrix-only) without coupling.
    history = _format_list(risk_factors or matrix.past_medical_history)
    meds = _format_list(medications or matrix.medications)
    allergy_lines = _format_list(allergies or matrix.allergies)
    red_flags = _format_list(matrix.red_flags)

    header_meta: list[str] = []
    if patient_pseudonym:
        header_meta.append(f"**Paziente:** `{patient_pseudonym}`")
    if session_id:
        header_meta.append(f"**Sessione:** `{session_id}`")
    header_meta.append(f"**Generato:** {when.strftime('%Y-%m-%d %H:%M UTC')}")
    header_block = " · ".join(header_meta)

    body = f"# Pre-triage clinico\n{header_block}\n\n"

    # Clinical synthesis paragraph — short prose summary the clinician can
    # read in 5 seconds before diving into the structured sections.
    synthesis = _format_clinical_synthesis(matrix, differential, triage)
    if synthesis:
        body += "### Sintesi clinica\n" + synthesis + "\n\n"

    body += (
        "### Motivo della visita\n"
        f"{primary}\n\n"
        "### Storia della malattia attuale (HPI)\n"
        f"{hpi}\n\n"
        "### Sintomi negati (pertinent negatives)\n"
        f"{negatives}\n\n"
        "### Anamnesi patologica rilevante\n"
        f"{history}\n\n"
        "### Allergie\n"
        f"{allergy_lines}\n\n"
        "### Terapia in corso\n"
        f"{meds}\n\n"
        "### Red flag\n"
        f"{red_flags}\n\n"
    )

    if discriminator_answers:
        disc_block = _format_discriminator_section(discriminator_answers)
        if disc_block:
            body += disc_block

    if triage:
        body += _format_triage_section(triage)
    if differential and differential.hypotheses:
        body += _format_differential_section(differential)

    body += (
        "### Disclaimer\n"
        "Decisione preliminare automatica. Validazione clinica umana "
        "obbligatoria prima di qualsiasi atto medico.\n\n"
        f"_Aggiornato: {when.strftime('%Y-%m-%d %H:%M UTC')}_"
    )
    return body


def _format_clinical_synthesis(
    matrix: SymptomMatrix,
    differential: DifferentialDiagnosis | None,
    triage: dict | None,
) -> str | None:
    if not matrix.symptoms:
        return None
    chief = matrix.symptoms[0]
    parts: list[str] = [f"Paziente riferisce **{chief.canonical_name}**"]
    if chief.body_site:
        parts.append(f"in sede {chief.body_site}")
    if chief.severity_nrs is not None:
        parts.append(f"intensità NRS {chief.severity_nrs}/10")
    if chief.onset is not None:
        parts.append(f"esordio {chief.onset.strftime('%Y-%m-%d %H:%M UTC')}")
    if chief.character:
        parts.append("qualità " + ", ".join(chief.character[:3]))
    if len(matrix.symptoms) > 1:
        others = ", ".join(s.canonical_name for s in matrix.symptoms[1:4])
        parts.append(f"sintomi associati: {others}")
    if matrix.denied_symptoms:
        parts.append("pertinent negatives: " + ", ".join(matrix.denied_symptoms[:4]))
    line1 = ", ".join(parts).rstrip(",") + "."

    line2 = ""
    if differential and differential.hypotheses:
        top = differential.hypotheses[0]
        line2 = (
            f"Ipotesi diagnostica prevalente: **{top.condition}**"
            + (f" (ICD `{top.icd10}`)" if top.icd10 else "")
            + f", confidence {int(round(top.confidence * 100))}%."
        )
        if len(differential.hypotheses) > 1:
            second = differential.hypotheses[1]
            line2 += (
                f" Diagnosi differenziale: {second.condition}"
                + f" ({int(round(second.confidence * 100))}%)."
            )

    line3 = ""
    if differential and differential.hypotheses:
        top = differential.hypotheses[0]
        if top.recommended_workup:
            line3 = (
                "Workup raccomandato: " + ", ".join(top.recommended_workup[:4]) + "."
            )

    line4 = ""
    if triage and triage.get("code"):
        latency = triage.get("target_latency_minutes")
        latency_str = (
            "valutazione immediata"
            if latency == 0
            else (f"valutazione entro {latency} min" if latency else "—")
        )
        line4 = f"Codice triage suggerito: **{triage['code']}** ({latency_str})."

    return "\n\n".join(s for s in [line1, line2, line3, line4] if s)


def _format_discriminator_section(answers: list[dict[str, str]]) -> str:
    rows: list[str] = []
    for entry in answers:
        question = entry.get("question") or "—"
        ans = (entry.get("answer") or "").strip() or "(senza risposta)"
        condition = entry.get("condition")
        suffix = f" _(probe per {condition})_" if condition else ""
        rows.append(f"- **D:** {question}{suffix}\n  **R:** _{ans}_")
    if not rows:
        return ""
    return "### Domande discriminanti\n" + "\n".join(rows) + "\n\n"


def _format_triage_section(triage: dict) -> str:
    code = str(triage.get("code", "—"))
    rationale = str(triage.get("rationale") or "—")
    latency = triage.get("target_latency_minutes")
    overrides = triage.get("red_flag_overrides") or []
    latency_str = (
        "immediato" if latency == 0 else (f"≤ {latency} min" if latency else "—")
    )
    lines = [
        "### Triage",
        f"- **Codice:** `{code}` · target {latency_str}",
        f"- **Razionale:** {rationale}",
    ]
    if overrides:
        lines.append("- **Override red-flag:**")
        for o in overrides:
            lines.append(f"  - {o}")
    return "\n".join(lines) + "\n\n"


def _format_differential_section(ddx: DifferentialDiagnosis) -> str:
    out: list[str] = [
        "### Valutazione clinica",
        f"_Modello:_ `{ddx.model_id}`",
    ]
    if ddx.notes:
        out.append(f"_Note:_ {ddx.notes}")
    out.append("")
    for i, h in enumerate(ddx.hypotheses[:5], start=1):
        confidence_pct = int(round(h.confidence * 100))
        line = f"**{i}. {h.condition}**"
        if h.icd10:
            line += f" · ICD `{h.icd10}`"
        line += f" · confidence **{confidence_pct}%**"
        out.append(line)
        if h.supporting_findings:
            out.append("  - _A favore:_ " + ", ".join(h.supporting_findings[:6]))
        if h.contradicting_findings:
            out.append("  - _Contro:_ " + ", ".join(h.contradicting_findings[:6]))
        if h.recommended_workup:
            out.append(
                "  - _Workup raccomandato:_ " + ", ".join(h.recommended_workup[:6])
            )
    return "\n".join(out) + "\n\n"


def _format_primary_concern(matrix: SymptomMatrix) -> str:
    if not matrix.symptoms:
        return "—"
    chief = matrix.symptoms[0]
    bits: list[str] = [chief.canonical_name]
    if chief.body_site:
        bits.append(f"({chief.body_site})")
    if chief.icd10_hint:
        bits.append(f"`{chief.icd10_hint}`")
    return " ".join(bits)


def _format_hpi(matrix: SymptomMatrix) -> str:
    if not matrix.symptoms:
        return "—"
    lines: list[str] = []
    for sym in matrix.symptoms:
        parts: list[str] = [f"**{sym.canonical_name}**"]
        if sym.body_site:
            parts.append(f"sede: {sym.body_site}")
        if sym.onset is not None:
            parts.append(f"esordio: {sym.onset.strftime('%Y-%m-%d %H:%M UTC')}")
        if sym.severity_nrs is not None:
            parts.append(f"NRS: {sym.severity_nrs}/10")
        if sym.character:
            parts.append(f"qualità: {', '.join(sym.character[:4])}")
        if sym.raw_quote:
            parts.append(f'"_{sym.raw_quote.strip()[:140]}_"')
        lines.append("- " + " · ".join(parts))
    if matrix.temporal_sequence:
        seq = ", ".join(
            f"{link.source} {link.relation.lower()} {link.target}"
            for link in matrix.temporal_sequence[:4]
        )
        lines.append(f"- _Sequenza:_ {seq}")
    return "\n".join(lines)


def _format_list(items: list[str]) -> str:
    if not items:
        return "—"
    return "\n".join(f"- {it}" for it in items)
