"""BPMN 2.0 / draw.io / generic XML → :class:`ProcessGraph` import.

Tolerant by design. Three dialects are recognised:

* **BPMN 2.0** — ``task``/``userTask``/``serviceTask``, ``startEvent``/
  ``endEvent``, ``*Gateway``, ``sequenceFlow``.
* **draw.io / diagrams.net** — the ``mxGraphModel`` format, where shapes are
  ``<mxCell vertex="1">`` and connectors are ``<mxCell edge="1">``. Node kind is
  inferred from the cell ``style`` (rhombus → decision, ellipse/terminator →
  start/end by connectivity) and the label from ``value`` (HTML stripped).
* a minimal generic ``<node>/<edge>`` dialect for hand-rolled forms.

Namespaces are ignored by matching on the *local* tag name.

Parsing uses :mod:`defusedxml` (a core framework dependency), which hardens the
stdlib parser against XXE / external-entity / billion-laughs attacks. As a second
layer, the raw source is rejected outright if it declares a DOCTYPE or ENTITY
before any tree is built. Stdlib ``ElementTree`` is imported only for its element
and error *types*; the actual parse goes through the defused front end.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from defusedxml.ElementTree import fromstring as _defused_fromstring

from .models import KpiDefinition, NodeKind, ProcessEdge, ProcessGraph, ProcessNode


class ProcessImportError(ValueError):
    """Raised when an XML document cannot be parsed into a process graph."""


# BPMN local tag -> coarse node kind. Anything ending in 'Gateway' is a decision.
_KIND_BY_TAG: dict[str, NodeKind] = {
    "startevent": NodeKind.START,
    "endevent": NodeKind.END,
    "task": NodeKind.TASK,
    "usertask": NodeKind.TASK,
    "servicetask": NodeKind.TASK,
    "scripttask": NodeKind.TASK,
    "manualtask": NodeKind.TASK,
    "subprocess": NodeKind.TASK,
    "parallelgateway": NodeKind.PARALLEL,
    "node": NodeKind.TASK,
}


def import_process(
    process_id: str, xml: str, kpis: list[KpiDefinition] | None = None
) -> ProcessGraph:
    """Parse a BPMN/XML document into a :class:`ProcessGraph`.

    Args:
        process_id: Id to assign to the resulting process.
        xml: BPMN 2.0 or generic-dialect XML source.
        kpis: Optional user-defined KPIs to attach to the imported process.

    Returns:
        A populated :class:`ProcessGraph`.

    Raises:
        ProcessImportError: If the document is malformed, unsafe, or yields no
            recognisable process steps.
    """
    if "<!DOCTYPE" in xml or "<!ENTITY" in xml:
        raise ProcessImportError("DOCTYPE/ENTITY declarations are not allowed")
    try:
        root: ET.Element = _defused_fromstring(xml)
    except ET.ParseError as exc:
        raise ProcessImportError(f"invalid XML: {exc}") from exc

    root = _inflate_drawio_if_needed(root)
    if _is_drawio(root):
        nodes, edges = _parse_drawio(root)
        name = ""
    else:
        nodes, edges, name = _parse_bpmn(root)

    if not nodes:
        raise ProcessImportError("no process steps found in document")

    return ProcessGraph(
        id=process_id,
        name=name or process_id,
        description=_attr(root, "documentation"),
        nodes=nodes,
        edges=_valid_edges(edges, {n.id for n in nodes}),
        kpis=kpis or [],
    )


def _parse_bpmn(
    root: ET.Element,
) -> tuple[list[ProcessNode], list[ProcessEdge], str]:
    """Parse the BPMN / generic-dialect vocabulary into nodes and edges."""
    nodes: list[ProcessNode] = []
    edges: list[ProcessEdge] = []
    # A BPMN <process name> wins over the outer <definitions name>; fall back to
    # the id only when neither carries a name.
    name = _attr(root, "name")

    for element in root.iter():
        tag = _local(element.tag).lower()
        if tag == "process":
            name = _attr(element, "name") or name
        elif tag == "sequenceflow":
            edge = _to_edge(element)
            if edge is not None:
                edges.append(edge)
        elif tag in _KIND_BY_TAG or tag.endswith("gateway"):
            node = _to_node(element, tag)
            if node is not None:
                nodes.append(node)
    return nodes, edges, name


# ---------------------------------------------------------------------------
# draw.io / diagrams.net (mxGraphModel) dialect
# ---------------------------------------------------------------------------


def _is_drawio(root: ET.Element) -> bool:
    """Detect the draw.io ``mxGraphModel`` format by its marker tags."""
    for element in root.iter():
        if _local(element.tag).lower() in ("mxgraphmodel", "mxcell"):
            return True
    return False


def _inflate_drawio_if_needed(root: ET.Element) -> ET.Element:
    """Expand a compressed draw.io ``<diagram>`` payload into a real tree.

    draw.io commonly stores the diagram as deflate-compressed, base64-encoded,
    URL-escaped text inside ``<diagram>`` rather than as inline ``mxGraphModel``
    XML. When that is detected (a ``<diagram>`` with text and no inline model),
    the payload is inflated and re-parsed through the same hardened front end.
    Uncompressed documents are returned unchanged.
    """
    for element in root.iter():
        if _local(element.tag).lower() == "mxgraphmodel":
            return root  # already inline — nothing to inflate

    for element in root.iter():
        if _local(element.tag).lower() != "diagram":
            continue
        payload = (element.text or "").strip()
        if not payload:
            continue
        try:
            import base64
            import urllib.parse
            import zlib

            raw = zlib.decompress(base64.b64decode(payload), -15)
            inner = urllib.parse.unquote(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001 — not a compressed payload; leave as-is
            continue
        if "<!DOCTYPE" in inner or "<!ENTITY" in inner:
            raise ProcessImportError("DOCTYPE/ENTITY declarations are not allowed")
        try:
            return _defused_fromstring(inner)
        except ET.ParseError:
            continue
    return root


def _parse_drawio(
    root: ET.Element,
) -> tuple[list[ProcessNode], list[ProcessEdge]]:
    """Parse a draw.io diagram into nodes and edges.

    Shapes are ``<mxCell vertex="1">`` and connectors ``<mxCell edge="1">``; the
    implicit root/layer cells (ids ``0``/``1``, which are neither) are ignored.
    Node kind is inferred from ``style`` and, for terminator/ellipse shapes,
    refined to START/END by connectivity.
    """
    raw_nodes: list[tuple[str, str, str]] = []  # (id, name, style)
    edges: list[ProcessEdge] = []
    for element in root.iter():
        if _local(element.tag).lower() != "mxcell":
            continue
        if _attr(element, "vertex") == "1":
            node_id = _attr(element, "id")
            if node_id:
                name = _strip_html(_attr(element, "value")) or node_id
                raw_nodes.append((node_id, name, _attr(element, "style").lower()))
        elif _attr(element, "edge") == "1":
            source = _attr(element, "source")
            target = _attr(element, "target")
            if source and target:
                edges.append(
                    ProcessEdge(
                        source=source,
                        target=target,
                        condition=_strip_html(_attr(element, "value")),
                    )
                )

    indeg = {nid: 0 for nid, _, _ in raw_nodes}
    outdeg = {nid: 0 for nid, _, _ in raw_nodes}
    for edge in edges:
        if edge.source in outdeg:
            outdeg[edge.source] += 1
        if edge.target in indeg:
            indeg[edge.target] += 1

    nodes = [
        ProcessNode(
            id=nid,
            name=name,
            kind=_drawio_kind(style, indeg.get(nid, 0), outdeg.get(nid, 0)),
        )
        for nid, name, style in raw_nodes
    ]
    return nodes, edges


def _drawio_kind(style: str, indeg: int, outdeg: int) -> NodeKind:
    """Map a draw.io cell style + connectivity onto a coarse node kind."""
    if "rhombus" in style or "decision" in style:
        return NodeKind.DECISION
    if "parallel" in style:
        return NodeKind.PARALLEL
    if "ellipse" in style or "terminator" in style or "mxgraph.flowchart" in style:
        if indeg == 0:
            return NodeKind.START
        if outdeg == 0:
            return NodeKind.END
    return NodeKind.TASK


def _strip_html(value: str) -> str:
    """Reduce a draw.io HTML label to clean single-line text."""
    text = re.sub(r"<[^>]+>", " ", value)
    text = text.replace("&nbsp;", " ")
    return " ".join(text.split())


def _to_node(element: ET.Element, tag: str) -> ProcessNode | None:
    """Build a :class:`ProcessNode` from a BPMN flow element."""
    node_id = _attr(element, "id")
    if not node_id:
        return None
    kind = _KIND_BY_TAG.get(
        tag, NodeKind.DECISION if "gateway" in tag else NodeKind.TASK
    )
    return ProcessNode(
        id=node_id,
        name=_attr(element, "name") or node_id,
        kind=kind,
        role=_attr(element, "role"),
    )


def _to_edge(element: ET.Element) -> ProcessEdge | None:
    """Build a :class:`ProcessEdge` from a BPMN ``sequenceFlow``."""
    source = _attr(element, "sourceRef") or _attr(element, "source")
    target = _attr(element, "targetRef") or _attr(element, "target")
    if not source or not target:
        return None
    return ProcessEdge(source=source, target=target, condition=_attr(element, "name"))


def _valid_edges(edges: list[ProcessEdge], node_ids: set[str]) -> list[ProcessEdge]:
    """Drop edges that reference unknown nodes (defensive against partial XML)."""
    return [e for e in edges if e.source in node_ids and e.target in node_ids]


def _attr(element: ET.Element, name: str) -> str:
    """Read an attribute case-insensitively, returning '' when absent."""
    for key, value in element.attrib.items():
        if _local(key).lower() == name.lower():
            return value
    return ""


def _local(tag: str) -> str:
    """Strip an XML namespace prefix, returning the bare local name."""
    return tag.rsplit("}", 1)[-1]


__all__ = ["import_process", "ProcessImportError"]
