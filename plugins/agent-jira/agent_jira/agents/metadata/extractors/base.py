# app/agents/metadata/extractors/logic.py
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from ..models import ProjectContext
from . import patterns

logger = logging.getLogger(__name__)


class ProjectContextExtractor:
    """Extracts project metadata from document text (Fast Path)."""

    def extract_from_text(
        self, text: str, associated_projects: Optional[List[str]] = None
    ) -> ProjectContext:
        """
        Extract comprehensive project metadata from document text.
        """
        context = ProjectContext()
        if associated_projects:
            context.associated_jira_projects = associated_projects

        context.goals = self._extract_goals(text)
        context.stakeholders = self._extract_stakeholders(text)
        context.timeline = self._extract_timeline(text)
        context.technologies = self._extract_technologies(text)
        context.risks = self._extract_risks(text)
        context.modules = self._extract_modules(text)
        context.integrations = self._extract_integrations(text)
        context.constraints = self._extract_constraints(text)
        context.business_rules = self._extract_business_rules(text)
        context.assumptions = self._extract_assumptions(text)
        context.open_questions = self._extract_open_questions(text)

        # Infer domain
        context.domain = self._infer_domain(text)

        logger.info(
            f"Extracted project context (Regex): {len(context.goals)} goals, "
            f"{len(context.stakeholders)} stakeholders, "
            f"{len(context.technologies)} technologies"
        )

        return context

    def extract_from_analysis_file(self, analysis_path: Path) -> List[str]:
        """
        Extract project keys from a sibling .analysis.json file.
        """
        if not analysis_path.exists():
            return []

        try:
            data = json.loads(analysis_path.read_text(encoding="utf-8"))
            jira_results = data.get("jira", {}).get("results", [])
            keys = set()
            for issue in jira_results:
                key = issue.get("key")
                if isinstance(key, str) and "-" in key:
                    project_key = key.split("-")[0].upper()
                    keys.add(project_key)
            return list(keys)
        except Exception as e:
            logger.warning(f"Failed to extract projects from {analysis_path}: {e}")
            return []

    def _extract_goals(self, text: str) -> List[str]:
        """Extract project goals/objectives."""
        goals = []
        for keyword in patterns.GOAL_KEYWORDS:
            pattern = rf"{keyword}[:\s]+([^.!?\n]+)"
            matches = re.findall(pattern, text, re.IGNORECASE)
            goals.extend([m.strip() for m in matches if len(m.strip()) > 10])

        obiettivi_section = re.search(
            r"(?:Obiettivi|Goals)[:\s]*\n((?:[-*•]\s+.+\n?)+)", text, re.IGNORECASE
        )
        if obiettivi_section:
            bullets = re.findall(r"[-*•]\s+(.+)", obiettivi_section.group(1))
            goals.extend([b.strip() for b in bullets])

        return list(set(goals))[:10]

    def _extract_stakeholders(self, text: str) -> List[Dict[str, str]]:
        """Extract stakeholders using regex."""
        stakeholders = []
        seen = set()

        for pattern in patterns.STAKEHOLDER_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                name = None
                role = "Unknown"

                if isinstance(match, tuple):
                    if len(match) == 2:
                        name_candidate, role_candidate = match
                        name = name_candidate.strip()
                        role = role_candidate.strip("()")
                    elif len(match) == 1:
                        val = match[0].strip()
                        if "@" in val:
                            stakeholders.append(
                                {"name": val.split("@")[0], "email": val}
                            )
                            seen.add(val)
                            continue
                        else:
                            name = val
                            role = "Team"
                else:
                    val = match.strip() if isinstance(match, str) else match[0].strip()
                    if "," in val and " " in val:  # List
                        names = [n.strip() for n in val.split(",")]
                        for n in names:
                            if n and n not in seen:
                                # Basic validation
                                if any(
                                    bad in n.lower() for bad in patterns.BLACKLIST_TERMS
                                ):
                                    continue
                                if any(
                                    t.lower() == n.lower()
                                    for t in patterns.TECH_KEYWORDS
                                ):
                                    continue
                                stakeholders.append({"name": n, "role": role})
                                seen.add(n)
                        continue

                    elif "@" in val:
                        stakeholders.append({"name": val.split("@")[0], "email": val})
                        seen.add(val)
                        continue
                    else:
                        name = val

                # Validation
                if name and name not in seen:
                    # Check blacklist
                    if any(bad in name.lower() for bad in patterns.BLACKLIST_TERMS):
                        continue
                    if any(t.lower() == name.lower() for t in patterns.TECH_KEYWORDS):
                        continue

                    stakeholders.append({"name": name, "role": role})
                    seen.add(name)

        return stakeholders[:20]

    def _extract_timeline(self, text: str) -> List[Dict[str, str]]:
        """
        Extract timeline information (fast path).
        Returns list of rich milestone objects (defaulting missing fields).
        """
        timeline = []
        seen_keys = set()
        counter = 1

        for pattern in patterns.TIMELINE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:10]:
                match_text = match
                if isinstance(match, tuple):
                    match_text = next((g for g in match if g), "")

                if not match_text:
                    continue

                clean_match = match_text.strip()
                # Heuristic naming
                is_named = any(
                    k in clean_match.lower()
                    for k in ["release", "mvp", "alpha", "beta", "go-live"]
                )

                if is_named:
                    name = clean_match
                    date_val = clean_match  # regex match acts as both often
                else:
                    if len(clean_match) < 30:
                        name = f"Milestone {clean_match}"
                        date_val = clean_match
                    else:
                        name = f"Milestone {counter}"
                        date_val = clean_match
                        counter += 1

                if name not in seen_keys:
                    timeline.append(
                        {
                            "name": name,
                            "date": date_val,
                            "type": "Generic",  # Default for regex
                            "status": "Planned",  # Default for regex
                            "description": "Estratto dal testo tramite regex",
                        }
                    )
                    seen_keys.add(name)

        return timeline

    def _extract_technologies(self, text: str) -> List[str]:
        technologies = []
        for tech in patterns.TECH_KEYWORDS:
            if re.search(rf"\b{re.escape(tech)}\b", text, re.IGNORECASE):
                technologies.append(tech)
        return list(set(technologies))

    def _extract_risks(self, text: str) -> List[str]:
        risks = []
        for keyword in patterns.RISK_KEYWORDS:
            pattern = rf"{keyword}[:\s]+([^.!?\n]+)"
            matches = re.findall(pattern, text, re.IGNORECASE)
            risks.extend([m.strip() for m in matches if len(m.strip()) > 10])
        return list(set(risks))[:10]

    def _extract_modules(self, text: str) -> List[str]:
        modules = self._extract_bullet_section(
            text, [r"moduli", r"funzionalità", r"funzionalita", r"scope applicativo"]
        )
        for pattern in patterns.MODULE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                candidate = match.strip()
                if len(candidate) < 4:
                    continue
                if any(term in candidate.lower() for term in patterns.BLACKLIST_TERMS):
                    continue
                modules.append(candidate)
        return self._dedupe_strings(modules, limit=10)

    def _extract_integrations(self, text: str) -> List[str]:
        integrations = []
        for pattern in patterns.INTEGRATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            integrations.extend(match.strip() for match in matches if match.strip())

        section_lines = self._extract_bullet_section(
            text, [r"integrazioni", r"sistemi esterni", r"interfacce", r"dipendenze"]
        )
        integrations.extend(section_lines)
        return self._dedupe_strings(integrations, limit=8)

    def _extract_constraints(self, text: str) -> List[str]:
        constraints = self._extract_lines_by_keywords(
            text, patterns.CONSTRAINT_KEYWORDS, max_items=8
        )
        constraints.extend(
            self._extract_bullet_section(
                text, [r"vincoli", r"constraints", r"non functional", r"nfr"]
            )
        )
        return self._dedupe_strings(constraints, limit=8)

    def _extract_business_rules(self, text: str) -> List[str]:
        rules = self._extract_lines_by_keywords(
            text, patterns.BUSINESS_RULE_KEYWORDS, max_items=8
        )
        rules.extend(
            self._extract_bullet_section(
                text, [r"regole", r"business rules", r"logica di business"]
            )
        )
        return self._dedupe_strings(rules, limit=8)

    def _extract_assumptions(self, text: str) -> List[str]:
        assumptions = self._extract_lines_by_keywords(
            text, patterns.ASSUMPTION_KEYWORDS, max_items=6
        )
        assumptions.extend(
            self._extract_bullet_section(
                text, [r"assunzioni", r"presupposti", r"assumptions"]
            )
        )
        return self._dedupe_strings(assumptions, limit=6)

    def _extract_open_questions(self, text: str) -> List[str]:
        questions = []
        for line in text.splitlines():
            cleaned = self._clean_line(line)
            if not cleaned:
                continue
            lower = cleaned.lower()
            if cleaned.endswith("?") or any(
                keyword in lower for keyword in patterns.OPEN_QUESTION_KEYWORDS
            ):
                questions.append(cleaned)

        questions.extend(
            self._extract_bullet_section(
                text, [r"domande aperte", r"open questions", r"punti aperti"]
            )
        )
        return self._dedupe_strings(questions, limit=8)

    def _extract_lines_by_keywords(
        self, text: str, keywords: List[str], *, max_items: int
    ) -> List[str]:
        results = []
        for line in text.splitlines():
            cleaned = self._clean_line(line)
            if not cleaned:
                continue
            lower = cleaned.lower()
            if any(keyword in lower for keyword in keywords):
                results.append(cleaned)
            if len(results) >= max_items:
                break
        return results

    def _extract_bullet_section(self, text: str, headers: List[str]) -> List[str]:
        for header in headers:
            pattern = rf"(?:{header})[:\s]*\n((?:\s*[-*•]\s+.+\n?)+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return [
                    self._clean_line(item)
                    for item in re.findall(r"\s*[-*•]\s+(.+)", match.group(1))
                    if self._clean_line(item)
                ]
        return []

    def _clean_line(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip(" -*•\t")
        return cleaned.strip()

    def _dedupe_strings(self, values: List[str], *, limit: int) -> List[str]:
        deduped = []
        seen = set()
        for value in values:
            cleaned = self._clean_line(value)
            if len(cleaned) < 4:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(cleaned)
            if len(deduped) >= limit:
                break
        return deduped

    def _infer_domain(self, text: str) -> Optional[str]:
        domains = {
            "finance": ["bank", "payment", "transaction", "invoice", "fintech"],
            "healthcare": ["patient", "medical", "health", "clinic", "hospital"],
            "ecommerce": ["shop", "cart", "checkout", "product", "order"],
            "education": ["student", "course", "learning", "school", "university"],
            "logistics": ["shipping", "delivery", "warehouse", "tracking"],
        }
        text_lower = text.lower()
        scores = {}
        for domain, keywords in domains.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[domain] = score
        if scores:
            return max(scores, key=scores.get)
        return None
