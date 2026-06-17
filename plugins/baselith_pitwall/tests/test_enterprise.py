"""Tests for the enterprise layer: store, session manager, HITL, adapters.

All hermetic — the in-memory store, the simulated/file sources, and the LLM
disabled — so the suite stays fast and needs no external infra.
"""

from __future__ import annotations

import json
from pathlib import Path

from plugins.baselith_pitwall.config import PitwallConfig
from plugins.baselith_pitwall.ingestion import (
    FileReplaySource,
    SimulatedSource,
    TelemetryBus,
    UdpSource,
    WebSocketSource,
    build_source,
)
from plugins.baselith_pitwall.models import (
    Recommendation,
    RecommendationKind,
    StintState,
    TelemetryFrame,
    TyreCompound,
)
from plugins.baselith_pitwall.session_manager import PitwallSessionManager
from plugins.baselith_pitwall.session_models import (
    AckStatus,
    RaceSession,
    SessionCreate,
    SessionStatus,
    TelemetrySourceKind,
)
from plugins.baselith_pitwall.store import (
    InMemoryPitwallStore,
    build_store,
    resolve_persistence,
)


def _frame(**kw) -> TelemetryFrame:
    base = dict(
        car_id="BC44",
        lap=10,
        position=4,
        speed_kph=300.0,
        engine_temp_c=110.0,
        oil_temp_c=100.0,
        fuel_kg=60.0,
        compound=TyreCompound.MEDIUM,
        tyre_age_laps=10,
        tyre_wear=0.4,
        tyre_temp_c=100.0,
        gap_ahead_s=1.5,
    )
    base.update(kw)
    return TelemetryFrame(**base)


def _rec(rec_id: str, car_id: str = "BC44") -> Recommendation:
    return Recommendation(
        id=rec_id,
        car_id=car_id,
        lap=10,
        kind=RecommendationKind.PIT_NOW,
        summary="box",
        rationale="worn",
        confidence=0.8,
    )


# -- store -----------------------------------------------------------------


async def test_memory_store_session_crud() -> None:
    store = InMemoryPitwallStore()
    await store.initialize()
    session = RaceSession(id="s1", tenant_id="t1", name="GP", total_laps=58)
    await store.save_session(session)
    assert (await store.get_session("t1", "s1")).name == "GP"
    assert len(await store.list_sessions("t1")) == 1
    assert await store.list_sessions("t2") == []
    assert await store.delete_session("t1", "s1") is True
    assert await store.get_session("t1", "s1") is None


async def test_memory_store_recommendations_paginated() -> None:
    store = InMemoryPitwallStore()
    for i in range(5):
        await store.save_recommendation("t1", "s1", _rec(f"r{i}"))
    page, total = await store.list_recommendations("t1", "s1", limit=2, offset=0)
    assert total == 5
    assert len(page) == 2
    assert page[0].id == "r4"  # newest first
    got = await store.get_recommendation("t1", "s1", "r2")
    assert got is not None and got.id == "r2"


async def test_memory_store_tenant_isolation() -> None:
    store = InMemoryPitwallStore()
    await store.save_recommendation("t1", "s1", _rec("r1"))
    await store.save_recommendation("t2", "s1", _rec("r2"))
    page_t1, total_t1 = await store.list_recommendations("t1", "s1")
    assert total_t1 == 1 and page_t1[0].id == "r1"


async def test_memory_store_snapshots() -> None:
    store = InMemoryPitwallStore()
    for lap in range(1, 4):
        await store.add_stint_snapshot("t1", "s1", StintState(car_id="BC44", lap=lap))
    snaps = await store.list_stint_snapshots("t1", "s1", "BC44")
    assert [s.lap for s in snaps] == [1, 2, 3]


# -- persistence factory ---------------------------------------------------


def test_resolve_persistence_defaults_memory() -> None:
    assert resolve_persistence(None) == "memory"
    assert resolve_persistence({"persistence": "postgres"}) == "postgres"
    assert resolve_persistence({"persistence": "bogus"}) == "memory"


