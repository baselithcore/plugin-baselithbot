from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ProjectContext:
    """Rich project metadata extracted from documents."""

    goals: List[str] = field(default_factory=list)
    stakeholders: List[Dict[str, str]] = field(
        default_factory=list
    )  # {name, role, email}
    timeline: List[Dict[str, str]] = field(
        default_factory=list
    )  # [{name, date, type, status, description}]
    technologies: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    modules: List[str] = field(default_factory=list)
    integrations: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    business_rules: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    budget_info: Dict[str, Any] = field(default_factory=dict)
    semantic_relationships: List[Dict[str, Any]] = field(default_factory=list)
    associated_jira_projects: List[str] = field(default_factory=list)
    domain: Optional[str] = None

    def signal_count(self) -> int:
        """Returns how many structured metadata areas were populated."""
        buckets = (
            self.goals,
            self.stakeholders,
            self.timeline,
            self.technologies,
            self.risks,
            self.modules,
            self.integrations,
            self.constraints,
            self.business_rules,
            self.assumptions,
            self.open_questions,
            self.associated_jira_projects,
        )
        return sum(1 for bucket in buckets if bucket) + int(bool(self.domain))

    def to_search_metadata(self) -> Dict[str, str]:
        """Flattens the most relevant structured metadata for retrieval payloads."""
        data: Dict[str, str] = {}
        if self.domain:
            data["domain"] = self.domain
        if self.associated_jira_projects:
            data["doc_projects"] = ", ".join(self.associated_jira_projects)
        if self.goals:
            data["doc_goals"] = "; ".join(self.goals[:3])
        if self.modules:
            data["doc_modules"] = ", ".join(self.modules[:5])
        if self.integrations:
            data["doc_integrations"] = ", ".join(self.integrations[:5])
        if self.constraints:
            data["doc_constraints"] = "; ".join(self.constraints[:3])
        if self.business_rules:
            data["doc_business_rules"] = "; ".join(self.business_rules[:3])
        return data

    def to_planning_brief(self) -> str:
        """Builds a concise, planner-oriented brief from structured metadata."""
        sections: List[tuple[str, List[str]]] = []

        if self.domain:
            sections.append(("Dominio", [self.domain]))
        if self.goals:
            sections.append(("Obiettivi", self.goals[:5]))
        if self.modules:
            sections.append(("Moduli/Funzionalita", self.modules[:8]))
        if self.stakeholders:
            stakeholder_lines = []
            for stakeholder in self.stakeholders[:8]:
                name = stakeholder.get("name", "").strip()
                role = stakeholder.get("role", "").strip()
                if not name:
                    continue
                stakeholder_lines.append(f"{name} ({role})" if role else name)
            if stakeholder_lines:
                sections.append(("Stakeholder", stakeholder_lines))
        if self.integrations:
            sections.append(("Integrazioni", self.integrations[:6]))
        if self.constraints:
            sections.append(("Vincoli", self.constraints[:6]))
        if self.business_rules:
            sections.append(("Regole business", self.business_rules[:6]))
        if self.risks:
            sections.append(("Rischi", self.risks[:6]))
        if self.open_questions:
            sections.append(("Punti da chiarire", self.open_questions[:6]))
        if self.assumptions:
            sections.append(("Assunzioni", self.assumptions[:4]))

        if not sections:
            return ""

        lines = [
            "### Metadati strutturati del documento",
            "Usa questo brief come scheletro dell'analisi funzionale e delle user story.",
        ]
        for title, values in sections:
            lines.append(f"- {title}:")
            lines.extend(f"  * {value}" for value in values if value)
        return "\n".join(lines)


@dataclass
class QueryMetadata:
    """Metadata extracted from user query."""

    feature_module: Optional[str] = None
    priority: Optional[str] = None  # urgent, high, medium, low
    request_type: Optional[str] = None  # stories, tests, analysis
    mentioned_stakeholders: List[str] = field(default_factory=list)
    quantity: Optional[int] = None


class UsageTracker:
    """Tracks document usage patterns."""

    @staticmethod
    def create_usage_update(
        doc_id: str, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "doc_id": doc_id,
            "accessed_at": datetime.utcnow().isoformat(),
            "query": query[:200],  # Truncate long queries
            "context": context or {},
        }
