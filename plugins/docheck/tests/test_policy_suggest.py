"""Tests for `services.policy_suggest` (ADR-0015).

Unit-level: the LLM and DB calls are monkeypatched so we exercise the
filtering/grounding logic in isolation. No end-to-end integration test
here — that is covered by the API smoke test below.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import HTTPException

from docheck.services import policy_ingest, policy_suggest

SRC = (
    "Art. 1 — Il fornitore deve consegnare entro 30 giorni dalla stipula. "
    "Art. 2 — Il pagamento avviene entro 60 giorni dalla fattura. "
    "Art. 3 — Non è ammessa la subappaltazione senza autorizzazione."
)


def _make_db_with_rules(rules: list[dict[str, Any]]):
    """Build a stand-in DB that `list_rules` will return our rules from."""

    class _DB:
        pass

    async def fake_list_rules(db, pid, version):
        return rules

    return _DB(), fake_list_rules


def test_suggest_filters_existing_excerpts(monkeypatch) -> None:
    db, fake_list_rules = _make_db_with_rules(
        [
            {"excerpt": "Il fornitore deve consegnare entro 30 giorni dalla stipula."},
        ]
    )
    from docheck.services import policies as policy_svc

    monkeypatch.setattr(policy_svc, "list_rules", fake_list_rules)

    async def fake_extract(text, hint_title=None):
        return {
            "rules": [
                # Already in policy -> filtered.
                {
                    "rule_type": "semantic",
                    "severity": "warn",
                    "excerpt": "Il fornitore deve consegnare entro 30 giorni dalla stipula.",
                },
                # New -> kept.
                {
                    "rule_type": "semantic",
                    "severity": "warn",
                    "excerpt": "Il pagamento avviene entro 60 giorni dalla fattura.",
                },
                # New -> kept.
                {
                    "rule_type": "absence",
                    "severity": "fail",
                    "excerpt": "Non è ammessa la subappaltazione senza autorizzazione.",
                },
                # Hallucinated (not in source) -> dropped by grounding.
                {
                    "rule_type": "semantic",
                    "severity": "warn",
                    "excerpt": "Obbligo inesistente nel sorgente di test.",
                },
            ]
        }

    monkeypatch.setattr(policy_ingest, "_llm_extract", fake_extract)

    suggestions = asyncio.run(
        policy_suggest.suggest_more(db, pid="p", version="1.0.0", source_text=SRC)
    )

    excerpts = {s["excerpt"] for s in suggestions}
    assert excerpts == {
        "Il pagamento avviene entro 60 giorni dalla fattura.",
        "Non è ammessa la subappaltazione senza autorizzazione.",
    }


def test_suggest_empty_source_raises() -> None:
    class _DB:
        pass

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            policy_suggest.suggest_more(
                _DB(), pid="p", version="1.0.0", source_text="   "
            )
        )
    assert exc.value.status_code == 400


def test_suggest_caps_at_max(monkeypatch) -> None:
    # 50 distinct grounded suggestions in source; service must cap at MAX_SUGGESTIONS.
    sentences = [
        f"Obbligo distinto numero {i} da rispettare entro tempi certi."
        for i in range(50)
    ]
    src = " ".join(sentences)

    db, fake_list_rules = _make_db_with_rules([])
    from docheck.services import policies as policy_svc

    monkeypatch.setattr(policy_svc, "list_rules", fake_list_rules)

    async def fake_extract(text, hint_title=None):
        return {
            "rules": [
                {"rule_type": "semantic", "severity": "warn", "excerpt": s}
                for s in sentences
            ]
        }

    monkeypatch.setattr(policy_ingest, "_llm_extract", fake_extract)

    suggestions = asyncio.run(
        policy_suggest.suggest_more(db, pid="p", version="1.0.0", source_text=src)
    )
    assert len(suggestions) == policy_suggest.MAX_SUGGESTIONS
