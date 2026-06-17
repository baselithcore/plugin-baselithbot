"""Smoke tests validating the digital-twin vertical and OpenWA integration.

Drives the whole ingest → learn → draft → govern → deliver path against the
in-memory store and the fake gateway, plus the pure cognition units (style
extraction, salient-fact mining, autonomy policy, LTM retrieval) and the i18n
layer. No external infra, no LLM, no network — everything runs deterministically.

``asyncio_mode = auto`` (pytest.ini) lets the ``async def`` tests run directly.
"""

from __future__ import annotations

import pytest

from plugins.baselithtwin.config import (
    AutonomyMode,
    GatewayKind,
    PersistenceKind,
    TwinConfig,
)
from plugins.baselithtwin.gateway import FakeGateway
from plugins.baselithtwin.gateway.models import InboundMessage
from plugins.baselithtwin.i18n import negotiate_locale, translate
from plugins.baselithtwin.memory import LTMIndex, extract_facts
from plugins.baselithtwin.models import (
    DraftReply,
    ReplyStatus,
    SalientFact,
    WhitelistEntry,
)
from plugins.baselithtwin.policy import Decision, decide
from plugins.baselithtwin.service import TwinService
from plugins.baselithtwin.style import extract_style


# -- Fixtures ----------------------------------------------------------------


def _owner_msgs() -> list[InboundMessage]:
    texts = [
        "ciao raga, tutto a posto?",
        "ahah si dai, ci sentiamo dopo 😄",
        "grazie mille, sei un grande 🙏",
        "domani sono libero, organizziamo!",
        "perfetto, a che ora ci vediamo?",
    ]
    return [
        InboundMessage(id=f"o{i}", contact_id="c1@c.us", text=t, from_me=True)
        for i, t in enumerate(texts)
    ]


async def _service(**overrides) -> TwinService:
    # Hermetic by construction: explicit backends override any ambient ``.env``
    # (e.g. a developer's local ``BASELITH_TWIN_GATEWAY=openwa``) so the suite
    # never touches the network — honouring the module's no-infra contract.
    params: dict = {
        "owner_name": "Gio",
        "gateway": GatewayKind.FAKE,
        "persistence": PersistenceKind.MEMORY,
        "require_webhook_secret": False,
    }
    params.update(overrides)
    svc = TwinService(TwinConfig(**params))
    await svc.initialize()
    return svc


# -- Style extraction --------------------------------------------------------


def test_style_extraction_learns_metrics_and_locale() -> None:
    profile = extract_style("gio", _owner_msgs())
    assert profile.trained is True
    assert profile.sample_size == 5
    assert profile.metrics.dominant_locale == "it"
    assert profile.metrics.emoji_rate > 0
    assert profile.exemplars  # exemplars captured for few-shot priming


def test_style_extraction_empty_history_is_untrained() -> None:
    profile = extract_style("gio", [])
    assert profile.trained is False
    assert profile.sample_size == 0


# -- Salient-fact mining + LTM retrieval -------------------------------------


def test_extract_facts_picks_durable_statements() -> None:
    msg = InboundMessage(
        id="m1", contact_id="c2@c.us", text="I live in Milan and I work in tech"
    )
    facts = extract_facts(msg)
    assert len(facts) == 1
    assert facts[0].contact_id == "c2@c.us"
    assert facts[0].salience >= 0.5


def test_extract_facts_ignores_smalltalk() -> None:
    msg = InboundMessage(id="m2", contact_id="c2@c.us", text="ok 👍")
    assert extract_facts(msg) == []


async def test_ltm_retrieval_ranks_relevant_facts() -> None:
    facts = [
        SalientFact(id="f1", contact_id="c", text="my flight is on Friday morning"),
        SalientFact(id="f2", contact_id="c", text="I love hiking in the mountains"),
    ]
    top = await LTMIndex().relevant("when is your flight?", facts, top_k=1)
    assert len(top) == 1
    assert top[0].id == "f1"


# -- Autonomy policy ---------------------------------------------------------


def test_policy_suggest_always_queues() -> None:
    out = decide(
        AutonomyMode.SUGGEST, is_whitelisted=True, rate_ok=True, confidence=0.9
    )
    assert out is Decision.QUEUE


def test_policy_whitelist_auto_sends_only_whitelisted() -> None:
    assert (
        decide(
            AutonomyMode.WHITELIST, is_whitelisted=True, rate_ok=True, confidence=0.9
        )
        is Decision.AUTO_SEND
    )
    assert (
        decide(
            AutonomyMode.WHITELIST, is_whitelisted=False, rate_ok=True, confidence=0.9
        )
        is Decision.QUEUE
    )


