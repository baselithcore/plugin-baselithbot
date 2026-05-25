"""Unit tests for `services.policy_coverage` (ADR-0014)."""

from __future__ import annotations

import asyncio
from typing import Any

from docheck.services import policy_coverage


def test_is_grounded_strict_and_loose() -> None:
    src = "Il fornitore deve consegnare entro 30 giorni dalla stipula."
    assert policy_coverage._is_grounded("Il fornitore deve consegnare", src) is True
    # Loose normalization: extra punctuation/whitespace tolerated.
    assert policy_coverage._is_grounded("Il fornitore,  deve consegnare!", src) is True
    # Not in source -> False.
    assert policy_coverage._is_grounded("Il fornitore può ritardare.", src) is False
    # Empty/short excerpt -> False under loose threshold.
    assert policy_coverage._is_grounded("", src) is False


def test_detected_matches_extracted_both_directions() -> None:
    extracted = [
        "Il fornitore deve consegnare entro 30 giorni dalla stipula del contratto.",
        "Il pagamento avviene entro 60 giorni dalla fattura.",
    ]
    # detected is substring of extracted -> match.
    assert policy_coverage._detected_matches_extracted("entro 30 giorni dalla stipula", extracted)
    # extracted is substring of detected -> still match (direction-agnostic).
    assert policy_coverage._detected_matches_extracted(
        "Il fornitore deve consegnare entro 30 giorni dalla stipula del contratto entrante.",
        extracted,
    )
    # No overlap -> no match.
    assert not policy_coverage._detected_matches_extracted("Risoluzione per inadempimento.", extracted)


def test_dedupe_obligations() -> None:
    items = [
        {"label": "a", "excerpt": "Stesso testo verbatim qui."},
        {"label": "b", "excerpt": "Stesso testo verbatim qui."},  # dup
        {"label": "c", "excerpt": "Stesso  testo   verbatim qui."},  # ws-dup
        {"label": "d", "excerpt": "Testo distinto."},
        {"label": "e", "excerpt": ""},  # dropped
    ]
    out = policy_coverage._dedupe_obligations(items)
    assert [o["label"] for o in out] == ["a", "d"]


def test_compute_coverage_happy_path(monkeypatch) -> None:
    src = (
        "Art. 1 Il fornitore deve consegnare entro 30 giorni dalla stipula. "
        "Art. 2 Il pagamento avviene entro 60 giorni. "
        "Art. 3 Non è ammessa la subappaltazione senza autorizzazione."
    )
    extracted_excerpts = [
        "Il fornitore deve consegnare entro 30 giorni dalla stipula.",
        # Art. 3 NOT extracted → should appear as gap.
    ]

    async def fake_detect(chunk_text: str) -> list[dict[str, Any]]:
        return [
            {
                "label": "termine consegna",
                "excerpt": "Il fornitore deve consegnare entro 30 giorni dalla stipula.",
                "severity_hint": "fail",
            },
            {
                "label": "termine pagamento",
                "excerpt": "Il pagamento avviene entro 60 giorni.",
                "severity_hint": "warn",
            },
            {
                "label": "subappalto",
                "excerpt": "Non è ammessa la subappaltazione senza autorizzazione.",
                "severity_hint": "fail",
            },
            {
                "label": "hallucinated",
                "excerpt": "Obbligo inventato non presente nel sorgente.",
                "severity_hint": "warn",
            },
        ]

    monkeypatch.setattr(policy_coverage, "_detect_obligations_chunk", fake_detect)

    result = asyncio.run(
        policy_coverage.compute_coverage(
            source_text=src,
            extracted_excerpts=extracted_excerpts,
            chunk_trigger_chars=10_000,
        )
    )

    # Hallucinated obligation must be dropped by grounding.
    assert result["detected_count"] == 3
    assert result["extracted_count"] == 1
    assert 0.30 <= result["coverage_ratio"] <= 0.34
    labels = sorted(g["label"] for g in result["gaps"])
    assert labels == ["subappalto", "termine pagamento"]


def test_compute_coverage_no_extracted_no_detected() -> None:
    src = "Nessuna obbligazione qui."

    async def empty_detect(chunk_text: str) -> list[dict[str, Any]]:
        return []

    import unittest.mock as mock

    with mock.patch.object(policy_coverage, "_detect_obligations_chunk", empty_detect):
        result = asyncio.run(
            policy_coverage.compute_coverage(
                source_text=src,
                extracted_excerpts=[],
                chunk_trigger_chars=10_000,
            )
        )
    assert result["extracted_count"] == 0
    assert result["detected_count"] == 0
    # No detected -> coverage defaults to 0 (nothing extracted either).
    assert result["coverage_ratio"] == 0.0
    assert result["gaps"] == []


def test_compute_coverage_chunk_failure_is_soft(monkeypatch) -> None:
    """A single chunk failure must not abort the coverage pass."""
    # Build a source with multiple article markers so the chunker yields
    # >1 chunk under chunk_trigger_chars=10_000.
    src = "\n\n".join(f"Art. {i} — A. " + ("x" * 5_000) for i in range(1, 6))
    call_count = {"n": 0}

    async def flaky_detect(chunk_text: str) -> list[dict[str, Any]]:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated LLM hiccup")
        # Subsequent chunks return one grounded item.
        return [{"label": "x", "excerpt": "Art. 1 — A.", "severity_hint": "info"}]

    monkeypatch.setattr(policy_coverage, "_detect_obligations_chunk", flaky_detect)

    result = asyncio.run(
        policy_coverage.compute_coverage(
            source_text=src,
            extracted_excerpts=[],
            chunk_trigger_chars=10_000,
        )
    )
    assert call_count["n"] >= 2
    # At least one surviving detected obligation is reported.
    assert result["detected_count"] >= 1