def test_build_store_memory_default() -> None:
    assert isinstance(build_store({}), InMemoryPitwallStore)


# -- session manager lifecycle --------------------------------------------


def _cfg() -> PitwallConfig:
    return PitwallConfig(use_simulated_source=False, use_llm=False)


async def test_manager_lifecycle_and_audit() -> None:
    store = InMemoryPitwallStore()
    mgr = PitwallSessionManager(_cfg(), store)
    await mgr.initialize()  # no demo session (simulated source off)
    assert await mgr.list_sessions("t1") == []

    session = await mgr.create_session(
        "t1",
        SessionCreate(name="GP", source_kind=TelemetrySourceKind.MANUAL),
        actor="u1",
    )
    assert session.status is SessionStatus.CONFIGURING

    started = await mgr.start_session("t1", session.id, actor="u1")
    assert started is not None and started.status is SessionStatus.LIVE
    assert mgr.get_service("t1", session.id) is not None

    paused = await mgr.pause_session("t1", session.id, actor="u1")
    assert paused.status is SessionStatus.PAUSED
    assert mgr.get_service("t1", session.id) is None

    deleted = await mgr.delete_session("t1", session.id, actor="u1")
    assert deleted is True

    events, _total = await store.list_audit("t1")
    actions = {e.action.value for e in events}
    assert "session_created" in actions
    assert "session_started" in actions
    assert "session_deleted" in actions
    await mgr.shutdown()


async def test_manager_acknowledge_records_hitl() -> None:
    store = InMemoryPitwallStore()
    mgr = PitwallSessionManager(_cfg(), store)
    await mgr.initialize()
    session = await mgr.create_session(
        "t1",
        SessionCreate(name="GP", source_kind=TelemetrySourceKind.MANUAL),
        actor="u1",
    )
    await mgr.start_session("t1", session.id, actor="u1")
    service = mgr.get_service("t1", session.id)
    assert service is not None
    for lap in range(1, 30):
        await service._on_frame(
            _frame(lap=lap, tyre_age_laps=lap, tyre_wear=min(1.0, 0.03 * lap))
        )
    recs = service.recent_recommendations()
    assert recs, "expected at least one emitted recommendation"
    rec_id = recs[0].id

    ack = await mgr.acknowledge(
        "t1", session.id, rec_id, AckStatus.ACCEPTED, actor="strategist"
    )
    assert ack is not None and ack.status is AckStatus.ACCEPTED
    stored = await store.list_acks("t1", session.id)
    assert len(stored) == 1 and stored[0].recommendation_id == rec_id
    # Unknown rec id yields no ack.
    assert (
        await mgr.acknowledge("t1", session.id, "nope", AckStatus.REJECTED, actor="x")
        is None
    )
    await mgr.shutdown()


# -- telemetry adapters ----------------------------------------------------


def test_build_source_maps_kinds() -> None:
    cfg = PitwallConfig(websocket_url="ws://x", replay_path=None)
    assert isinstance(build_source(TelemetrySourceKind.SIMULATED, cfg), SimulatedSource)
    assert isinstance(build_source(TelemetrySourceKind.WEBSOCKET, cfg), WebSocketSource)
    assert isinstance(build_source(TelemetrySourceKind.UDP, cfg), UdpSource)
    assert build_source(TelemetrySourceKind.MANUAL, cfg) is None
    # file replay without a configured path degrades to None.
    assert build_source(TelemetrySourceKind.FILE_REPLAY, cfg) is None


async def test_file_replay_source_feeds_bus(tmp_path: Path) -> None:
    rows = [_frame(lap=lap).model_dump(mode="json") for lap in (1, 2, 3)]
    rec_file = tmp_path / "rec.jsonl"
    rec_file.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    bus = TelemetryBus(maxsize=16)
    src = FileReplaySource(rec_file, tick_seconds=0.0, speed=0.0)
    await src.run(bus.emit)
    assert bus.frames_ingested == 3
    assert bus.frames_rejected == 0
