"""Jira entity operations for graph database management."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

from agent_jira.graphdb import GraphDb
from agent_jira.graphdb.relationship_schema import build_relationship_properties

logger = logging.getLogger(__name__)


class EntityOperations:
    """Handles Jira entity node operations (Epic, Story, TestCase, Requirement)."""

    def __init__(self, graph_client: GraphDb) -> None:
        self.client = graph_client

    def upsert_requirement(
        self,
        req_id: str,
        text: str,
        source_doc_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registra un requisito e opzionalmente lo collega al documento sorgente."""
        if not self.client.is_enabled():
            return

        try:
            # Shorten name for display
            short_name = text
            if len(short_name) > 50:
                short_name = short_name[:47] + "..."

            props = {"text": text, "name": short_name}
            props["label_display"] = f"Requirement: {req_id}"
            if properties:
                props.update(properties)

            self.client.upsert_node(req_id, labels=["Requirement"], properties=props)
            if source_doc_id:
                self.client.upsert_edge(
                    req_id,
                    "DERIVES_FROM",
                    source_doc_id,
                    properties=build_relationship_properties(
                        "DERIVES_FROM",
                        provenance="metadata_extraction",
                        source_document_id=source_doc_id,
                        extraction_method="requirement_extraction",
                        confidence=0.95,
                        evidence=text[:140],
                    ),
                )
            logger.debug(f"GraphAgent: upsert_requirement {req_id}")
        except Exception:
            logger.warning(
                f"GraphAgent: failed to upsert requirement {req_id}", exc_info=True
            )

    def upsert_epic(
        self,
        epic_id: str,
        summary: str,
        status: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registra un'Epica Jira."""
        if not self.client.is_enabled():
            return

        try:
            props = {"summary": summary, "status": status, "name": summary}
            props["label_display"] = f"Epic: {summary}"
            if properties:
                props.update(properties)
            self.client.upsert_node(epic_id, labels=["Epic"], properties=props)
            logger.debug(f"GraphAgent: upsert_epic {epic_id}")
        except Exception:
            logger.warning(
                f"GraphAgent: failed to upsert epic {epic_id}", exc_info=True
            )

    def upsert_story(
        self,
        story_id: str,
        summary: str,
        status: str,
        points: Optional[int] = None,
        assignee: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registra una User Story Jira."""
        if not self.client.is_enabled():
            return

        try:
            props = {"summary": summary, "status": status, "name": summary}
            props["label_display"] = f"Story: {summary} ({status})"
            if points is not None:
                props["points"] = points
            if properties:
                props.update(properties)

            # People handling
            if properties:
                assignee = properties.get("assignee")
                reporter = properties.get("reporter")
                if assignee:
                    props["assignee"] = assignee
                if reporter:
                    props["reporter"] = reporter

            self.client.upsert_node(story_id, labels=["Story"], properties=props)
            logger.debug(f"GraphAgent: upsert_story {story_id}")

            # --- Vector Store Sync ---
            # Calcoliamo embedding per ricerca semantica duplicati
            try:
                import uuid

                from qdrant_client.models import PointStruct

                from agent_jira.nlp_models import get_embedder
                from agent_jira.config import COLLECTION, QDRANT

                # Deterministico based on story_id per evitare duplicati
                # Usa un namespace fisso per generare UUID da stringa
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"story_{story_id}"))

                embedder = get_embedder()
                vector = embedder.encode(summary, convert_to_numpy=True)
                # Convert numpy array to list
                if hasattr(vector, "tolist"):
                    vector = vector.tolist()

                payload = {
                    "type": "story",
                    "story_id": story_id,
                    "text": summary,
                    "status": status,
                }

                QDRANT.upsert(
                    collection_name=COLLECTION,
                    points=[PointStruct(id=point_id, vector=vector, payload=payload)],
                )
                logger.debug(f"GraphAgent: upserted story vector {story_id}")
            except Exception:
                # Non bloccare il flusso principale se il vettore fallisce
                logger.warning(
                    f"GraphAgent: failed to sync story vector {story_id}", exc_info=True
                )
        except Exception:
            logger.warning(
                f"GraphAgent: failed to upsert story {story_id}", exc_info=True
            )

    def upsert_test_case(
        self,
        test_id: str,
        test_type: str,
        summary: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registra un Test Case."""
        if not self.client.is_enabled():
            return

        try:
            props = {"type": test_type, "summary": summary, "name": summary}
            props["label_display"] = f"Test ({test_type}): {summary}"
            if properties:
                props.update(properties)
            self.client.upsert_node(test_id, labels=["TestCase"], properties=props)
            logger.debug(f"GraphAgent: upsert_test_case {test_id}")
        except Exception:
            logger.warning(
                f"GraphAgent: failed to upsert test case {test_id}", exc_info=True
            )

    def get_tracked_issues(self) -> Dict[str, str]:
        """
        Recupera tutte le issue tracciate nel grafo (Story, Epic, JiraIssue).
        Returns: dict {key: status}
        """
        if not self.client.is_enabled():
            return {}

        tracked = {}
        try:
            # Match Generic JiraIssue or specific labels
            cypher = "MATCH (n) WHERE 'JiraIssue' IN labels(n) OR 'Story' IN labels(n) OR 'Epic' IN labels(n) RETURN n.id, n.status"
            results = self.client.query(cypher)
            # FalkorDB compact format: [header, [data_rows], stats]
            # Scalar values are [type_code, value] pairs
            data_rows = results[1] if results and len(results) > 1 else []
            for row in data_rows:
                if not isinstance(row, list) or len(row) < 2:
                    continue
                key_v, status_v = row[0], row[1]
                key = key_v[1] if isinstance(key_v, list) and len(key_v) >= 2 else key_v
                status = (
                    status_v[1]
                    if isinstance(status_v, list) and len(status_v) >= 2
                    else status_v
                )
                if key:
                    tracked[str(key)] = str(status) if status else "Unknown"
        except Exception:
            logger.error("GraphAgent: failed to get tracked issues", exc_info=True)
        return tracked

    def update_issue_status(self, issue_key: str, new_status: str) -> None:
        """Aggiorna lo stato di una issue esistente nel grafo."""
        if not self.client.is_enabled():
            return

        try:
            # We don't want to change labels, just property
            query = "MATCH (n {id: $id}) SET n.status = $status"
            self.client.query(query, {"id": issue_key, "status": new_status})
            logger.info(f"GraphAgent: updated status for {issue_key} -> {new_status}")
        except Exception:
            logger.error(
                f"GraphAgent: failed to update status for {issue_key}", exc_info=True
            )

    # --- Metadata Entity Operations ---

    def upsert_stakeholder(
        self,
        name: str,
        *,
        role: Optional[str] = None,
        email: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source_document_id: Optional[str] = None,
    ) -> str:
        """Create or update a Stakeholder node."""
        if not self.client.is_enabled() or not name:
            return ""

        try:
            stakeholder_id = self._build_entity_id(
                "stakeholder", name, source_document_id=source_document_id
            )
            props = dict(properties or {})
            props["name"] = name
            props["canonical_name"] = name
            props["entity_key"] = self._normalize_id(name)
            display_role = f" ({role})" if role else ""
            props["label_display"] = f"{name}{display_role}"
            if role:
                props["role"] = role
            if email:
                props["email"] = email
            self._apply_entity_scope(props, source_document_id)

            self.client.upsert_node(
                stakeholder_id, labels=["Stakeholder"], properties=props
            )
            logger.debug(f"GraphAgent: upserted stakeholder {name}")
            return stakeholder_id
        except Exception:
            logger.warning(
                f"GraphAgent: failed to upsert stakeholder {name}", exc_info=True
            )
            return ""

    def upsert_milestone(
        self,
        name: str,
        *,
        date: Optional[str] = None,
        description: Optional[str] = None,
        milestone_type: str = "Generic",
        status: str = "Planned",
        properties: Optional[Dict[str, Any]] = None,
        source_document_id: Optional[str] = None,
    ) -> str:
        """Create or update a Milestone node with rich metadata."""
        if not self.client.is_enabled() or not name:
            return ""

        try:
            milestone_key = f"{name}|{date or ''}|{milestone_type}"
            milestone_id = self._build_entity_id(
                "milestone", milestone_key, source_document_id=source_document_id
            )
            props = dict(properties or {})
            props["name"] = name
            props["canonical_name"] = name
            props["entity_key"] = self._normalize_id(milestone_key)
            display_date = f" ({date})" if date else ""
            props["label_display"] = f"{name}{display_date}"
            if date:
                props["target_date"] = date
            if description:
                props["description"] = description

            # Rich metadata
            props["type"] = milestone_type
            props["status"] = status
            self._apply_entity_scope(props, source_document_id)

            self.client.upsert_node(
                milestone_id, labels=["Milestone"], properties=props
            )
            logger.debug(f"GraphAgent: upserted milestone {name}")
            return milestone_id
        except Exception:
            logger.warning(
                f"GraphAgent: failed to upsert milestone {name}", exc_info=True
            )
            return ""

    def upsert_technology(
        self,
        name: str,
        *,
        category: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source_document_id: Optional[str] = None,
    ) -> str:
        """Create or update a Technology node."""
        if not self.client.is_enabled() or not name:
            return ""

        try:
            tech_id = self._build_entity_id(
                "technology", name, source_document_id=source_document_id
            )
            props = dict(properties or {})
            props["name"] = name
            props["canonical_name"] = name
            props["entity_key"] = self._normalize_id(name)
            display_cat = f" ({category})" if category else ""
            props["label_display"] = f"{name}{display_cat}"
            if category:
                props["category"] = category
            self._apply_entity_scope(props, source_document_id)

            self.client.upsert_node(tech_id, labels=["Technology"], properties=props)
            logger.debug(f"GraphAgent: upserted technology {name}")
            return tech_id
        except Exception:
            logger.warning(
                f"GraphAgent: failed to upsert technology {name}", exc_info=True
            )
            return ""

    def upsert_risk(
        self,
        description: str,
        *,
        severity: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source_document_id: Optional[str] = None,
    ) -> str:
        """Create or update a Risk node."""
        if not self.client.is_enabled() or not description:
            return ""

        try:
            risk_id = self._build_entity_id(
                "risk", description, source_document_id=source_document_id
            )
            props = dict(properties or {})
            props["description"] = description
            props["canonical_description"] = description
            props["entity_key"] = self._normalize_id(description)

            # Generate a short name/title for the node
            # If description is short, use it. If long, truncate.
            if len(description) < 50:
                props["name"] = description
            else:
                props["name"] = " ".join(description.split()[:8]) + "..."

            display_risk = (
                description[:50] + "..." if len(description) > 50 else description
            )
            props["label_display"] = f"Risk: {display_risk}"

            if severity:
                props["severity"] = severity
            self._apply_entity_scope(props, source_document_id)

            self.client.upsert_node(risk_id, labels=["Risk"], properties=props)
            logger.debug(f"GraphAgent: upserted risk {risk_id}")
            return risk_id
        except Exception:
            logger.warning("GraphAgent: failed to upsert risk", exc_info=True)
            return ""

    def upsert_topic(
        self,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
        source_document_id: Optional[str] = None,
    ) -> str:
        """Create or update a generic Topic/Concept node."""
        if not self.client.is_enabled() or not name:
            return ""

        try:
            topic_id = self._build_entity_id(
                "topic", name, source_document_id=source_document_id
            )
            props = dict(properties or {})
            props["name"] = name
            props["canonical_name"] = name
            props["entity_key"] = self._normalize_id(name)
            props["label_display"] = name
            self._apply_entity_scope(props, source_document_id)

            self.client.upsert_node(topic_id, labels=["Topic"], properties=props)
            logger.debug(f"GraphAgent: upserted topic {name}")
            return topic_id
        except Exception:
            logger.warning(f"GraphAgent: failed to upsert topic {name}", exc_info=True)
            return ""

    @staticmethod
    def _normalize_id(name: str) -> str:
        """Normalize a name to create a stable ID."""
        normalized = name.lower().strip().replace(" ", "-")
        normalized = "".join(c for c in normalized if c.isalnum() or c == "-")
        return normalized[:50]

    @staticmethod
    def _stable_hash(value: str, length: int = 12) -> str:
        return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]

    @classmethod
    def _build_entity_id(
        cls,
        entity_kind: str,
        raw_value: str,
        *,
        source_document_id: Optional[str] = None,
    ) -> str:
        entity_key = cls._normalize_id(raw_value)
        if source_document_id:
            doc_key = cls._stable_hash(source_document_id)
            return f"{entity_kind}:{doc_key}:{entity_key}"
        return f"{entity_kind}:{entity_key}"

    @staticmethod
    def _apply_entity_scope(
        props: Dict[str, Any], source_document_id: Optional[str]
    ) -> None:
        # Propaga il tenant corrente su ogni entità metadata (Topic, Stakeholder,
        # Milestone, Technology, ...) per consentirne il filtraggio cross-tenant.
        from agent_jira.tenant_context import get_current_tenant_id

        tenant_id = get_current_tenant_id()
        if tenant_id and not props.get("tenant_id"):
            props["tenant_id"] = tenant_id

        if source_document_id:
            props["scope"] = "document"
            props["source_document_id"] = source_document_id
        else:
            props.setdefault("scope", "global")
