"""CLI entry point: ``python -m docheck.services.eval`` (ADR-0016)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from .baseline import baseline_from_result, check_gate, load_baseline, save_baseline
from .models import EvalResult, GateOutcome
from .report_html import render_html
from .runner import CannedProvider, execute, load_cases


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="docheck.services.eval", description="Run the doCheck evaluation harness."
    )
    p.add_argument("--testset", type=Path, default=Path("tests/eval/testset.jsonl"))
    p.add_argument("--baseline", type=Path, default=Path("tests/eval/baseline.json"))
    p.add_argument(
        "--predictions",
        type=Path,
        help="JSON file mapping case_id -> [finding-like dicts] (mock mode)",
    )
    p.add_argument("--update-baseline", action="store_true")
    p.add_argument("--html", type=Path, help="Write standalone HTML report to PATH")
    p.add_argument(
        "--live",
        action="store_true",
        help="Use real LangGraph pipeline (opt-in, requires vLLM)",
    )
    p.add_argument("--tolerance", type=float, default=0.02)
    return p


def _print_summary(result: EvalResult, gate: GateOutcome | None = None) -> None:
    m = result.metric_dict()
    print(f"cases={len(result.cases)} TP={result.tp} FP={result.fp} FN={result.fn}")
    print(f"precision={m['precision']:.4f} recall={m['recall']:.4f} f1={m['f1']:.4f}")
    if gate is not None:
        verdict = "PASS" if gate.passed else "FAIL"
        deltas = " ".join(f"{k}{v:+.4f}" for k, v in gate.deltas.items())
        print(f"gate={verdict} {deltas}")
        for f in gate.failures:
            print(f"  ! {f}", file=sys.stderr)


async def _run(args: argparse.Namespace) -> int:
    cases = load_cases(args.testset)

    if args.live:
        print(
            "live mode requires a doc_loader implementation; not yet wired",
            file=sys.stderr,
        )
        return 2
    if not args.predictions:
        print("--predictions is required in mock mode (or use --live)", file=sys.stderr)
        return 2
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    provider = CannedProvider(predictions)

    result = await execute(cases, provider, mode="mock")
    gate = None

    if args.update_baseline:
        version = datetime.now(UTC).strftime("%Y-%m-%d")
        new_baseline = baseline_from_result(
            result, version=version, tolerance=args.tolerance
        )
        save_baseline(args.baseline, new_baseline)
        print(f"baseline written to {args.baseline} ({new_baseline.metrics})")
    elif args.baseline.exists():
        baseline = load_baseline(args.baseline)
        gate = check_gate(result, baseline)

    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_html(result, gate=gate), encoding="utf-8")
        print(f"html report written to {args.html}")

    _print_summary(result, gate)
    return 0 if (gate is None or gate.passed) else 1


def main() -> int:
    args = _build_parser().parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
