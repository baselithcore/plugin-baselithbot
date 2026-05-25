"""End-to-end agent pipeline test against mock LLM (in-process patch)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from docheck.agents import legal, pii, structurer, synthesizer, technical
from docheck.schemas.state import CheckState, Chunk

SAMPLE_TEXT = (
    "Art. 1 — Scopo del contratto.\n"
    "I dati saranno trattati per finalità contrattuali.\n"
    "La scadenza del trattamento è da definire.\n"
)


def _chunk() -> Chunk:
    return Chunk(
        id="c-test",
        text=SAMPLE_TEXT,
        page=1,
        line_start=1,
        line_end=3,
        bbox=(0.0, 0.0, 100.0, 100.0),
        token_count=len(SAMPLE_TEXT.split()),
    )


@pytest.fixture
def state() -> CheckState:
    return {
        "doc_id": "doc-test",
        "lang": "it",
        "chunks": [_chunk()],
        "structure": [],
        "selected_policies": ["IT_GDPR_2026"],
        "findings": [],
        "trace": [],
        "errors": [],
    }


async def test_structurer_handles_llm_failure_gracefully(state: CheckState) -> None:
    with patch(
        "docheck.agents.structurer.chat_json_resilient",
        side_effect=RuntimeError("offline"),
    ):
        out = await structurer.run(state)
    assert out.get("structure") == []


async def test_technical_agent_flags_missing_iso_date(state: CheckState) -> None:
    out = await technical.run(state)
    findings = out.get("findings", [])
    assert any(f.rule_id == "FORMAT-DATE-ISO" for f in findings)


async def test_pii_agent_skips_when_no_candidates() -> None:
    s: CheckState = {
        "doc_id": "d",
        "lang": "it",
        "chunks": [
            Chunk(
                id="c1",
                text="Lorem ipsum",
                page=1,
                line_start=1,
                line_end=1,
                bbox=(0, 0, 0, 0),
                token_count=2,
            )
        ],
        "structure": [],
        "selected_policies": [],
        "findings": [],
        "trace": [],
        "errors": [],
    }
    out = await pii.run(s)
    assert out.get("findings") == []


async def test_synthesizer_dedupes_and_scores(state: CheckState) -> None:
    tech_out = await technical.run(state)
    # Simulate parallel concat: findings list has duplicates
    state["findings"] = list(tech_out["findings"]) + list(tech_out["findings"])
    out = await synthesizer.run(state)
    rule_ids = [f.rule_id for f in out.get("final_findings", [])]
    assert len(rule_ids) == len(set(rule_ids))
    assert "score" in out
    assert 0 <= out["score"] <= 100


async def test_legal_agent_validates_finding_schema(state: CheckState) -> None:
    excerpt = "Il titolare informa l'interessato del periodo di conservazione."
    candidate = {
        "rule_id": "GDPR-Art-13",
        "policy_id": "IT_GDPR_2026",
        "version": "3.0.0",
        "title": "Informativa retention",
        "scope": "eu",
        "severity_default": "fail",
        "rule_type": "presence",
        "excerpt": excerpt,
        "score": 0.1,
    }
    canned = {
        "findings": [
            {
                "rule_id": "GDPR-Art-13",
                "policy_id": "IT_GDPR_2026",
                "policy_version": "3.0.0",
                "severity": "FAIL",
                "chunk_id": "c-test",
                "line_start": 1,
                "line_end": 3,
                "policy_excerpt": excerpt,
                "explanation": "Manca retention",
                "suggestion": "Aggiungere clausola.",
                "confidence": 0.9,
                "reasoning": [],
            }
        ]
    }
    with (
        patch("docheck.agents.legal.retrieve_policy", return_value=[candidate]),
        patch("docheck.agents.legal.chat_json_resilient", return_value=canned),
    ):
        out = await legal.run(state)
    findings = out.get("findings", [])
    assert len(findings) == 1
    assert findings[0].evidence.chunk_id == "c-test"
    assert findings[0].policy_ref.excerpt
