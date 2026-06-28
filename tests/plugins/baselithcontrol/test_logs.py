"""Unit tests for the in-memory log ring handler (no real logging config)."""

from __future__ import annotations

import logging

from plugins.baselithcontrol.service.logs import LogRingHandler, plugin_of


def _record(name: str, level: int, msg: str) -> logging.LogRecord:
    return logging.LogRecord(name, level, __file__, 1, msg, None, None)


def test_plugin_of_attribution() -> None:
    assert plugin_of("plugins.auth.routes") == "auth"
    assert plugin_of("plugins.baselithcontrol") == "baselithcontrol"
    assert plugin_of("core.api.factory") == "core"
    assert plugin_of("uvicorn.access") == "uvicorn"
    assert plugin_of("") == "root"


def test_ring_captures_and_orders_newest_first() -> None:
    h = LogRingHandler(capacity=100)
    h.emit(_record("plugins.a.x", logging.INFO, "first"))
    h.emit(_record("plugins.b.y", logging.ERROR, "second"))
    tail = h.tail(limit=10)
    assert [e["message"] for e in tail] == ["second", "first"]
    assert tail[0]["plugin"] == "b" and tail[0]["level"] == "ERROR"
    assert all("seq" in e for e in tail) and tail[0]["seq"] > tail[1]["seq"]


def test_capacity_bounds_the_ring() -> None:
    h = LogRingHandler(capacity=2)
    for i in range(5):
        h.emit(_record("core.x", logging.INFO, f"m{i}"))
    msgs = [e["message"] for e in h.tail(limit=10)]
    assert msgs == ["m4", "m3"]  # only the last 2 retained, newest first


def test_min_level_filter() -> None:
    h = LogRingHandler(capacity=50)
    h.emit(_record("core.x", logging.DEBUG, "dbg"))
    h.emit(_record("core.x", logging.INFO, "inf"))
    h.emit(_record("core.x", logging.ERROR, "err"))
    assert [e["message"] for e in h.tail(level="WARNING")] == ["err"]
    assert {e["message"] for e in h.tail(level="INFO")} == {"inf", "err"}


def test_plugin_and_query_filters() -> None:
    h = LogRingHandler(capacity=50)
    h.emit(_record("plugins.auth.a", logging.INFO, "token minted"))
    h.emit(_record("plugins.news.b", logging.INFO, "feed fetched"))
    assert [e["message"] for e in h.tail(plugin="auth")] == ["token minted"]
    assert [e["message"] for e in h.tail(query="FEED")] == ["feed fetched"]
    # query also matches the logger name
    assert [e["plugin"] for e in h.tail(query="auth")] == ["auth"]


def test_long_message_truncated() -> None:
    h = LogRingHandler(capacity=10)
    h.emit(_record("core.x", logging.INFO, "z" * 5000))
    msg = h.tail(limit=1)[0]["message"]
    assert len(msg) <= 2001 and msg.endswith("…")


def test_known_plugins_distinct_sorted() -> None:
    h = LogRingHandler(capacity=50)
    for name in ("plugins.b.x", "plugins.a.y", "core.z", "plugins.b.w"):
        h.emit(_record(name, logging.INFO, "m"))
    assert h.known_plugins() == ["a", "b", "core"]
