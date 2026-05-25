"""Adversary-emulation unit tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from plugins.red_agent.adversary.atomic_loader import (
    load_technique,
    select_test,
)
from plugins.red_agent.adversary.caldera_client import (
    CalderaClient,
    CalderaClientError,
)
from plugins.red_agent.adversary.plan import (
    AtomicTest,
    EmulationPlan,
    EmulationStep,
    PlanLoadError,
)
from plugins.red_agent.adversary.result import (
    EmulationOutcome,
    EmulationResult,
    EmulationRunSummary,
)
from plugins.red_agent.adversary.result_to_findings import to_finding
from plugins.red_agent.models import Severity


# --- plan ---


def _atomic() -> AtomicTest:
    return AtomicTest(
        name="t",
        executor="bash",
        command="echo hi",
        supported_platforms=["linux"],
    )


def test_plan_techniques_dedups_preserving_order() -> None:
    plan = EmulationPlan(
        name="p",
        authored_by="a",
        steps=[
            EmulationStep(technique_id="T1059.001", test=_atomic()),
            EmulationStep(technique_id="T1003", test=_atomic()),
            EmulationStep(technique_id="T1059.001", test=_atomic()),
        ],
    )
    assert plan.techniques() == ["T1059.001", "T1003"]


def test_plan_dual_control_requires_distinct_reviewer() -> None:
    p = EmulationPlan(name="p", authored_by="a")
    assert p.is_dual_controlled() is False
    p2 = EmulationPlan(name="p", authored_by="a", reviewed_by="a")
    assert p2.is_dual_controlled() is False
    p3 = EmulationPlan(name="p", authored_by="a", reviewed_by="b")
    assert p3.is_dual_controlled() is True


# --- atomic_loader ---


def _write_atomic_yaml(root: Path, technique_id: str, body: str) -> None:
    technique_dir = root / technique_id
    technique_dir.mkdir(parents=True, exist_ok=True)
    (technique_dir / f"{technique_id}.yaml").write_text(body, encoding="utf-8")


def test_load_technique_returns_empty_when_missing(tmp_path: Path) -> None:
    assert load_technique(atomics_root=tmp_path, technique_id="T9999") == []


def test_load_technique_parses_yaml(tmp_path: Path) -> None:
    body = """
attack_technique: T1059.001
display_name: PowerShell
atomic_tests:
  - name: Run-WhoAmI
    auto_generated_guid: aaaa-1111
    description: Whoami
    supported_platforms:
      - windows
    executor:
      name: powershell
      command: whoami
      cleanup_command: echo cleanup
    input_arguments:
      target:
        description: t
        type: String
        default: "x"
    elevation_required: false
