"""Test del code-block guard (vincolo di negazione su snippet)."""

from __future__ import annotations

from llm_wiki.agents import code_block_guard as g


def _conceptual_context() -> str:
    return (
        "### Industry leaders\n"
        "Il documento fa riferimento a 'leading organizations' in senso "
        "generico. Whitepaper, executive summary, panoramica della "
        "strategia con principi e obiettivi. Niente comandi né snippet."
    )


def _operational_context_python() -> str:
    return (
        "### Deploy runbook\n"
        "Prerequisiti: kubectl configurato. Esegui:\n"
        "```python\n"
        "from k8s_client import Client\n"
        "Client().rollout_restart('api')\n"
        "```\n"
        "Verifica con la dashboard."
    )


def test_answer_with_python_on_conceptual_context_violates() -> None:
    answer = (
        "Per creare un agent segui questi passi:\n\n"
        "```python\n"
        "from anthropic import Anthropic\n"
        "client = Anthropic()\n"
        "client.messages.create(model='claude-opus-4-7', messages=[])\n"
        "```\n\n"
        "Poi configura..."
    )
    report = g.analyze(answer, _conceptual_context())
    assert report.has_violations is True
    assert report.answer_has_code_context_does_not is True
    assert len(report.answer_fences) == 1
    assert report.answer_fences[0].language == "python"


def test_answer_without_code_on_conceptual_context_ok() -> None:
    answer = (
        "Il documento descrive un approccio a tre fasi (valutazione, "
        "pilot, scaling) e non specifica passaggi tecnici di "
        "implementazione."
    )
    report = g.analyze(answer, _conceptual_context())
    assert report.has_violations is False


def test_answer_with_matching_language_on_operational_context_ok() -> None:
    answer = (
        "Il runbook prescrive:\n"
        "```python\n"
        "from k8s_client import Client\n"
        "Client().rollout_restart('api')\n"
        "```"
    )
    report = g.analyze(answer, _operational_context_python())
    assert report.has_violations is False


def test_answer_invents_language_not_in_context() -> None:
    # CONTESTO Python, risposta usa bash → violazione lingua fabbricata.
    answer = "Esegui:\n```bash\nkubectl rollout restart deployment/api\n```"
    report = g.analyze(answer, _operational_context_python())
    assert report.has_violations is True
    assert "bash" in report.answer_only_langs


def test_strip_fabricated_removes_all_fences_when_context_has_none() -> None:
    answer = "Intro.\n\n```python\nx = 1\n```\n\nConclusione."
    report = g.analyze(answer, _conceptual_context())
    stripped = g.strip_fabricated_fences(answer, report)
    assert "```python" not in stripped
    assert "x = 1" not in stripped
    assert "Intro." in stripped
    assert "Conclusione." in stripped


def test_strip_fabricated_keeps_valid_langs() -> None:
    # Risposta Python (valido) + bash (fabbricato). Strip rimuove solo bash.
    answer = (
        "Step 1:\n```python\nclient.go()\n```\n\nStep 2:\n```bash\nfake-command\n```\n"
    )
    report = g.analyze(answer, _operational_context_python())
    stripped = g.strip_fabricated_fences(answer, report)
    assert "client.go()" in stripped  # python preserved
    assert "fake-command" not in stripped


def test_repair_feedback_lists_violations() -> None:
    answer = "```python\nx=1\n```"
    report = g.analyze(answer, _conceptual_context())
    feedback = g.repair_feedback(report)
    assert "CODE BLOCK VIOLATION" in feedback
    assert "nessuno" in feedback
