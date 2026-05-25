"""Graph-grounded chat endpoint.

SSE streaming chat over the attack-surface graph. The LLM is given a
compacted, redacted view of the supplied nodes + edges and answers
questions about correlations, attack paths, lateral movement, blast
radius, etc. The endpoint never executes anything — it only reasons.
"""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from collections.abc import AsyncIterator
from typing import Any, Literal, cast

from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends as DependsParam
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.observability.logging import get_logger
from plugins.red_agent.dependencies import require_viewer
from plugins.red_agent.llm_planner import redact_secrets

logger = get_logger(__name__)

router = APIRouter(prefix="/graph", tags=["red-agent", "chat"])


_MAX_NODES = 400
_MAX_EDGES = 800
_MAX_HISTORY = 12
_MAX_QUESTION_CHARS = 4000

_SYSTEM_PROMPT = (
    "You are a red-team graph analyst. You are given a snapshot of an "
    "attack-surface graph (nodes + edges) and must answer the operator's "
    "questions about correlations, attack paths, blast radius, lateral "
    "movement, and prioritisation. Constraints:\n"
    "- Reason ONLY from the provided graph. If something is not in the "
    "graph, say so. Never fabricate node IDs, CVEs, or relationships.\n"
    "- When you reference a node or edge, cite its id in backticks "
    "(e.g. `endpoint:web-1`).\n"
    "- Be terse and concrete. Lead with the answer, then evidence.\n"
    "- If asked to act (run a scan, exploit, etc.) refuse and explain "
    "this is a read-only analytical surface.\n"
    "- Output plain markdown. No code fences unless quoting raw data."
)


class _CyNodeData(BaseModel):
    id: str
    label: str
    display: str | None = None
    severity: str | None = None
    cvss: float | str | None = None


class _CyEdgeData(BaseModel):
    source: str
    target: str
    type: str


class _CyNode(BaseModel):
    data: _CyNodeData


class _CyEdge(BaseModel):
    data: _CyEdgeData


class _ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class GraphChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=_MAX_QUESTION_CHARS)
    nodes: list[_CyNode] = Field(default_factory=list, max_length=_MAX_NODES)
    edges: list[_CyEdge] = Field(default_factory=list, max_length=_MAX_EDGES)
    focus_ids: list[str] = Field(default_factory=list, max_length=20)
    scan_id: str | None = None
    target: str | None = None
    history: list[_ChatTurn] = Field(default_factory=list, max_length=_MAX_HISTORY)


def _redact_str(value: str) -> str:
    return cast(str, redact_secrets(value))


_NODE_BUDGET = 25
_EDGE_BUDGET = 40
_DISPLAY_TRUNC = 40
_PROMPT_CHAR_CAP = 18000  # ~4500 tokens — leaves room for system + response.


def _summarize_graph(req: GraphChatRequest) -> str:
    nodes = req.nodes
    edges = req.edges
    by_label: Counter[str] = Counter(n.data.label for n in nodes)
    sev_hist: Counter[str] = Counter(
        (n.data.severity or "n/a") for n in nodes if n.data.label == "Vulnerability"
    )
    edge_hist: Counter[str] = Counter(e.data.type for e in edges)

    focus_set = set(req.focus_ids)
    nodes_by_id = {n.data.id: n for n in nodes}
    # Build adjacency restricted to focused nodes + 1-hop neighbors.
    focus_neighbors: set[str] = set(focus_set)
    if focus_set:
        for e in edges:
            if e.data.source in focus_set:
                focus_neighbors.add(e.data.target)
            if e.data.target in focus_set:
                focus_neighbors.add(e.data.source)

    # Rank non-focused nodes: criticals > high > others, then by degree.
    sev_rank = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
    deg: Counter[str] = Counter()
    for e in edges:
        deg[e.data.source] += 1
        deg[e.data.target] += 1

    def _rank(n: _CyNode) -> tuple[int, int]:
        s = sev_rank.get(n.data.severity or "", 0)
        return (s, deg[n.data.id])

    node_lines: list[str] = []
    seen: set[str] = set()
    # Focused first.
    for nid in focus_set:
        n = nodes_by_id.get(nid)
        if n:
            node_lines.append(_node_line(n, focused=True))
            seen.add(nid)
    # Then neighbors of focus.
    for nid in focus_neighbors - focus_set:
        n = nodes_by_id.get(nid)
        if n and len(node_lines) < _NODE_BUDGET:
            node_lines.append(_node_line(n, focused=False))
            seen.add(nid)
    # Fill with top-ranked remaining.
    remaining = sorted(
        (n for n in nodes if n.data.id not in seen), key=_rank, reverse=True
    )
    for n in remaining:
        if len(node_lines) >= _NODE_BUDGET:
            break
        node_lines.append(_node_line(n, focused=False))
        seen.add(n.data.id)

    # Edges: focus-touching first, then high-severity-touching, capped.
    edge_lines: list[str] = []
    used_edges: set[int] = set()
    if focus_set:
        for i, e in enumerate(edges):
            if len(edge_lines) >= _EDGE_BUDGET:
                break
            if e.data.source in focus_set or e.data.target in focus_set:
                edge_lines.append(_edge_line(e))
                used_edges.add(i)
    for i, e in enumerate(edges):
        if len(edge_lines) >= _EDGE_BUDGET:
            break
        if i in used_edges:
            continue
        s = nodes_by_id.get(e.data.source)
        t = nodes_by_id.get(e.data.target)
        if (s and (s.data.severity or "") in ("critical", "high")) or (
            t and (t.data.severity or "") in ("critical", "high")
        ):
            edge_lines.append(_edge_line(e))
            used_edges.add(i)
    for i, e in enumerate(edges):
        if len(edge_lines) >= _EDGE_BUDGET:
            break
        if i in used_edges:
            continue
        edge_lines.append(_edge_line(e))

    parts: list[str] = []
    if req.target:
        parts.append(f"target: {req.target}")
    if req.scan_id:
        parts.append(f"scan_id: {req.scan_id}")
    parts.append(f"totals: {len(nodes)} nodes, {len(edges)} edges")
    parts.append(
        "node counts: "
        + ", ".join(
            f"{k}={v}" for k, v in sorted(by_label.items(), key=lambda x: -x[1])
        )
    )
    if sev_hist:
        parts.append(
            "vuln severity: "
            + ", ".join(
                f"{k}={v}" for k, v in sorted(sev_hist.items(), key=lambda x: -x[1])
            )
        )
    parts.append(
        "edge types: "
        + ", ".join(
            f"{k}={v}" for k, v in sorted(edge_hist.items(), key=lambda x: -x[1])
        )
    )
    if focus_set:
        parts.append("focused: " + ", ".join(sorted(focus_set)))
    parts.append(
        f"top nodes (focused + ranked, {len(node_lines)}/{len(nodes)} shown):\n"
        + "\n".join(node_lines)
    )
    parts.append(
        f"top edges ({len(edge_lines)}/{len(edges)} shown):\n" + "\n".join(edge_lines)
    )
    summary = "\n".join(parts)
    return _redact_str(summary)


