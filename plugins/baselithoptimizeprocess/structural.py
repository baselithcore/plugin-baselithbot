"""Structure-only process analysis (no metrics required).

Bottleneck detection in :mod:`.detection` is *reactive* — it needs ingested KPI
samples to fire. A freshly mapped or imported process (e.g. a BPMN/draw.io
diagram) has no runtime data yet, so the optimizer would have nothing to reason
over. This module closes that gap: it inspects the process *graph topology* and
surfaces design-level inefficiency signals (rework loops, long sequential
chains, hand-off convergence, stacked approvals, orphaned/dangling steps) that
the optimizer can turn into advisory proposals before a single metric arrives.

Everything here is pure and deterministic over a :class:`ProcessGraph`, so it is
fully unit-testable and never touches I/O.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from .models import ProcessGraph, Severity

# Default: a linear hand-off chain at or above this length is worth flagging.
_LONG_CHAIN_THRESHOLD = 6
# A node with at least this many inbound (or outbound) edges is a hot spot.
_FAN_THRESHOLD = 3
# Substrings (lower-cased, multilingual) marking an approval/review-style step.
_APPROVAL_HINTS = (
    "approv",
    "review",
    "sign",
    "validat",
    "gate",
    "autoriz",
    "firma",
    "approvazione",
    "verifica",
)


class StructuralFindingKind(str, Enum):
    """Categories of design-level inefficiency detected from topology alone."""

    REWORK_LOOP = "rework_loop"
    LONG_CHAIN = "long_chain"
    CONVERGENCE = "convergence"
    SEQUENTIAL_APPROVALS = "sequential_approvals"
    ORPHAN = "orphan"
    NO_START = "no_start"
    NO_END = "no_end"


class StructuralFinding(BaseModel):
    """A design-level inefficiency signal localized to a process region."""

    kind: StructuralFindingKind
    severity: Severity = Severity.MEDIUM
    node_ids: list[str] = Field(default_factory=list)
    title: str
    detail: str
    suggestion: str = ""


def analyze_structure(process: ProcessGraph) -> list[StructuralFinding]:
    """Return structural findings for a process, highest-severity first."""
    nodes = process.nodes
    if not nodes:
        return []
    node_ids = {n.id for n in nodes}
    names = {n.id: (n.name or n.id) for n in nodes}
    out_adj: dict[str, list[str]] = {n.id: [] for n in nodes}
    indeg: dict[str, int] = {n.id: 0 for n in nodes}
    outdeg: dict[str, int] = {n.id: 0 for n in nodes}
    for edge in process.edges:
        if edge.source in node_ids and edge.target in node_ids:
            out_adj[edge.source].append(edge.target)
            outdeg[edge.source] += 1
            indeg[edge.target] += 1

    findings: list[StructuralFinding] = []
    findings += _entry_exit(nodes, indeg, outdeg, names)
    findings += _orphans(node_ids, indeg, outdeg, names)
    findings += _rework_loops(node_ids, out_adj, names)
    findings += _convergence(node_ids, indeg, outdeg, names)
    findings += _long_chains(node_ids, out_adj, indeg, outdeg, names)
    findings += _sequential_approvals(process, out_adj, names)

    findings.sort(key=lambda f: _SEVERITY_RANK.get(f.severity, 0), reverse=True)
    return findings


def _entry_exit(nodes, indeg, outdeg, names) -> list[StructuralFinding]:  # type: ignore[no-untyped-def]
    """Flag a missing single entry/exit — a sign of an ill-formed flow."""
    out: list[StructuralFinding] = []
    if not any(indeg[n.id] == 0 for n in nodes):
        out.append(
            StructuralFinding(
                kind=StructuralFindingKind.NO_START,
                severity=Severity.HIGH,
                title="No clear start step",
                detail="Every step has an inbound transition, so the process has "
                "no unambiguous entry point.",
                suggestion="Mark or add a single start step.",
            )
        )
    if not any(outdeg[n.id] == 0 for n in nodes):
        out.append(
            StructuralFinding(
                kind=StructuralFindingKind.NO_END,
                severity=Severity.HIGH,
                title="No clear end step",
                detail="Every step has an outbound transition, so the process has "
                "no unambiguous completion point.",
                suggestion="Mark or add a single end step.",
            )
        )
    return out


def _orphans(node_ids, indeg, outdeg, names) -> list[StructuralFinding]:  # type: ignore[no-untyped-def]
    """Flag isolated steps (no transitions) when the graph otherwise connects."""
    if len(node_ids) <= 1:
        return []
    orphans = [n for n in node_ids if indeg[n] == 0 and outdeg[n] == 0]
    if not orphans:
        return []
    return [
        StructuralFinding(
            kind=StructuralFindingKind.ORPHAN,
            severity=Severity.MEDIUM,
            node_ids=sorted(orphans),
            title=f"{len(orphans)} disconnected step(s)",
            detail="These steps have no transitions and are unreachable: "
            + ", ".join(names[o] for o in sorted(orphans)[:8]),
            suggestion="Connect them into the flow or remove them.",
        )
    ]


def _rework_loops(node_ids, out_adj, names) -> list[StructuralFinding]:  # type: ignore[no-untyped-def]
    """Detect cycles (rework loops) via DFS back-edge discovery."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in node_ids}
    cycle_nodes: set[str] = set()

    def visit(start: str) -> None:
        stack = [(start, iter(out_adj[start]))]
        color[start] = GREY
        path = [start]
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color[nxt] == GREY:  # back-edge → cycle
                    cycle_nodes.update(
                        path[path.index(nxt) :] if nxt in path else [nxt]
                    )
                elif color[nxt] == WHITE:
                    color[nxt] = GREY
                    stack.append((nxt, iter(out_adj[nxt])))
                    path.append(nxt)
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
                if path:
                    path.pop()

    for n in node_ids:
        if color[n] == WHITE:
            visit(n)
    if not cycle_nodes:
        return []
    return [
        StructuralFinding(
            kind=StructuralFindingKind.REWORK_LOOP,
            severity=Severity.HIGH,
            node_ids=sorted(cycle_nodes),
            title="Rework loop detected",
            detail="These steps form a cycle, indicating rework/back-and-forth: "
            + ", ".join(names[c] for c in sorted(cycle_nodes)[:8]),
            suggestion="Reduce rework: add upfront validation or a clear exit "
            "condition to break the loop.",
        )
    ]


