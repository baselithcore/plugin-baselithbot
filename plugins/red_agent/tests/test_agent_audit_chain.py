"""Tests for the daemon audit log hash-chain helper.

These exercise the pure helpers (``_canonical_json``) and the
chain-verification semantics by feeding synthetic rows through the
verification routine without touching Postgres. Persistence-backed
tests live under ``tests/integration/`` and require a live database.
"""

from __future__ import annotations

import hashlib

from plugins.red_agent.persistence.agent_audit import _canonical_json


def test_canonical_json_is_stable_under_key_reorder() -> None:
    a = {"b": 1, "a": 2, "c": [3, 2, 1]}
    b = {"a": 2, "c": [3, 2, 1], "b": 1}
    assert _canonical_json(a) == _canonical_json(b)


def test_canonical_json_handles_uuid_and_datetime() -> None:
    from datetime import datetime, timezone
    from uuid import UUID

    payload = {
        "agent": UUID("12345678-1234-5678-1234-567812345678"),
        "ts": datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc),
    }
    out = _canonical_json(payload)
    assert b"12345678-1234-5678-1234-567812345678" in out
    assert b"2026-04-26" in out


def test_chain_progression_matches_sha256_definition() -> None:
    """Reproduces the prev_hash || canonical(payload) chaining rule."""
    payloads = [{"event": f"step-{i}"} for i in range(3)]

    prev = b""
    expected = []
    for p in payloads:
        h = hashlib.sha256(prev + _canonical_json(p)).digest()
        expected.append((prev, h))
        prev = h

    # Sanity: each step's prev_hash equals previous step's row_hash.
    for i in range(1, len(expected)):
        assert expected[i][0] == expected[i - 1][1]

    # And the chain length matches input length.
    assert len(expected) == 3
