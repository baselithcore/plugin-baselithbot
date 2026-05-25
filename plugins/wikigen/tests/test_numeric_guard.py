"""Test del numeric guard (vincolo di non-fabbricazione di metriche)."""

from __future__ import annotations

from llm_wiki.agents import numeric_guard as g


def _whitepaper_context() -> str:
    return (
        "### Industry trends\n"
        "Whitepaper di posizionamento strategico. Le organizzazioni "
        "leader hanno aumentato gli investimenti del 25% negli ultimi "
        "trimestri. Il tempo medio di adozione si misura in mesi, non "
        "settimane. Riferimento al benchmark del 2024."
    )


def _operational_context() -> str:
    return (
        "### Latenza target\n"
        "Threshold p99 < 30 ms. Errore se la rolling window di 5 minuti "
        "supera il 2.5%. Costo stimato €1.500 al mese per cluster da 4 "
        "nodi (4 GB RAM ciascuno)."
    )


# --- extraction ------------------------------------------------------------


def test_extract_percentage() -> None:
    claims = g.extract_numeric_claims("La crescita è del 25% YoY.")
    assert len(claims) == 1
    assert claims[0].core == "25"
    assert claims[0].family == "percent"
    assert claims[0].unit == "%"


def test_extract_duration_no_space() -> None:
    claims = g.extract_numeric_claims("Latenza target 30ms p99.")
    assert any(c.core == "30" and c.family == "time" and c.unit == "ms" for c in claims)


def test_extract_duration_with_space() -> None:
    claims = g.extract_numeric_claims("Threshold p99 < 30 ms.")
    assert any(c.core == "30" and c.family == "time" for c in claims)


def test_extract_currency_prefix() -> None:
    claims = g.extract_numeric_claims("Costo €1.500 al mese.")
    assert any(c.core == "1500" and c.family == "currency" for c in claims)


def test_extract_currency_suffix() -> None:
    claims = g.extract_numeric_claims("Budget 1500 EUR.")
    assert any(c.core == "1500" and c.family == "currency" for c in claims)


def test_extract_byte_size() -> None:
    claims = g.extract_numeric_claims("Cluster con 4 GB RAM.")
    assert any(c.core == "4" and c.family == "byte" for c in claims)


def test_decimal_comma_normalization() -> None:
    claims = g.extract_numeric_claims("Errore 2,5% del totale.")
    assert any(c.core == "2.5" and c.family == "percent" for c in claims)


def test_year_filtered_out_by_default() -> None:
    """Anno a 4 cifre standalone non deve sporcare i claim."""
    claims = g.extract_numeric_claims(
        "Riferimento al benchmark del 2024.", include_generic=True
    )
    assert not any(c.core == "2024" for c in claims)


def test_generic_off_by_default() -> None:
    """Numeri standalone senza unit non vengono catturati se ``include_generic=False``."""
    claims = g.extract_numeric_claims("Sono coinvolti 3 team operativi.")
    assert claims == []


def test_generic_on_captures_standalone() -> None:
    claims = g.extract_numeric_claims(
        "Throughput 1500 record processati.", include_generic=True
    )
    assert any(c.core == "1500" for c in claims)


# --- analyze ---------------------------------------------------------------


def test_fabricated_percentage_flagged() -> None:
    answer = "Le organizzazioni hanno aumentato gli investimenti del 73% nel trimestre."
    report = g.analyze(answer, _whitepaper_context())
    assert report.has_violations
    assert any(c.core == "73" for c in report.unsupported)


def test_supported_percentage_passes() -> None:
    answer = "Gli investimenti sono cresciuti del 25% YoY come riportato nel documento."
    report = g.analyze(answer, _whitepaper_context())
    assert not report.has_violations


def test_fabricated_duration_flagged() -> None:
    answer = "La latenza target è di 100 ms con tolleranza minima."
    report = g.analyze(answer, _operational_context())
    assert report.has_violations
    assert any(c.core == "100" and c.family == "time" for c in report.unsupported)


def test_supported_duration_passes() -> None:
    answer = "La latenza p99 è sotto 30 ms come da spec."
    report = g.analyze(answer, _operational_context())
    assert not report.has_violations


def test_cross_family_not_supported() -> None:
    """``5%`` nell'answer non deve essere validato da ``5 minuti`` nel CONTESTO."""
    context = "Il rollout dura 5 minuti complessivi."
    answer = "La quota è del 5%."
    report = g.analyze(answer, context)
    assert report.has_violations


def test_decimal_separator_robustness() -> None:
    """``2,5%`` nell'answer matcha ``2.5%`` nel CONTESTO e viceversa."""
    context = "Errore se supera il 2.5% del totale."
    answer = "Limite ammesso: 2,5% di errore."
    report = g.analyze(answer, context)
    assert not report.has_violations


def test_empty_inputs() -> None:
    assert g.analyze("", "").has_violations is False
    assert (
        g.analyze("Risposta senza numeri.", "Contesto vuoto.").has_violations is False
    )


# --- repair feedback / strip ----------------------------------------------


def test_repair_feedback_lists_violations() -> None:
    answer = "Latenza misurata: 73 ms con uptime del 99,9%."
    report = g.analyze(answer, _operational_context())
    feedback = g.repair_feedback(report)
    assert "NUMERIC CLAIM VIOLATION" in feedback
    assert "73 ms" in feedback or "73ms" in feedback


def test_strip_redacts_unsupported() -> None:
    answer = "Latenza misurata: 73 ms con throughput rilevante."
    report = g.analyze(answer, _operational_context())
    redacted = g.strip_unsupported_numerics(answer, report)
    assert "73 ms" not in redacted
    assert "[dato non verificato]" in redacted


def test_strip_noop_when_no_violations() -> None:
    answer = "Latenza p99 sotto 30 ms come da spec."
    report = g.analyze(answer, _operational_context())
    assert g.strip_unsupported_numerics(answer, report) == answer