def _convergence(node_ids, indeg, outdeg, names) -> list[StructuralFinding]:  # type: ignore[no-untyped-def]
    """Flag hand-off hot spots: steps with heavy fan-in or fan-out."""
    out: list[StructuralFinding] = []
    hot_in = [n for n in node_ids if indeg[n] >= _FAN_THRESHOLD]
    for n in sorted(hot_in, key=lambda x: indeg[x], reverse=True)[:3]:
        out.append(
            StructuralFinding(
                kind=StructuralFindingKind.CONVERGENCE,
                severity=Severity.MEDIUM,
                node_ids=[n],
                title=f"Hand-off bottleneck at '{names[n]}'",
                detail=f"'{names[n]}' converges {indeg[n]} inbound paths; it is a "
                "likely queueing/waiting point.",
                suggestion="Add capacity, parallelize upstream, or split this step.",
            )
        )
    return out


def _long_chains(node_ids, out_adj, indeg, outdeg, names) -> list[StructuralFinding]:  # type: ignore[no-untyped-def]
    """Flag long purely-sequential hand-off chains (no parallelism)."""
    linear = {n for n in node_ids if indeg[n] <= 1 and outdeg[n] <= 1}
    seen: set[str] = set()
    out: list[StructuralFinding] = []
    for start in node_ids:
        if start not in linear or start in seen or indeg[start] == 1:
            continue
        chain: list[str] = []
        cur = start
        while cur in linear and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            nxts = out_adj[cur]
            if nxts and nxts[0] in linear:
                cur = nxts[0]
            else:
                break
        if len(chain) >= _LONG_CHAIN_THRESHOLD:
            out.append(
                StructuralFinding(
                    kind=StructuralFindingKind.LONG_CHAIN,
                    severity=Severity.MEDIUM,
                    node_ids=chain,
                    title=f"Long sequential chain ({len(chain)} steps)",
                    detail="A run of "
                    f"{len(chain)} steps executes strictly in sequence with no "
                    "parallelism, inflating cycle time.",
                    suggestion="Parallelize independent steps or automate "
                    "low-value hand-offs.",
                )
            )
    return out


def _sequential_approvals(process, out_adj, names) -> list[StructuralFinding]:  # type: ignore[no-untyped-def]
    """Flag stacked approval/review steps that run back-to-back."""

    def is_approval(node_id: str) -> bool:
        node = next((n for n in process.nodes if n.id == node_id), None)
        if node is None:
            return False
        text = f"{node.name} {node.role}".lower()
        return any(hint in text for hint in _APPROVAL_HINTS)

    out: list[StructuralFinding] = []
    flagged: set[str] = set()
    for node in process.nodes:
        if node.id in flagged or not is_approval(node.id):
            continue
        run = [node.id]
        cur = node.id
        while True:
            nxts = [t for t in out_adj[cur] if is_approval(t) and t not in run]
            if not nxts:
                break
            cur = nxts[0]
            run.append(cur)
        if len(run) >= 2:
            flagged.update(run)
            out.append(
                StructuralFinding(
                    kind=StructuralFindingKind.SEQUENTIAL_APPROVALS,
                    severity=Severity.MEDIUM,
                    node_ids=run,
                    title=f"{len(run)} stacked approval steps",
                    detail="Consecutive approval/review steps run in series: "
                    + ", ".join(names[r] for r in run[:8]),
                    suggestion="Consolidate approvers or run approvals in "
                    "parallel to cut wait time.",
                )
            )
    return out


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


__all__ = ["StructuralFinding", "StructuralFindingKind", "analyze_structure"]
