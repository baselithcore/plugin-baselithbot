"""LangGraph orchestrator with parallel fan-out.

Topology:
  classifier → structurer → fan-out [legal, technical, pii] → synthesizer

ADR-0011: ClassifierAgent runs first to populate `doc_type`, which is then
used by Structurer (taxonomy) and per-agent applicability filtering. Agents
not applicable to the detected DocType short-circuit at run-time.
"""

from operator import add
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from ..schemas.finding import Finding, ReasoningStep
from ..schemas.state import Chunk, StructureNode
from . import classifier, legal, pii, structurer, synthesizer, technical


class ParallelState(TypedDict, total=False):
    """State with reducer-annotated findings for safe concurrent merge."""

    doc_id: str
    lang: str
    chunks: list[Chunk]
    structure: list[StructureNode]
    selected_policies: list[str]
    findings: Annotated[list[Finding], add]
    final_findings: list[Finding]
    score: int
    by_severity: dict[str, int]
    trace: Annotated[list[ReasoningStep], add]
    errors: Annotated[list[str], add]
    doc_type: str
    doc_type_confidence: float
    doc_type_low_confidence: bool
    doc_type_rationale: str


def build_graph() -> Any:
    graph: StateGraph[ParallelState] = StateGraph(ParallelState)
    graph.add_node("classifier", classifier.run)
    graph.add_node("structurer", structurer.run)
    graph.add_node("legal", legal.run)
    graph.add_node("technical", technical.run)
    graph.add_node("pii", pii.run)
    graph.add_node("synthesizer", synthesizer.run)

    graph.set_entry_point("classifier")
    graph.add_edge("classifier", "structurer")
    # Fan-out: structurer → 3 parallel agents
    graph.add_edge("structurer", "legal")
    graph.add_edge("structurer", "technical")
    graph.add_edge("structurer", "pii")
    # Fan-in: all 3 must complete before synthesizer
    graph.add_edge("legal", "synthesizer")
    graph.add_edge("technical", "synthesizer")
    graph.add_edge("pii", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


_compiled: Any = None


def get_graph() -> Any:
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
