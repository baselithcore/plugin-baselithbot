"""Planner + multi-step chain tests."""

from __future__ import annotations

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.planner import (
    ChainingPlanner,
    DeterministicPlanner,
    PlannerState,
)


def _state(scanners: list[str]) -> PlannerState:
    return PlannerState(
        initial_target=Target(type=TargetType.URL, value="http://example.com"),
        intensity=ScanIntensity.PASSIVE,
        requested_scanners=scanners,
    )


async def test_deterministic_runs_once_then_stops() -> None:
    p = DeterministicPlanner()
    s = _state(["nmap", "nuclei"])
    step = await p.plan(s, [])
    assert step is not None
    assert step.scanners == ["nmap", "nuclei"]
    s.iterations = 1
    assert await p.plan(s, []) is None


async def test_chaining_planner_iter0_runs_full_requested_set() -> None:
    p = ChainingPlanner(max_iterations=3)
    s = _state(["nmap", "nuclei", "zap"])
    step = await p.plan(s, [])
    assert step is not None
    assert step.scanners == ["nmap", "nuclei", "zap"]
    assert step.target.value == "http://example.com"


async def test_chaining_planner_iter1_runs_dast_on_new_endpoints() -> None:
    p = ChainingPlanner(max_iterations=3)
    s = _state(["nmap", "nuclei", "zap"])
    s.iterations = 1
    new = [
        Finding(
            scanner="nmap",
            title="open 80",
            description="d",
            severity=Severity.INFO,
            target="example.com",
            endpoint="http://example.com:80/",
        )
    ]
    step = await p.plan(s, new)
    assert step is not None
    assert step.target.value == "http://example.com:80/"
    assert "nuclei" in step.scanners


async def test_chaining_planner_stops_at_max_iterations() -> None:
    p = ChainingPlanner(max_iterations=2)
    s = _state(["nmap"])
    s.iterations = 2
    assert await p.plan(s, []) is None


async def test_chaining_planner_no_new_endpoints_stops() -> None:
    p = ChainingPlanner(max_iterations=3)
    s = _state(["nmap", "nuclei"])
    s.iterations = 1
    assert await p.plan(s, []) is None


async def test_chaining_planner_skips_already_seen_endpoints() -> None:
    p = ChainingPlanner(max_iterations=3)
    s = _state(["nmap", "nuclei"])
    s.iterations = 1
    s.seen_endpoints.add("http://example.com:80/")
    new = [
        Finding(
            scanner="nmap",
            title="x",
            description="d",
            severity=Severity.INFO,
            target="example.com",
            endpoint="http://example.com:80/",
        )
    ]
    assert await p.plan(s, new) is None
