"""Atomic Red Team YAML loader.

Reads tests from a local checkout of the upstream repository
(``redcanaryco/atomic-red-team``) and produces validated
:class:`AtomicTest` records the orchestrator can reference inside an
:class:`EmulationPlan`. Works against a directory tree of the form

::

    atomics/
      T1059/T1059.yaml
      T1059.001/T1059.001.yaml
      …

The loader is deliberately offline: no git pulls happen here. CI /
ops pipelines are responsible for keeping the local mirror current
(this is the same pattern the SIGMA hint enricher uses for its rule
pack). Fail-loud on malformed YAML so a bad operator-supplied file
never silently degrades the plan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.observability.logging import get_logger
from plugins.red_agent.adversary.plan import AtomicTest, PlanLoadError

logger = get_logger(__name__)


def _coerce_test(raw: dict[str, Any]) -> AtomicTest:
    executor_obj = raw.get("executor") or {}
    if not isinstance(executor_obj, dict):
        raise PlanLoadError("test.executor must be a mapping")

    executor_name = executor_obj.get("name")
    command = executor_obj.get("command")
    if not isinstance(executor_name, str) or not isinstance(command, str):
        raise PlanLoadError("test.executor.name and command are required")

    return AtomicTest(
        name=str(raw.get("name", "")),
        auto_generated_guid=raw.get("auto_generated_guid"),
        description=str(raw.get("description", "")),
        supported_platforms=list(raw.get("supported_platforms") or []),
        executor=executor_name,
        command=command,
        cleanup_command=executor_obj.get("cleanup_command"),
        input_arguments=dict(raw.get("input_arguments") or {}),
        elevation_required=bool(raw.get("elevation_required", False)),
    )


def load_technique(*, atomics_root: Path, technique_id: str) -> list[AtomicTest]:
    """Return every AtomicTest defined for ``technique_id``.

    ``atomics_root`` is the path to the ``atomics`` directory of an
    Atomic Red Team checkout. Missing techniques return an empty
    list — callers should treat that as "we don't have coverage"
    rather than a hard error so a plan can list techniques the user
    might fill in via Caldera or a custom YAML.
    """

    yaml_path = atomics_root / technique_id / f"{technique_id}.yaml"
    if not yaml_path.exists():
        logger.info(
            "red_agent.atomic.technique_missing",
            extra={"technique_id": technique_id, "path": str(yaml_path)},
        )
        return []

    try:
        doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PlanLoadError(f"failed to parse {yaml_path}: {exc}") from exc

    if not isinstance(doc, dict):
        raise PlanLoadError(f"{yaml_path}: top-level YAML must be a mapping")

    tests = doc.get("atomic_tests")
    if not isinstance(tests, list):
        raise PlanLoadError(f"{yaml_path}: missing atomic_tests list")

    out: list[AtomicTest] = []
    for raw in tests:
        if not isinstance(raw, dict):
            continue
        try:
            out.append(_coerce_test(raw))
        except PlanLoadError as exc:
            logger.warning(
                "red_agent.atomic.test_skipped",
                extra={
                    "technique_id": technique_id,
                    "name": raw.get("name"),
                    "err": str(exc),
                },
            )
            continue
    return out


def select_test(
    tests: list[AtomicTest],
    *,
    platform: str,
    guid: str | None = None,
) -> AtomicTest | None:
    """Pick the first test that runs on ``platform``.

    When ``guid`` is supplied it is matched first — operators can pin
    a plan to a specific Atomic Red Team test version regardless of
    upstream re-ordering.
    """

    if guid:
        for t in tests:
            if t.auto_generated_guid == guid:
                return t
        return None
    for t in tests:
        if platform.lower() in (p.lower() for p in t.supported_platforms):
            return t
    return None
