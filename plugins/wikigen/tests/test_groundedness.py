"""Test del groundedness scorer (LLM-as-judge gated)."""

from __future__ import annotations

from llm_wiki.agents import groundedness as g


def test_split_claims_strips_wikilinks_and_fonti_section() -> None:
    answer = (
        "Apertura della risposta.\n\n"
        "Il documento illustra **tre fasi della roadmap**: valutazione, "
        "champion pilot, scaling.\n\n"
        "Le tre fasi sono descritte come progressive e governate da "
        "stakeholder business.\n\n"
        "## Fonti\n"
        "- [[concepts/industry-leaders]]\n"
        "- [[sources/anthropic-whitepaper]]\n"
    )
    claims = g.split_into_claims(answer)
    # Almeno i due claim sostantivi, mai i wikilink della sezione Fonti.
    joined = " ".join(claims)
    assert "tre fasi" in joined
    assert "[[" not in joined


def test_safe_parse_judge_with_clean_json() -> None:
    raw = (
        '{"claims": ['
        '{"text": "claim 1", "supported": true, "note": "ok"},'
        '{"text": "claim 2", "supported": false, "note": "kubectl non presente"}'
        "]}"
    )
    scores = g._safe_parse_judge(raw, ["claim 1", "claim 2"])
    assert len(scores) == 2
    assert scores[0].supported is True
    assert scores[1].supported is False


def test_safe_parse_judge_strips_code_fences() -> None:
    raw = '```json\n{"claims": [{"text": "x", "supported": true, "note": ""}]}\n```'
    scores = g._safe_parse_judge(raw, ["x"])
    assert len(scores) == 1
    assert scores[0].supported is True


def test_safe_parse_judge_fallback_to_unsupported_on_garbage() -> None:
    raw = "This is not JSON at all."
    scores = g._safe_parse_judge(raw, ["claim a", "claim b"])
    # Fallback: tutti marcati unsupported con nota parse_error.
    assert len(scores) == 2
    assert all(not s.supported for s in scores)
    assert all("parse_error" in s.note for s in scores)


def test_repair_feedback_lists_unsupported_only() -> None:
    report = g.GroundednessReport(
        claims=[
            g.ClaimScore("claim ok", supported=True),
            g.ClaimScore("claim cattivo kubectl deploy", supported=False, note="non nel contesto"),
        ],
        supported_ratio=0.5,
        threshold=0.95,
        below_threshold=True,
    )
    feedback = g.repair_feedback(report)
    assert "claim cattivo kubectl deploy" in feedback
    assert "claim ok" not in feedback


def test_repair_feedback_empty_when_all_supported() -> None:
    report = g.GroundednessReport(
        claims=[g.ClaimScore("only", supported=True)],
        supported_ratio=1.0,
        threshold=0.95,
        below_threshold=False,
    )
    assert g.repair_feedback(report) == ""
