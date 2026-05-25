"""Tests for AuditRetentionTask lifecycle (start / stop / loop iteration)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from plugins.red_agent import tasks as tasks_mod
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.tasks import AuditRetentionTask


@pytest.mark.asyncio
async def test_start_then_stop_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int]] = []

    async def fake_delete(dsn: str, retention_days: int) -> int:
        calls.append((dsn, retention_days))
        return 7

    monkeypatch.setattr(tasks_mod, "_delete_expired_audit", fake_delete)

    cfg = RedAgentConfig(audit_retention_days=30)
    task = AuditRetentionTask(dsn="postgresql://x", config=cfg, interval_seconds=10)
    task.start()
    # Let the first sweep run.
    await asyncio.sleep(0.05)
    await task.stop()
    assert calls and calls[0] == ("postgresql://x", 30)


@pytest.mark.asyncio
async def test_loop_survives_sweep_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    async def boom(_dsn: str, _days: int) -> int:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("fake postgres failure")

    monkeypatch.setattr(tasks_mod, "_delete_expired_audit", boom)

    cfg = RedAgentConfig(audit_retention_days=30)
    task = AuditRetentionTask(dsn="postgresql://x", config=cfg, interval_seconds=10)
    task.start()
    await asyncio.sleep(0.05)
    await task.stop()
    # Sweep failed but loop did not crash; at least one attempt observed.
    assert attempts >= 1


@pytest.mark.asyncio
async def test_stop_without_start_is_safe() -> None:
    cfg = RedAgentConfig(audit_retention_days=30)
    task = AuditRetentionTask(dsn="postgresql://x", config=cfg, interval_seconds=10)
    # Should not raise.
    await task.stop()


def test_internal_state_initialized() -> None:
    cfg = RedAgentConfig(audit_retention_days=30)
    task = AuditRetentionTask(dsn="postgresql://x", config=cfg, interval_seconds=42)
    assert task.interval_seconds == 42
    assert task.config.audit_retention_days == 30


def _quiet(_args: Any) -> None:
    """Pyright happiness — no behavior."""
    return None
