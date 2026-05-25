"""
FalkorDB graph layer for the Red Agent.

Core scan-result schema:

  (:Target {id, type, value, tenant_id})
    -[:HAS_ENDPOINT]-> (:Endpoint {url, method})
    -[:EXPOSES]-> (:Service {name, port, protocol})
    -[:HAS_VULN]-> (:Vulnerability {id, title, severity, cvss, cve, cwe, scanner})
       -[:MAPS_TO]-> (:CWE {id, name})
       -[:MAPS_TO]-> (:CVE {id, year})
       -[:DETECTED_BY]-> (:Scanner {name})
       -[:FOUND_IN]-> (:Scan {id, started_at, intensity, requested_by})

Context-aware extension (populated by the operator's cloud-context
plugin or imported from external CSPM/CMDB sources):

  (:CloudResource {id, kind, region, owner_account})
    -[:HOSTS]-> (:Target)
    -[:RUNS_AS]-> (:Identity {id, principal, type})
    -[:STORES]-> (:DataStore {id, kind, sensitivity})
    -[:GOVERNED_BY]-> (:ApiSpec {id, format, location})

  (:Vulnerability)-[:LATERAL_TO]->(:CloudResource | :Identity | :DataStore)

The orchestrator upserts the scan-result subgraph; the cloud-context
nodes are inserted by external code (`upsert_cloud_resource`,
`upsert_identity`, `upsert_data_store`, `upsert_api_spec`,
`link_lateral_path`). Lateral movement queries traverse both layers.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from core.observability.logging import get_logger
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.models import Finding, ScanRequest, Target

logger = get_logger(__name__)


class VulnerabilityGraph:
    """
    Thin wrapper over a FalkorDB client.

    The injected ``client`` is expected to expose ``select_graph(name)``
    returning an object with ``.query(cypher, params)`` — the standard
    ``falkordb`` Python SDK shape. When ``client`` is ``None`` (FalkorDB
    unreachable / not installed) every method degrades to a no-op so the
    rest of the agent keeps working. Cypher errors are logged and
    swallowed: a graph hiccup must never stall a scan.
    """

    def __init__(self, client: Any | None, config: RedAgentConfig) -> None:
        self.client = client
        self.available = client is not None
        self.graph = config.graph_name

    def _query(self, cypher: str, params: dict[str, Any]) -> Any:
        if self.client is None:
            return None
        try:
            graph = self.client.select_graph(self.graph)
            return graph.query(cypher, params)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.graph.query_failed",
                extra={"err": str(e), "graph": self.graph},
            )
            return None

    def upsert_target(self, target: Target, tenant_id: str | None) -> None:
        self._query(
            """
            MERGE (t:Target {id: $id})
            SET t.type = $type, t.value = $value, t.tenant_id = $tenant_id
            """,
            {
                "id": f"target::{target.value}",
                "type": target.type.value,
                "value": target.value,
                "tenant_id": tenant_id,
            },
        )

    def upsert_scan(self, scan_id: UUID, request: ScanRequest) -> None:
        self._query(
            """
            MERGE (s:Scan {id: $id})
            SET s.intensity = $intensity, s.requested_by = $requested_by
            WITH s
            MATCH (t:Target {id: $target_id})
            MERGE (t)-[:SCANNED_BY]->(s)
            """,
            {
                "id": str(scan_id),
                "intensity": request.intensity.value,
                "requested_by": request.requested_by,
                "target_id": f"target::{request.target.value}",
            },
        )

    def upsert_finding(self, scan_id: UUID, finding: Finding) -> None:
        self._query(
            """
            MERGE (v:Vulnerability {id: $id})
            SET v.title = $title,
                v.severity = $severity,
                v.cvss = $cvss,
                v.cve = $cve,
                v.cwe = $cwe,
                v.scanner = $scanner
            WITH v
            MATCH (s:Scan {id: $scan_id})
            MERGE (s)-[:FOUND]->(v)
            WITH v
            MATCH (t:Target {id: $target_id})
            MERGE (t)-[:HAS_VULN]->(v)
            """,
            {
                "id": str(finding.id),
                "title": finding.title,
                "severity": finding.severity.value,
                "cvss": finding.cvss_score,
                "cve": finding.cve,
                "cwe": finding.cwe,
                "scanner": finding.scanner,
                "scan_id": str(scan_id),
                "target_id": f"target::{finding.target}",
            },
        )

        if finding.endpoint:
            self._query(
                """
                MERGE (e:Endpoint {url: $url})
                WITH e
                MATCH (t:Target {id: $target_id})
                MERGE (t)-[:HAS_ENDPOINT]->(e)
                WITH e
                MATCH (v:Vulnerability {id: $vuln_id})
                MERGE (e)-[:HAS_VULN]->(v)
                """,
                {
                    "url": finding.endpoint,
                    "target_id": f"target::{finding.target}",
                    "vuln_id": str(finding.id),
                },
            )

        if finding.port:
            self._query(
                """
                MERGE (s:Service {key: $key})
                SET s.name = $name, s.port = $port, s.protocol = $protocol
                WITH s
                MATCH (t:Target {id: $target_id})
                MERGE (t)-[:EXPOSES]->(s)
                WITH s
                MATCH (v:Vulnerability {id: $vuln_id})
                MERGE (s)-[:HAS_VULN]->(v)
                """,
                {
                    "key": f"{finding.target}:{finding.port}",
                    "name": finding.service or "unknown",
                    "port": finding.port,
                    "protocol": "tcp",
                    "target_id": f"target::{finding.target}",
                    "vuln_id": str(finding.id),
                },
            )

    # ---- context layer (cloud / identity / data) -------------------

    def upsert_cloud_resource(
        self,
        *,
        resource_id: str,
        kind: str,
        region: str | None = None,
        owner_account: str | None = None,
        target_value: str | None = None,
    ) -> None:
        """Register a CloudResource and optionally link it to a Target."""
        self._query(
            """
            MERGE (c:CloudResource {id: $id})
            SET c.kind = $kind,
                c.region = $region,
                c.owner_account = $owner_account
            """,
            {
                "id": resource_id,
                "kind": kind,
                "region": region,
                "owner_account": owner_account,
            },
        )
        if target_value is not None:
            self._query(
                """
                MATCH (c:CloudResource {id: $cid}), (t:Target {id: $tid})
                MERGE (c)-[:HOSTS]->(t)
                """,
                {
                    "cid": resource_id,
                    "tid": f"target::{target_value}",
                },
            )

    def upsert_identity(
        self,
        *,
        identity_id: str,
        principal: str,
        type_: str,
        cloud_resource_id: str | None = None,
    ) -> None:
        self._query(
            """
            MERGE (i:Identity {id: $id})
            SET i.principal = $principal, i.type = $type
            """,
            {"id": identity_id, "principal": principal, "type": type_},
        )
        if cloud_resource_id is not None:
            self._query(
                """
                MATCH (c:CloudResource {id: $cid}), (i:Identity {id: $iid})
                MERGE (c)-[:RUNS_AS]->(i)
                """,
                {"cid": cloud_resource_id, "iid": identity_id},
            )

    def upsert_data_store(
        self,
        *,
        store_id: str,
        kind: str,
        sensitivity: str = "unknown",
        cloud_resource_id: str | None = None,
    ) -> None:
        self._query(
            """
            MERGE (d:DataStore {id: $id})
            SET d.kind = $kind, d.sensitivity = $sensitivity
            """,
            {"id": store_id, "kind": kind, "sensitivity": sensitivity},
        )
        if cloud_resource_id is not None:
            self._query(
                """
                MATCH (c:CloudResource {id: $cid}), (d:DataStore {id: $did})
                MERGE (c)-[:STORES]->(d)
                """,
                {"cid": cloud_resource_id, "did": store_id},
            )

    def upsert_api_spec(
        self,
        *,
        spec_id: str,
        format_: str,
        location: str,
        target_value: str | None = None,
    ) -> None:
        self._query(
            """
            MERGE (a:ApiSpec {id: $id})
            SET a.format = $format, a.location = $location
            """,
            {"id": spec_id, "format": format_, "location": location},
        )
        if target_value is not None:
            self._query(
                """
                MATCH (a:ApiSpec {id: $aid}), (t:Target {id: $tid})
                MERGE (t)-[:GOVERNED_BY]->(a)
                """,
                {"aid": spec_id, "tid": f"target::{target_value}"},
            )

    def link_lateral_path(
        self,
        vuln_id: str,
        next_node_label: str,
        next_node_id: str,
    ) -> None:
        """Link a vulnerability to a downstream resource it can pivot to."""
        if next_node_label not in {"CloudResource", "Identity", "DataStore"}:
            raise ValueError(f"unsupported lateral target {next_node_label!r}")
        self._query(
            f"""
            MATCH (v:Vulnerability {{id: $vid}}), (n:{next_node_label} {{id: $nid}})
            MERGE (v)-[:LATERAL_TO]->(n)
            """,
            {"vid": vuln_id, "nid": next_node_id},
        )

    def lateral_paths(self, vuln_id: str, max_depth: int = 3) -> list[list[Any]]:
        """Return paths from a vulnerability through the context layer."""
        result = self._query(
            f"""
            MATCH path = (v:Vulnerability {{id: $vid}})
                         -[:LATERAL_TO|RUNS_AS|STORES|HOSTS*1..{max_depth}]-(n)
            RETURN path
            """,
            {"vid": vuln_id},
        )
        if hasattr(result, "result_set"):
            return list(result.result_set)
        return list(result or [])

    # ---- finding-scoped subgraph (modal drilldown) -----------------

    def finding_subgraph(self, finding_id: str, depth: int = 2) -> dict[str, Any]:
        """Return the small subgraph centered on a single vulnerability.

        Used by the finding-detail modal to render a focused view: the
        vulnerability node, its parent target/endpoint/service, the scan
        that found it, and any lateral links out to identities/data
        stores within ``depth`` hops. Output is the same Cytoscape shape
        as :meth:`attack_surface` so the front-end can reuse one
        renderer.
        """
        # Path must not traverse any *other* Vulnerability node, otherwise
        # depth=2 expands through the parent Target/Scan/Endpoint back out
        # to every sibling finding and the subgraph degenerates into the
        # full scan attack-surface graph.
        nodes_query = f"""
        MATCH p = (v:Vulnerability {{id: $id}})-[*0..{depth}]-(n)
        WHERE ALL(x IN nodes(p) WHERE
            (labels(x)[0] <> 'Vulnerability' OR x.id = $id)
            AND labels(x)[0] <> 'Scan')
        WITH DISTINCT n
        RETURN
          coalesce(n.id, n.url, n.key)              AS node_id,
          labels(n)[0]                              AS node_label,
          coalesce(n.value, n.url, n.title, n.name, n.id) AS display,
          n.severity                                AS severity,
          n.cvss                                    AS cvss
        """
        edges_query = f"""
        MATCH p = (v:Vulnerability {{id: $id}})-[*1..{depth}]-(n)
        WHERE ALL(x IN nodes(p) WHERE
            (labels(x)[0] <> 'Vulnerability' OR x.id = $id)
            AND labels(x)[0] <> 'Scan')
        UNWIND relationships(p) AS r
        RETURN DISTINCT
          coalesce(startNode(r).id, startNode(r).url, startNode(r).key) AS source,
          coalesce(endNode(r).id, endNode(r).url, endNode(r).key) AS target,
          type(r) AS rel_type
        """
        params = {"id": finding_id}
        nodes_raw = self._query(nodes_query, params)
        edges_raw = self._query(edges_query, params)

        nodes = [
            {
                "data": {
                    "id": str(_pick(row, "node_id", 0)),
                    "label": _pick(row, "node_label", 1) or "Node",
                    "display": _pick(row, "display", 2) or "",
                    "severity": _pick(row, "severity", 3),
                    "cvss": _pick(row, "cvss", 4),
                }
            }
            for row in _iter_rows(nodes_raw)
            if _pick(row, "node_id", 0) is not None
        ]
        edges = [
            {
                "data": {
                    "id": (
                        f"{_pick(row, 'source', 0)}--"
                        f"{_pick(row, 'rel_type', 2)}-->"
                        f"{_pick(row, 'target', 1)}"
                    ),
                    "source": str(_pick(row, "source", 0)),
                    "target": str(_pick(row, "target", 1)),
                    "type": _pick(row, "rel_type", 2),
                }
            }
            for row in _iter_rows(edges_raw)
            if _pick(row, "source", 0) is not None
            and _pick(row, "target", 1) is not None
        ]
        return {"nodes": nodes, "edges": edges}

    # ---- existing attack-surface query ------------------------------

    def attack_surface(self, target_value: str) -> dict[str, Any]:
        """
        Return Cytoscape-shaped nodes + edges for the dashboard attack-surface view.

        Output:
            {"nodes": [{"data": {...}}], "edges": [{"data": {...}}]}
        """
        nodes_query = """
        MATCH (t:Target {id: $id})-[*0..3]-(n)
        RETURN DISTINCT
          coalesce(n.id, n.url, n.key)            AS node_id,
          labels(n)[0]                            AS node_label,
          coalesce(n.value, n.url, n.title, n.name, n.id) AS display,
          n.severity                              AS severity,
          n.cvss                                  AS cvss
        """
        # Walk every path from the target out to 3 hops and unwind the
        # relationships along the way. The earlier ``exists((t)-[*..3]-(a))``
        # form returned an empty edge set under FalkorDB, leaving the
        # attack-surface graph rendered as orphan nodes only.
        edges_query = """
        MATCH p = (t:Target {id: $id})-[*1..3]-(n)
        UNWIND relationships(p) AS r
        RETURN DISTINCT
          coalesce(startNode(r).id, startNode(r).url, startNode(r).key) AS source,
          coalesce(endNode(r).id, endNode(r).url, endNode(r).key) AS target,
          type(r) AS rel_type
        """
        params = {"id": f"target::{target_value}"}

        nodes_raw = self._query(nodes_query, params)
        edges_raw = self._query(edges_query, params)

        nodes = [
            {
                "data": {
                    "id": str(_pick(row, "node_id", 0)),
                    "label": _pick(row, "node_label", 1) or "Node",
                    "display": _pick(row, "display", 2) or "",
                    "severity": _pick(row, "severity", 3),
                    "cvss": _pick(row, "cvss", 4),
                }
            }
            for row in _iter_rows(nodes_raw)
            if _pick(row, "node_id", 0) is not None
        ]
        edges = [
            {
                "data": {
                    "id": f"{_pick(row, 'source', 0)}--{_pick(row, 'rel_type', 2)}-->{_pick(row, 'target', 1)}",
                    "source": str(_pick(row, "source", 0)),
                    "target": str(_pick(row, "target", 1)),
                    "type": _pick(row, "rel_type", 2),
                }
            }
            for row in _iter_rows(edges_raw)
            if _pick(row, "source", 0) is not None
            and _pick(row, "target", 1) is not None
        ]
        return {"nodes": nodes, "edges": edges}


def _iter_rows(result: Any) -> Any:
    """Tolerate FalkorDB result shapes (object with .result_set or raw list)."""
    if result is None:
        return []
    if hasattr(result, "result_set"):
        return result.result_set
    return result


def _pick(row: Any, key: str, idx: int) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    if isinstance(row, (list, tuple)) and idx < len(row):
        return row[idx]
    return None
