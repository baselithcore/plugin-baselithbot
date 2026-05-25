"""Eval harness orchestrator (ADR-0016).

The runner is intentionally pipeline-agnostic: callers inject a
`predict_fn(case) -> list[finding-like]`. Two ready-made providers are
shipped:

  * ``CannedProvider``  — returns pre-recorded findings keyed by case id
    (deterministic, used by CI gate).
  * ``LivePipelineProvider`` — invokes the real LangGraph pipeline against
    vLLM (opt-in, off by default).

Findings can be Pydantic ``Finding`` instances or plain dicts with the
same field names; the scorer accepts both via duck typing.
"""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .models import CaseScore, EvalCase, EvalResult
from .scorer import aggregate, score_case

PredictFn = Callable[[EvalCase], Awaitable[list[Any]]]


class Provider(Protocol):
    async def __call__(self, case: EvalCase) -> list[Any]:  # pragma: no cover
        ...


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no} invalid JSON: {exc}") from exc
            cases.append(EvalCase.model_validate(payload))
    return cases


class CannedProvider:
    """Return pre-recorded predictions per case id.

    Useful for CI gate: pipes deterministic finding dicts into the scorer
    so we exercise scoring/baseline plumbing without any LLM call.
    """

    def __init__(self, predictions: dict[str, list[dict[str, Any]]]) -> None:
        self._predictions = predictions

    async def __call__(self, case: EvalCase) -> list[Any]:
        return list(self._predictions.get(case.id, []))


class LivePipelineProvider:
    """Invoke the real graph against vLLM. Opt-in, not used in CI."""

    def __init__(self, doc_loader: Callable[[EvalCase], Awaitable[dict[str, Any]]]):
        self._doc_loader = doc_loader

    async def __call__(self, case: EvalCase) -> list[Any]:
        from ...agents.graph import get_graph

        state = await self._doc_loader(case)
        result = await get_graph().ainvoke(state)
        return list(result.get("final_findings") or result.get("findings") or [])


async def execute(
    cases: Iterable[EvalCase],
    provider: Provider | PredictFn,
    *,
    mode: str = "mock",
) -> EvalResult:
    case_scores: list[CaseScore] = []
    started = datetime.now(UTC).isoformat()

    for case in cases:
        t0 = time.perf_counter()
        error: str | None = None
        predicted: list[Any] = []
        try:
            predicted = await provider(case)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        latency_ms = (time.perf_counter() - t0) * 1000.0
        case_scores.append(
            score_case(case, predicted, latency_ms=latency_ms, error=error)
        )

    finished = datetime.now(UTC).isoformat()
    cases_list = list(cases) if not isinstance(cases, list) else cases
    result = aggregate(case_scores, cases_list)
    result.started_at = started
    result.finished_at = finished
    result.mode = mode  # type: ignore[assignment]
    return result