def _edge_line(e: _CyEdge) -> str:
    return f"  {e.data.source} -[{e.data.type}]-> {e.data.target}"


def _node_line(n: _CyNode, *, focused: bool) -> str:
    d = n.data
    bits = [d.id, d.label]
    if d.display and d.display != d.id:
        bits.append(d.display[:_DISPLAY_TRUNC])
    if d.severity:
        bits.append(f"sev={d.severity}")
    if d.cvss not in (None, ""):
        bits.append(f"cvss={d.cvss}")
    prefix = "* " if focused else "  "
    return prefix + " | ".join(bits)


def _build_prompt(req: GraphChatRequest) -> str:
    summary = _summarize_graph(req)
    history_lines: list[str] = []
    for turn in req.history[-_MAX_HISTORY:]:
        # Trim each turn so a long prior assistant answer doesn't blow the budget.
        content = _redact_str(turn.content)[:600]
        history_lines.append(f"{turn.role.upper()}: {content}")
    history_block = "\n".join(history_lines) if history_lines else "(no prior turns)"
    prompt = (
        f"# graph snapshot\n{summary}\n\n"
        f"# conversation so far\n{history_block}\n\n"
        f"# operator question\n{_redact_str(req.question)}\n\n"
        "Answer now."
    )
    if len(prompt) > _PROMPT_CHAR_CAP:
        prompt = prompt[:_PROMPT_CHAR_CAP] + "\n…[snapshot truncated]"
    return prompt


def _sse(event: str, data: dict[str, Any] | str) -> bytes:
    payload = data if isinstance(data, str) else json.dumps(data, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode()


async def _stream_answer(req: GraphChatRequest) -> AsyncIterator[bytes]:
    try:
        from core.services.llm.service import get_llm_service
    except Exception as exc:
        yield _sse("error", {"message": f"LLM service unavailable: {exc}"})
        return

    try:
        service = get_llm_service()
    except Exception as exc:
        yield _sse("error", {"message": f"LLM service init failed: {exc}"})
        return

    prompt = _build_prompt(req)
    yield _sse("start", {"prompt_chars": len(prompt)})
    try:
        async for chunk in service.generate_response_stream(
            prompt=prompt, system_prompt=_SYSTEM_PROMPT
        ):
            if not chunk:
                continue
            yield _sse("delta", {"text": chunk})
            # Cooperative yield so the event loop flushes promptly.
            await asyncio.sleep(0)
        yield _sse("end", {})
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("graph_chat stream failed")
        yield _sse("error", {"message": str(exc)})


@router.post("/chat", dependencies=[cast(DependsParam, require_viewer())])
async def graph_chat(req: GraphChatRequest) -> StreamingResponse:
    """SSE stream of the LLM answer grounded in the supplied graph."""
    if not req.nodes and not req.focus_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least nodes or focus_ids for graph context.",
        )
    return StreamingResponse(
        _stream_answer(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
