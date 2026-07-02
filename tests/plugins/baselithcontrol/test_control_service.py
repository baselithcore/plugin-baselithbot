"""Governed lifecycle engine: validation, autonomy gate, dispatch, config write.

Fakes the registry/controller/config-store seams so the gating + dispatch logic
(the plugin's core advertised feature, previously untested) is pinned without
touching a live plugin registry or disk.
"""

from __future__ import annotations

from typing import Any

import pytest

from core.orchestration.autonomy import AutonomyLevel, AutonomyPolicy
from plugins.baselithcontrol.api_models import PluginState
from plugins.baselithcontrol.service import control as control_mod
from plugins.baselithcontrol.service.audit import InMemoryAuditSink
from plugins.baselithcontrol.service.control import ControlService

OPEN = AutonomyPolicy(level=AutonomyLevel.FULLY_AUTONOMOUS)
SUPERVISED = AutonomyPolicy(level=AutonomyLevel.SUPERVISED)


class _FakeController:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.calls: list[str] = []

    async def enable_plugin(self, name: str, config: Any) -> bool:
        self.calls.append(f"enable:{name}")
        return self.ok

    async def disable_plugin(self, name: str) -> bool:
        self.calls.append(f"disable:{name}")
        return self.ok

    async def reload_plugin(self, name: str, config: Any) -> bool:
        self.calls.append(f"reload:{name}")
        return self.ok


@pytest.fixture(autouse=True)
def _stub_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    # Never touch the event bus / disk in these unit tests.
    async def _noop_emit(**_: Any) -> None:
        return None

    monkeypatch.setattr(control_mod, "emit_action", _noop_emit)
    monkeypatch.setattr(control_mod, "read_block", lambda name: {})


def _svc(registry: Any, *, policy: AutonomyPolicy = OPEN, human: Any = None):
    return ControlService(
        registry, policy=policy, audit=InMemoryAuditSink(50), human_intervention=human
    )


async def test_unsupported_op_is_rejected() -> None:
    res = await _svc({"p": 1}).run(plugin="p", op="frobnicate", actor="a", reason=None)
    assert res.ok is False and res.state == PluginState.unknown
    assert "Unsupported" in res.message


async def test_unknown_plugin_not_found() -> None:
    res = await _svc({}).run(plugin="ghost", op="enable", actor="a", reason=None)
    assert res.ok is False and res.state == PluginState.unknown
    assert "not registered" in res.message


async def test_enable_dispatches_through_controller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctrl = _FakeController(ok=True)
    monkeypatch.setattr(ControlService, "_controller", staticmethod(lambda: ctrl))
    svc = _svc({"p": 1})
    res = await svc.run(plugin="p", op="enable", actor="admin", reason="why")
    assert res.ok is True and res.state == PluginState.active
    assert ctrl.calls == ["enable:p"]
    # The attempt is audited.
    tail = svc._audit.tail()
    assert tail[-1].plugin == "p" and tail[-1].ok is True


async def test_disable_failure_reports_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    ctrl = _FakeController(ok=False)
    monkeypatch.setattr(ControlService, "_controller", staticmethod(lambda: ctrl))
    res = await _svc({"p": 1}).run(plugin="p", op="disable", actor="a", reason=None)
    assert res.ok is False and res.state == PluginState.active
    assert "failed" in res.message


async def test_autonomy_denied_without_human_channel() -> None:
    # SUPERVISED requires approval for MUTATING/DESTRUCTIVE and no human channel
    # is wired → fail closed, audited as denied, never dispatched.
    svc = _svc({"p": 1}, policy=SUPERVISED, human=None)
    res = await svc.run(plugin="p", op="disable", actor="a", reason=None)
    assert res.ok is False and "denied" in res.message
    assert svc._audit.tail()[-1].ok is False


async def test_localized_message_it() -> None:
    res = await _svc({}).run(
        plugin="ghost", op="enable", actor="a", reason=None, locale="it"
    )
    assert "non è registrato" in res.message


async def test_set_config_not_found_when_absent_everywhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(control_mod, "read_manifest", lambda name: None)
    res = await _svc({}).set_config_enabled(
        plugin="ghost", enabled=True, actor="a", reason=None
    )
    assert res.ok is False and "not registered" in res.message


async def test_set_config_write_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(control_mod, "read_manifest", lambda name: {"name": "p"})
    monkeypatch.setattr(control_mod, "set_enabled", lambda name, enabled: False)
    res = await _svc({"p": 1}).set_config_enabled(
        plugin="p", enabled=False, actor="a", reason=None
    )
    assert res.ok is False and res.state == PluginState.unknown


async def test_set_config_success_persists_and_syncs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctrl = _FakeController(ok=True)
    monkeypatch.setattr(ControlService, "_controller", staticmethod(lambda: ctrl))
    monkeypatch.setattr(control_mod, "read_manifest", lambda name: {"name": "p"})
    writes: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        control_mod,
        "set_enabled",
        lambda name, enabled: (writes.append((name, enabled)), True)[1],
    )
    res = await _svc({"p": 1}).set_config_enabled(
        plugin="p", enabled=True, actor="admin", reason="turn on"
    )
    assert res.ok is True and writes == [("p", True)]
    assert ctrl.calls == ["enable:p"]  # runtime sync ran after the durable write