def test_policy_low_confidence_never_auto_sends() -> None:
    out = decide(AutonomyMode.FULL, is_whitelisted=True, rate_ok=True, confidence=0.1)
    assert out is Decision.QUEUE


def test_policy_rate_limit_downgrades_to_queue() -> None:
    out = decide(AutonomyMode.FULL, is_whitelisted=True, rate_ok=False, confidence=0.9)
    assert out is Decision.QUEUE


# -- End-to-end ingest -------------------------------------------------------


async def test_owner_message_is_learned_not_replied() -> None:
    svc = await _service()
    result = await svc.ingest(_owner_msgs()[0])
    assert result is None  # never reply to the owner's own message
    profile = await svc.train_style()
    assert profile.trained is True


async def test_non_whitelisted_contact_is_queued() -> None:
    svc = await _service(autonomy=AutonomyMode.WHITELIST)
    pending = await svc.ingest(
        InboundMessage(id="m1", contact_id="c9@c.us", text="ci sei?")
    )
    assert pending is not None
    assert pending.status is ReplyStatus.QUEUED
    queued = await svc.list_pending(only_queued=True)
    assert len(queued) == 1


async def test_whitelisted_high_confidence_auto_sends(monkeypatch) -> None:
    svc = await _service(autonomy=AutonomyMode.WHITELIST)
    await svc.add_to_whitelist(WhitelistEntry(contact_id="c2@c.us"))

    async def _high_conf_draft(message, *_a, **_k) -> DraftReply:
        return DraftReply(
            contact_id=message.contact_id,
            in_reply_to=message.id,
            text="Certo, ci sono!",
            confidence=0.8,
            style_applied=True,
        )

    monkeypatch.setattr(svc._engine, "draft", _high_conf_draft)
    pending = await svc.ingest(
        InboundMessage(id="m2", contact_id="c2@c.us", text="allora?")
    )
    assert pending is not None
    assert pending.status is ReplyStatus.AUTO_SENT
    gateway: FakeGateway = svc._gateway  # type: ignore[assignment]
    assert len(gateway.sent) == 1
    assert gateway.sent[0].text == "Certo, ci sono!"


async def test_approve_sends_queued_reply() -> None:
    svc = await _service(autonomy=AutonomyMode.SUGGEST)
    pending = await svc.ingest(
        InboundMessage(id="m3", contact_id="c3@c.us", text="ping")
    )
    assert pending is not None and pending.status is ReplyStatus.QUEUED
    decided = await svc.approve(pending.id, actor="operator")
    assert decided is not None
    assert decided.status is ReplyStatus.APPROVED
    gateway: FakeGateway = svc._gateway  # type: ignore[assignment]
    assert len(gateway.sent) == 1


async def test_reject_never_sends() -> None:
    svc = await _service(autonomy=AutonomyMode.SUGGEST)
    pending = await svc.ingest(
        InboundMessage(id="m4", contact_id="c4@c.us", text="ping")
    )
    assert pending is not None
    decided = await svc.reject(pending.id, actor="operator")
    assert decided is not None and decided.status is ReplyStatus.REJECTED
    gateway: FakeGateway = svc._gateway  # type: ignore[assignment]
    assert gateway.sent == []


async def test_status_reflects_state() -> None:
    svc = await _service()
    await svc.add_to_whitelist(WhitelistEntry(contact_id="c5@c.us"))
    status = await svc.status("0.1.0")
    assert status.owner_name == "Gio"
    assert status.whitelist_size == 1
    assert status.gateway_connected is True


# -- i18n --------------------------------------------------------------------


def test_i18n_negotiates_and_translates() -> None:
    assert negotiate_locale("it-IT,it;q=0.9,en;q=0.8") == "it"
    assert negotiate_locale("fr-FR") == "en"  # unsupported → default
    assert translate("twin.health.ok", "it") == "Il gemello digitale è online."
    assert "online" in translate("twin.health.ok", "en").lower()


def test_i18n_interpolates_params() -> None:
    msg = translate("twin.contact.allowed", "en", contact="bob@c.us")
    assert "bob@c.us" in msg


@pytest.mark.parametrize("locale", ["en", "it"])
def test_i18n_catalogs_in_sync(locale: str) -> None:
    from plugins.baselithtwin.i18n import _load_catalog

    en_keys = set(_load_catalog("en"))
    other = set(_load_catalog(locale))
    assert en_keys == other, f"{locale} catalog out of sync with en"
