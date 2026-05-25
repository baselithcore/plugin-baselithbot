# app/vectorstore/graph_sync.py
"""Graph database synchronization logic with metadata enrichment."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from agent_jira.graphdb import graph_db
from agent_jira.graphdb.relationship_schema import (
    build_relationship_properties,
    normalize_relationship_type,
)
from agent_jira.tenant_context import get_current_tenant_id

if TYPE_CHECKING:
    from agent_jira.agents.graph_agent import GraphAgent
    from agent_jira.agents.metadata_agent import ProjectContext

logger = logging.getLogger(__name__)

METADATA_GRAPH_SCHEMA_VERSION = 2
DOCUMENT_METADATA_EDGE_TYPES = (
    "HAS_STAKEHOLDER",
    "TARGETS_RELEASE",
    "HAS_DEADLINE",
    "STARTS_AT",
    "ENDS_AT",
    "HAS_MEETING",
    "HAS_DECISION",
    "HAS_MILESTONE",
    "USES_TECH",
    "HAS_RISK",
    "MENTIONS",
)
DOCUMENT_METADATA_EDGE_TYPES_CYPHER = (
    "["
    + ", ".join(f"'{edge_type}'" for edge_type in DOCUMENT_METADATA_EDGE_TYPES)
    + "]"
)


def _upsert_graph_document(
    document_id: str,
    fingerprint: str,
    *,
    source: str,
    metadata: Dict[str, Any],
    chunk_count: int,
    context: Optional[ProjectContext] = None,
) -> bool:
    """
    Sincronizza il nodo documento sul graph DB con metadata enrichment.

    Automatically extracts:
    - Project goals
    - Stakeholders
    - Timeline/milestones
    - Technologies
    - Risks

    Creates entity nodes and links them to the document.
    """
    if not graph_db.is_enabled():
        return False

    try:
        from agent_jira.agents.graph_agent import GraphAgent
        from agent_jira.agents.metadata_agent import MetadataAgent

        ga = GraphAgent(graph_db)

        # Idempotency Check:
        # If node exists and has same fingerprint, skip expensive LLM analysis
        try:
            existing_node = graph_db.get_node(document_id)
            if existing_node:
                existing_fp = existing_node.get("fingerprint")
                existing_version = existing_node.get("metadata_graph_version")
                if (
                    existing_fp
                    and existing_fp == fingerprint
                    and existing_version == METADATA_GRAPH_SCHEMA_VERSION
                ):
                    logger.info(
                        f"[graph_sync] Document {document_id} already up-to-date (fingerprint match). Skipping analysis."
                    )
                    return False
        except Exception as e:
            logger.warning(f"[graph_sync] Failed to check existing node: {e}")

        # Separate category from other properties
        cat = metadata.pop("category", None) if metadata else None

        # Prepare properties (safe primitives)
        safe_props: Dict[str, Any] = {
            "fingerprint": fingerprint,
            "source": source,
            "chunk_count": chunk_count,
            "metadata_graph_version": METADATA_GRAPH_SCHEMA_VERSION,
        }
        tenant_id = get_current_tenant_id()
        if tenant_id:
            safe_props["tenant_id"] = tenant_id
        for k, v in (metadata or {}).items():
            if k == "full_text":  # Do not store full text in graph node
                continue
            if isinstance(v, (str, int, float, bool)):
                safe_props[k] = v
            else:
                safe_props[k] = str(v)

        # Extract project context from document text if available
        full_text = metadata.get("full_text", "")
        if full_text and len(full_text) > 100:  # Only extract if substantial text
            try:
                agent = MetadataAgent()
                if not context:
                    context = agent.analyze_document(full_text, doc_id=document_id)
                else:
                    # Enrich existing context (from fast path) with LLM data
                    context = agent.enrich_metadata(
                        full_text, context, doc_id=document_id
                    )

                # Add extracted metadata to document properties
                if context.goals:
                    safe_props["goals"] = "; ".join(context.goals[:5])  # Limit to 5
                if context.domain:
                    safe_props["domain"] = context.domain
                if context.technologies:
                    safe_props["technologies"] = ", ".join(context.technologies[:10])

                logger.info(
                    f"Extracted metadata for {document_id}: "
                    f"{len(context.goals)} goals, {len(context.stakeholders)} stakeholders, "
                    f"{len(context.technologies)} technologies"
                )

            except Exception as e:
                logger.warning(f"Failed to extract metadata for {document_id}: {e}")
                context = None
        else:
            context = None

        # Upsert document node
        ga.upsert_document(
            doc_id=document_id,
            doc_type="file",
            path=str(metadata.get("filename") or document_id),
            category=str(cat) if cat else None,
            properties=safe_props,
        )

        _clear_document_metadata_entities(ga, document_id)

        # Create entity nodes and link them to document (AFTER document node is created)
        if context:
            _create_metadata_entities(ga, document_id, context)
        return True

    except Exception as exc:
        logger.warning(
            "[graphdb] Impossibile sincronizzare documento %s: %s",
            document_id,
            exc,
        )
        return False


def _create_metadata_entities(
    graph_agent: "GraphAgent",
    doc_id: str,
    context: "ProjectContext",
) -> None:
    """
    Create metadata entity nodes and link them to the document.

    Args:
        graph_agent: GraphAgent instance
        doc_id: Document ID
        context: Extracted project context
    """
    try:
        # Create stakeholder nodes and links
        for stakeholder in context.stakeholders[:10]:  # Limit to 10
            name = stakeholder.get("name", "")
            if name:
                stakeholder_id = graph_agent.upsert_stakeholder(
                    name=name,
                    role=stakeholder.get("role"),
                    email=stakeholder.get("email"),
                    source_document_id=doc_id,
                )
                if stakeholder_id:
                    # Link document to stakeholder
                    logger.info(f"Linking Doc {doc_id} -> Stakeholder {stakeholder_id}")
                    graph_agent.client.upsert_edge(
                        doc_id,
                        "HAS_STAKEHOLDER",
                        stakeholder_id,
                        properties=build_relationship_properties(
                            "HAS_STAKEHOLDER",
                            provenance="metadata_extraction",
                            source_document_id=doc_id,
                            extraction_method="metadata_agent",
                            confidence=0.92,
                            evidence=name,
                        ),
                    )

        # Create milestone nodes and links
        # Updated: context.timeline is now a list of dicts with rich metadata
        # Old format: {name: date} -> New format: [{name, date, type, status, description}]
        timeline_data = context.timeline

        # Backward compatibility check (if context.timeline is still a dict from old extraction)
        if isinstance(timeline_data, dict):
            # Convert old dict format to new list format
            timeline_data = [{"name": k, "date": v} for k, v in timeline_data.items()]

        for ms in timeline_data[:15]:  # Limit to 15 milestones
            if not isinstance(ms, dict):
                continue

            milestone_name = ms.get("name")
            if not milestone_name:
                continue

            milestone_id = graph_agent.upsert_milestone(
                name=milestone_name,
                date=ms.get("date"),
                description=ms.get("description"),
                milestone_type=ms.get("type", "Generic"),
                status=ms.get("status", "Planned"),
                source_document_id=doc_id,
            )

            # Determine semantic relationship
            milestone_type = ms.get("type", "Generic")
            edge_mapping = {
                "Release": "TARGETS_RELEASE",
                "Deadline": "HAS_DEADLINE",
                "Start": "STARTS_AT",
                "End": "ENDS_AT",
                "Meeting": "HAS_MEETING",
                "Decision": "HAS_DECISION",
            }
            edge_label = edge_mapping.get(milestone_type, "HAS_MILESTONE")

            if milestone_id:
                logger.info(
                    f"Linking Doc {doc_id} -> {edge_label} -> Milestone {milestone_id}"
                )
                graph_agent.client.upsert_edge(
                    doc_id,
                    edge_label,
                    milestone_id,
                    properties=build_relationship_properties(
                        edge_label,
                        provenance="metadata_extraction",
                        source_document_id=doc_id,
                        extraction_method="metadata_agent",
                        confidence=0.9,
                        evidence=milestone_name,
                    ),
                )

        # Create technology nodes and links
        for tech in context.technologies[:15]:  # Limit to 15
            tech_id = graph_agent.upsert_technology(
                name=tech,
                source_document_id=doc_id,
            )
            if tech_id:
                logger.info(f"Linking Doc {doc_id} -> Technology {tech_id}")
                graph_agent.client.upsert_edge(
                    doc_id,
                    "USES_TECH",
                    tech_id,
                    properties=build_relationship_properties(
                        "USES_TECH",
                        provenance="metadata_extraction",
                        source_document_id=doc_id,
                        extraction_method="metadata_agent",
                        confidence=0.94,
                        evidence=tech,
                    ),
                )

        # Create risk nodes and links
        for risk in context.risks[:10]:  # Limit to 10
            risk_id = graph_agent.upsert_risk(
                description=risk,
                source_document_id=doc_id,
            )
            if risk_id:
                logger.info(f"Linking Doc {doc_id} -> Risk {risk_id}")
                graph_agent.client.upsert_edge(
                    doc_id,
                    "HAS_RISK",
                    risk_id,
                    properties=build_relationship_properties(
                        "HAS_RISK",
                        provenance="metadata_extraction",
                        source_document_id=doc_id,
                        extraction_method="metadata_agent",
                        confidence=0.88,
                        evidence=risk[:140],
                    ),
                )

        logger.info(
            f"Created metadata entities for {doc_id}: "
            f"{len(context.stakeholders)} stakeholders, "
            f"{len(context.timeline)} milestones, "
            f"{len(context.technologies)} technologies, "
            f"{len(context.risks)} risks"
        )

    except Exception as e:
        logger.warning(f"Failed to create metadata entities for {doc_id}: {e}")

    # Create semantic relationships (Always try to process these)
    for rel in getattr(context, "semantic_relationships", []):
        try:
            # We expect dict: {source, target, relationship}
            # Source is usually the document itself or an entity referenced in it
            # For now, we assume the relationship is FROM an entity TO another entity
            # or FROM the document TO an entity if source is 'this' or empty

            source = rel.get("source")
            target = rel.get("target")
            relation_type = normalize_relationship_type(
                rel.get("relationship", "RELATED_TO")
            )
            confidence = rel.get("confidence")
            evidence = rel.get("evidence")

            if not source or not target:
                continue

            # If source is effectively the document (by name or empty), we link from doc_id
            # But currently semantic detection is text-based.
            # Simplification: We blindly create edges between named entities if they exist.
            # However, we don't know if these entities exist as nodes yet.
            # Ideally, we should upsert them as generic 'Entity' or 'Concept' nodes first.

            # Strategy: Upsert both as generic entities (Topic) if they assume to be concepts
            # This works for "Login API" or "UserProfile"

            # Robustness: Check before upserting
            if not source.strip() or not target.strip():
                continue

            src_node_id = graph_agent.upsert_topic(
                source,
                source_document_id=doc_id,
            )
            tgt_node_id = graph_agent.upsert_topic(
                target,
                source_document_id=doc_id,
            )

            if src_node_id and tgt_node_id:
                graph_agent.client.upsert_edge(
                    src_node_id,
                    relation_type,
                    tgt_node_id,
                    properties=build_relationship_properties(
                        relation_type,
                        provenance="semantic_relationship_extraction",
                        source_document_id=doc_id,
                        extraction_method="relationship_detector",
                        confidence=confidence,
                        evidence=evidence,
                    ),
                )
                logger.info(f"Semantic Edge: {source} -[{relation_type}]-> {target}")

                # Maintain connection to source document
                # This ensures the new topics are NOT orphans
                graph_agent.client.upsert_edge(
                    doc_id,
                    "MENTIONS",
                    src_node_id,
                    properties=build_relationship_properties(
                        "MENTIONS",
                        provenance="semantic_relationship_extraction",
                        source_document_id=doc_id,
                        extraction_method="relationship_detector",
                        confidence=confidence,
                        evidence=source,
                    ),
                )
                graph_agent.client.upsert_edge(
                    doc_id,
                    "MENTIONS",
                    tgt_node_id,
                    properties=build_relationship_properties(
                        "MENTIONS",
                        provenance="semantic_relationship_extraction",
                        source_document_id=doc_id,
                        extraction_method="relationship_detector",
                        confidence=confidence,
                        evidence=target,
                    ),
                )
        except Exception as e:
            logger.warning(f"Failed to create semantic edge: {e}")


def _clear_document_metadata_entities(graph_agent: "GraphAgent", doc_id: str) -> None:
    """Remove previously extracted metadata for a document before recreating it.

    In multi-tenant mode la cancellazione è scopata al tenant corrente per
    evitare che due documenti con stesso id (estremamente raro ma possibile
    con slug collisions cross-tenant) cancellino dati di un tenant diverso.
    """
    from agent_jira.tenant_context import get_current_tenant_id

    tenant_id = get_current_tenant_id()
    try:
        if tenant_id:
            graph_agent.client.query(
                (
                    "MATCH (d {id: $doc_id})-[r]->(m) "
                    f"WHERE type(r) IN {DOCUMENT_METADATA_EDGE_TYPES_CYPHER} "
                    "AND d.tenant_id = $tenant_id "
                    "DELETE r"
                ),
                {"doc_id": doc_id, "tenant_id": tenant_id},
            )
            graph_agent.client.query(
                (
                    "MATCH (n) WHERE n.source_document_id = $doc_id "
                    "AND n.tenant_id = $tenant_id DETACH DELETE n"
                ),
                {"doc_id": doc_id, "tenant_id": tenant_id},
            )
        else:
            graph_agent.client.query(
                (
                    "MATCH (d {id: $doc_id})-[r]->() "
                    f"WHERE type(r) IN {DOCUMENT_METADATA_EDGE_TYPES_CYPHER} "
                    "DELETE r"
                ),
                {"doc_id": doc_id},
            )
            graph_agent.client.query(
                "MATCH (n) WHERE n.source_document_id = $doc_id DETACH DELETE n",
                {"doc_id": doc_id},
            )
    except Exception as exc:
        logger.warning(
            "Failed to reset metadata entities for %s: %s",
            doc_id,
            exc,
        )
