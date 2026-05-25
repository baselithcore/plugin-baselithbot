"""Baseline persistence + regression gate (ADR-0016)."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Baseline, EvalResult, GateOutcome


def load_baseline(path: Path) -> Baseline:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Baseline.model_validate(data)


def save_baseline(path: Path, baseline: Baseline) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(baseline.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def baseline_from_result(result: EvalResult, version: str, tolerance: float = 0.02) -> Baseline:
    return Baseline(version=version, metrics=result.metric_dict(), tolerance=tolerance)


def check_gate(result: EvalResult, baseline: Baseline) -> GateOutcome:
    current = result.metric_dict()
    failures: list[str] = []
    deltas: dict[str, float] = {}
    for name, base_value in baseline.metrics.items():
        cur = current.get(name)
        if cur is None:
            failures.append(f"missing metric '{name}' in current run")
            continue
        delta = round(cur - base_value, 4)
        deltas[name] = delta
        if cur + 1e-9 < base_value - baseline.tolerance:
            failures.append(
                f"{name}: {cur:.4f} below baseline {base_value:.4f} "
                f"(tolerance {baseline.tolerance:.4f}, delta {delta:+.4f})"
            )
    return GateOutcome(passed=not failures, failures=failures, deltas=deltas)