"""
    _write_atomic_yaml(tmp_path, "T1059.001", body)

    tests = load_technique(atomics_root=tmp_path, technique_id="T1059.001")

    assert len(tests) == 1
    assert tests[0].name == "Run-WhoAmI"
    assert tests[0].executor == "powershell"
    assert tests[0].command == "whoami"
    assert tests[0].cleanup_command == "echo cleanup"


def test_load_technique_raises_on_invalid_yaml(tmp_path: Path) -> None:
    _write_atomic_yaml(tmp_path, "T1", "not: [yaml: broken")
    with pytest.raises(PlanLoadError):
        load_technique(atomics_root=tmp_path, technique_id="T1")


def test_load_technique_raises_when_top_level_not_mapping(tmp_path: Path) -> None:
    _write_atomic_yaml(tmp_path, "T2", "- just\n- a\n- list\n")
    with pytest.raises(PlanLoadError):
        load_technique(atomics_root=tmp_path, technique_id="T2")


def test_select_test_picks_by_platform() -> None:
    tests = [
        AtomicTest(
            name="win",
            executor="powershell",
            command="x",
            supported_platforms=["windows"],
        ),
        AtomicTest(
            name="linux", executor="bash", command="x", supported_platforms=["linux"]
        ),
    ]
    assert select_test(tests, platform="linux").name == "linux"  # type: ignore[union-attr]
    assert select_test(tests, platform="darwin") is None


def test_select_test_pinned_by_guid() -> None:
    tests = [
        AtomicTest(
            name="a",
            executor="bash",
            command="x",
            supported_platforms=["linux"],
            auto_generated_guid="g1",
        ),
        AtomicTest(
            name="b",
            executor="bash",
            command="x",
            supported_platforms=["linux"],
            auto_generated_guid="g2",
        ),
    ]
    assert select_test(tests, platform="linux", guid="g2").name == "b"  # type: ignore[union-attr]
    assert select_test(tests, platform="linux", guid="missing") is None


# --- result -> finding ---


def _result(outcome: EmulationOutcome) -> EmulationResult:
    return EmulationResult(
        plan_id=uuid4(),
        step_index=0,
        technique_id="T1059.001",
        agent_id="agent-1",
        outcome=outcome,
    )


def test_to_finding_executed_is_high_severity() -> None:
    f = to_finding(_result(EmulationOutcome.EXECUTED))
    assert f is not None
    assert f.severity == Severity.HIGH
    assert f.scanner == "adversary_emulation"
    assert "T1059.001" in f.title


def test_to_finding_blocked_is_info() -> None:
    f = to_finding(_result(EmulationOutcome.BLOCKED))
    assert f is not None and f.severity == Severity.INFO


def test_to_finding_skipped_returns_none() -> None:
    assert to_finding(_result(EmulationOutcome.SKIPPED)) is None
    assert to_finding(_result(EmulationOutcome.PRECONDITION_FAILED)) is None


def test_run_summary_counts_and_buckets() -> None:
    summary = EmulationRunSummary(plan_id=uuid4())
    summary.add(_result(EmulationOutcome.EXECUTED))
    summary.add(_result(EmulationOutcome.EXECUTED))
    summary.add(_result(EmulationOutcome.BLOCKED))

    assert summary.counts == {"executed": 2, "blocked": 1}
    assert summary.techniques_blocked() == ["T1059.001"]
    assert summary.techniques_unblocked() == ["T1059.001"]


# --- caldera client ---


class _FakeResponse:
    def __init__(self, *, status_code: int, body: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._body = body
        self.text = text

    @property
    def content(self) -> bytes:
        return b"x" if self._body is not None else b""

    def json(self) -> Any:
        return self._body


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> _FakeResponse:
        self.calls.append((method, url, json))
        return self._response


@pytest.mark.asyncio
async def test_caldera_submit_operation_posts_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _FakeResponse(status_code=200, body={"id": "op-1"})
    fake_client = _FakeClient(response)
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: fake_client)

    client = CalderaClient(base_url="https://caldera/", api_key="k")
    out = await client.submit_operation(name="op", adversary_id="adv-1", group="g")

    assert out == {"id": "op-1"}
    method, url, body = fake_client.calls[0]
    assert method == "POST"
    assert url == "https://caldera/api/v2/operations"
    assert body and body["adversary"] == {"adversary_id": "adv-1"}


@pytest.mark.asyncio
async def test_caldera_raises_on_non_2xx(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _FakeResponse(status_code=403, body=None, text="forbidden")
    fake_client = _FakeClient(response)
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: fake_client)

    client = CalderaClient(base_url="https://c", api_key="k")
    with pytest.raises(CalderaClientError) as exc:
        await client.get_operation("op-1")
    assert "403" in str(exc.value)


@pytest.mark.asyncio
async def test_caldera_list_links_returns_only_dicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _FakeResponse(
        status_code=200,
        body=[{"id": "l1"}, "junk", {"id": "l2"}],
    )
    fake_client = _FakeClient(response)
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: fake_client)

    client = CalderaClient(base_url="https://c", api_key="k")
    out = await client.list_links("op-1")

    assert [r["id"] for r in out] == ["l1", "l2"]
