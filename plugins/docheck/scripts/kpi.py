"""Compute precision/recall on annotated test set.

Test set format: JSONL, one row per document.
{
  "doc_path": "tests/fixtures/contract_01.pdf",
  "lang": "it",
  "policies": ["IT_GDPR_2026"],
  "expected_findings": [
    {"rule_id": "GDPR-Art-13", "chunk_text_contains": "retention", "severity": "FAIL"}
  ]
}

Usage:
  uv run python scripts/kpi.py --testset tests/fixtures/testset.jsonl --report kpi_report.json
"""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docheck-engine" / "src"))

from docheck.services import parser  # noqa: E402
from docheck.agents import get_graph  # noqa: E402
from docheck.schemas.state import CheckState  # noqa: E402


def matches(expected: dict, actual_finding) -> bool:
    if expected["rule_id"] != actual_finding.rule_id:
        return False
    if expected.get("severity") and expected["severity"] != actual_finding.severity:
        return False
    needle = expected.get("chunk_text_contains")
    if needle and needle.lower() not in actual_finding.evidence.text.lower():
        return False
    return True


async def evaluate_doc(row: dict) -> tuple[int, int, int]:
    """Returns (true_positives, false_positives, false_negatives)."""
    doc_path = Path(row["doc_path"])
    mime = _guess_mime(doc_path)
    chunks = parser.parse(doc_path, mime)

    state: CheckState = {
        "doc_id": doc_path.stem, "lang": row.get("lang", "it"),
        "chunks": chunks, "structure": [],
        "selected_policies": row.get("policies", []),
        "findings": [], "trace": [], "errors": [],
    }
    final_state = await get_graph().ainvoke(state)
    findings = final_state.get("findings", [])
    expected = row.get("expected_findings", [])

    tp = 0
    matched_expected: set[int] = set()
    for f in findings:
        for i, exp in enumerate(expected):
            if i in matched_expected:
                continue
            if matches(exp, f):
                tp += 1
                matched_expected.add(i)
                break

    fp = len(findings) - tp
    fn = len(expected) - len(matched_expected)
    return tp, fp, fn


def _guess_mime(path: Path) -> str:
    return {
        ".pdf":  "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".md":   "text/markdown",
        ".txt":  "text/plain",
    }.get(path.suffix.lower(), "application/octet-stream")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--testset", required=True, type=Path)
    ap.add_argument("--report", type=Path, default=Path("kpi_report.json"))
    args = ap.parse_args()

    rows = [json.loads(line) for line in args.testset.read_text().splitlines() if line.strip()]
    total_tp = total_fp = total_fn = 0
    per_doc: list[dict] = []

    for row in rows:
        tp, fp, fn = await evaluate_doc(row)
        total_tp += tp; total_fp += fp; total_fn += fn
        per_doc.append({"doc": row["doc_path"], "tp": tp, "fp": fp, "fn": fn})
        print(f"{row['doc_path']}: TP={tp} FP={fp} FN={fn}")

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    recall    = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    summary = {
        "total_docs": len(rows),
        "tp": total_tp, "fp": total_fp, "fn": total_fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "per_doc": per_doc,
    }
    args.report.write_text(json.dumps(summary, indent=2))
    print(f"\n=== KPI ===")
    print(f"Precision: {precision:.3f}  Recall: {recall:.3f}  F1: {f1:.3f}")
    print(f"Report → {args.report}")

    # Acceptance gate (MVP)
    if precision < 0.85:
        sys.exit(f"FAIL: precision {precision:.3f} < 0.85 target")
    if recall < 0.80:
        sys.exit(f"FAIL: recall {recall:.3f} < 0.80 target")


if __name__ == "__main__":
    asyncio.run(main())
