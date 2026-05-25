"""Test del classificatore di intento query ↔ registro CONTESTO.

Garantisce che lo scope-warning venga prepended SOLO quando una domanda
operativa incontra un CONTESTO concettuale — la fattispecie precisa che
i criteri di valutazione segnalavano come hallucination critica
("come creare un agent?" su un whitepaper Anthropic).

Falsi positivi (warning su query concettuali o su contesti già
operativi) compromettono la fluidità delle risposte normali, quindi
il test copre anche i casi che NON devono triggerare.
"""

from __future__ import annotations

from llm_wiki.agents.intent_classifier import (
    analyze,
    classify_context_register,
    classify_query_intent,
)


def _conceptual_corpus() -> str:
    return (
        "### Industry leaders\n"
        "Pagina: [[concepts/industry-leaders]]\n"
        "Sezione: Industry leaders\n"
        "Cita come: [[concepts/industry-leaders#Industry leaders]]\n\n"
        "Il documento fa riferimento a 'leading organizations' in senso "
        "generico, senza elencare nomi specifici. Whitepaper, executive "
        "summary, panoramica della strategia con principi e obiettivi."
    )


def _operational_corpus() -> str:
    return (
        "### Deploy runbook\n"
        "Pagina: [[sources/deploy-runbook]]\n"
        "Sezione: Deploy\n"
        "Cita come: [[sources/deploy-runbook#Deploy]]\n\n"
        "Prerequisiti: kubectl configurato. Eseguire:\n"
        "```bash\n"
        "kubectl rollout restart deployment/api\n"
        "kubectl logs -f deployment/api --tail=200\n"
        "```\n"
        "Verifica con `curl -sf https://api/health`."
    )


def test_operational_query_against_conceptual_context_triggers_warning() -> None:
    question = "come creare un agent? quali sono i passi per eseguire il deploy?"
    report = analyze(question, _conceptual_corpus())
    assert report.query_intent == "operational"
    assert report.context_register == "conceptual"
    assert report.mismatch is True
    assert "SCOPE WARNING" in report.warning_block()


def test_operational_query_with_operational_context_no_warning() -> None:
    question = "come faccio il deploy? quale comando devo eseguire?"
    report = analyze(question, _operational_corpus())
    assert report.query_intent == "operational"
    assert report.context_register == "operational"
    assert report.mismatch is False
    assert report.warning_block() == ""


def test_conceptual_query_no_warning_even_on_conceptual_context() -> None:
    question = "qual è la filosofia di Anthropic riguardo gli agenti enterprise?"
    report = analyze(question, _conceptual_corpus())
    assert report.query_intent in {"conceptual", "mixed", "unknown"}
    assert report.mismatch is False


def test_explicit_doc_register_in_hits_overrides_regex() -> None:
    # Contesto testuale che euristicamente sembra "concettuale" (zero
    # code fence, zero CLI token, prosa minimale) ma i payload espongono
    # doc_register=operational → il majority vote autorevole prevale.
    hits = [
        {"payload": {"doc_register": "operational", "text": "runbook ufficiale"}},
        {"payload": {"doc_register": "operational", "text": "altra parte runbook"}},
    ]
    question = "come faccio il deploy di un servizio in produzione?"
    report = analyze(question, "prosa generica senza marker", hits=hits)
    assert report.context_register == "operational"
    assert report.mismatch is False


def test_explicit_doc_register_conceptual_keeps_warning() -> None:
    hits = [
        {"payload": {"doc_register": "conceptual", "text": "whitepaper Anthropic"}},
        {"payload": {"doc_register": "conceptual", "text": "vision aziendale"}},
    ]
    question = "come creare un agent? quali comandi devo eseguire per il deploy?"
    report = analyze(question, "prosa generica", hits=hits)
    assert report.query_intent == "operational"
    assert report.context_register == "conceptual"
    assert report.mismatch is True


def test_empty_inputs_handled() -> None:
    intent, signal = classify_query_intent("")
    assert intent == "unknown"
    assert signal == 0

    register, diag = classify_context_register("")
    assert register == "unknown"
    assert diag["code_blocks"] == 0
