"""
Intelligent Relationship Detector for Graph Relationships.

Detects semantic relationships between user stories using NLP and embeddings.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

try:
    from agent_jira.graphdb.relationship_schema import normalize_relationship_type
except Exception:  # pragma: no cover - fallback for partial module stubs in tests

    def normalize_relationship_type(value: str) -> str:
        normalized = str(value or "").strip().upper().replace(" ", "_")
        return normalized or "RELATED_TO"


if TYPE_CHECKING:
    from agent_jira.project_manager import UserStory

logger = logging.getLogger(__name__)


@dataclass
class SemanticEdge:
    source: str
    target: str
    relationship: str
    confidence: float = 1.0
    evidence: str | None = None


class RelationshipDetector:
    """Detects intelligent relationships between user stories."""

    # Keywords that indicate blocking dependencies
    BLOCKING_KEYWORDS = [
        r"\bdepends?\s+on\b",
        r"\bblocked?\s+by\b",
        r"\brequires?\b",
        r"\bprerequisite\b",
        r"\bneeds?\b.*\bfirst\b",
        r"\bafter\b.*\bcomplete",
        r"\bwaiting?\s+for\b",
    ]

    # Keywords that indicate complementary relationships
    COMPLEMENT_KEYWORDS = [
        r"\btogether\s+with\b",
        r"\balong\s+with\b",
        r"\bin\s+conjunction\s+with\b",
        r"\bcomplementary\s+to\b",
        r"\bworks?\s+with\b",
    ]

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize the relationship detector.

        Args:
            similarity_threshold: Minimum similarity score for RELATES_TO (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold

    def detect_semantic_relationships(self, text: str) -> List[SemanticEdge]:
        """
        Uses LLM to extract semantic relationships from text.
        Returns a list of SemanticEdge objects.
        """
        from agent_jira.llm import generate_response

        prompt = f"""
        SYSTEM
        Sei un analista di grafi di conoscenza. Il tuo compito è estrarre relazioni semantiche REALI tra entità basandoti esclusivamente sul testo fornito.

        REGOLE DI GROUNDING:
        1. NO INVENZIONE: Estrai solo relazioni esplicitamente menzionate o direttamente deducibili dalla logica del testo.
        2. EVIDENZA: Ogni relazione deve avere una "evidence" (una breve frase del testo) che la giustifichi.
        3. NO DOMINIO GENERALE: Non creare relazioni basandoti su come funzionano solitamente i progetti software, ma solo su come è descritto QUESTO progetto.
        4. TIPI AMMESSI: Usa solo DEPENDS_ON, BLOCKS, RELATED_TO, MODIFIES, TRIGGERS.
        5. LINGUA: Estrai source, target e evidence mantenendo la lingua del documento (Italiano).

        TASK
        Analizza il testo ed estrai un elenco di relazioni per un Knowledge Graph.

        Testo:
        "{text[:2000]}"

        Restituisci SOLO un array JSON di oggetti con i seguenti campi:
        - "source": Entità soggetto
        - "target": Entità oggetto
        - "relationship": Uno dei tipi ammessi sopra
        - "confidence": Float tra 0.0 e 1.0
        - "evidence": La frase esatta o il frammento che prova la relazione (max 140 char)

        Se non trovi relazioni certe, restituisci [].
        """

        try:
            response = generate_response(prompt)
            # Basic cleanup if Markdown is returned
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            import json

            data = json.loads(response.strip())

            edges = []
            for item in data:
                if "source" in item and "target" in item and "relationship" in item:
                    source = str(item["source"]).strip()
                    target = str(item["target"]).strip()
                    if not source or not target or source == target:
                        continue
                    rel = normalize_relationship_type(item["relationship"])
                    confidence = item.get("confidence", 0.75)
                    try:
                        confidence = max(0.0, min(1.0, float(confidence)))
                    except (TypeError, ValueError):
                        confidence = 0.75
                    evidence = str(item.get("evidence", "")).strip() or None
                    edges.append(
                        SemanticEdge(
                            source=source,
                            target=target,
                            relationship=rel,
                            confidence=confidence,
                            evidence=evidence,
                        )
                    )
            unique_edges = {}
            for edge in edges:
                key = (edge.source.lower(), edge.target.lower(), edge.relationship)
                current = unique_edges.get(key)
                if current is None or edge.confidence > current.confidence:
                    unique_edges[key] = edge
            return list(unique_edges.values())
        except Exception as e:
            logger.warning(f"Failed to extract semantic relationships: {e}")
            return []

    def detect_blocking_dependencies(
        self, story: "UserStory", all_stories: List["UserStory"]
    ) -> List[Tuple[str, str]]:
        """
        Detect if a story blocks or is blocked by others.

        Returns:
            List of tuples: (blocked_story_key, reason)
        """
        blocks = []

        # Search in description and acceptance criteria
        search_text = f"{story.description} {' '.join(story.acceptance_criteria or [])}"

        for other_story in all_stories:
            if (
                not hasattr(other_story, "jira_issue_key")
                or not other_story.jira_issue_key
            ):
                continue
            if other_story.jira_issue_key == getattr(story, "jira_issue_key", None):
                continue

            # Check if this story mentions the other story's key
            if other_story.jira_issue_key in search_text:
                # Check for blocking keywords around the mention
                for pattern in self.BLOCKING_KEYWORDS:
                    if re.search(
                        f"{pattern}.*{re.escape(other_story.jira_issue_key)}",
                        search_text,
                        re.IGNORECASE,
                    ):
                        blocks.append(
                            (
                                other_story.jira_issue_key,
                                f"Depends on {other_story.jira_issue_key}",
                            )
                        )
                        break

        return blocks

    def detect_complementary_stories(
        self, story: "UserStory", all_stories: List["UserStory"]
    ) -> List[Tuple[str, List[str]]]:
        """
        Find stories that complement this one.

        Returns:
            List of tuples: (story_key, [shared_concepts])
        """
        complements = []

        # Extract key concepts from this story
        story_concepts = self._extract_concepts(story)

        for other_story in all_stories:
            if (
                not hasattr(other_story, "jira_issue_key")
                or not other_story.jira_issue_key
            ):
                continue
            if other_story.jira_issue_key == getattr(story, "jira_issue_key", None):
                continue

            # Check for explicit complement keywords
            search_text = (
                f"{story.description} {' '.join(story.acceptance_criteria or [])}"
            )
            for pattern in self.COMPLEMENT_KEYWORDS:
                if re.search(
                    f"{pattern}.*{re.escape(other_story.jira_issue_key)}",
                    search_text,
                    re.IGNORECASE,
                ):
                    complements.append(
                        (other_story.jira_issue_key, ["explicit_mention"])
                    )
                    break
            else:
                # Check for shared concepts
                other_concepts = self._extract_concepts(other_story)
                shared = story_concepts & other_concepts
                if len(shared) >= 2:  # At least 2 shared concepts
                    complements.append((other_story.jira_issue_key, list(shared)))

        return complements

    def detect_semantic_similarity(
        self,
        story: "UserStory",
        all_stories: List["UserStory"],
        embeddings: Optional[Dict[str, List[float]]] = None,
    ) -> List[Tuple[str, float]]:
        """
        Detect semantically similar stories using embeddings.

        Args:
            story: The story to compare
            all_stories: All other stories
            embeddings: Optional pre-computed embeddings {story_key: embedding_vector}

        Returns:
            List of tuples: (story_key, similarity_score)
        """
        if not embeddings:
            # Fallback to simple text similarity if no embeddings provided
            return self._simple_text_similarity(story, all_stories)

        story_key = getattr(story, "jira_issue_key", None)
        if not story_key or story_key not in embeddings:
            return []

        story_embedding = embeddings[story_key]
        similar = []

        for other_story in all_stories:
            other_key = getattr(other_story, "jira_issue_key", None)
            if not other_key or other_key == story_key or other_key not in embeddings:
                continue

            # Compute cosine similarity
            similarity = self._cosine_similarity(story_embedding, embeddings[other_key])

            if similarity >= self.similarity_threshold:
                similar.append((other_key, similarity))

        return similar

    def _extract_concepts(self, story: "UserStory") -> set:
        """Extract key concepts from a story (simple keyword extraction)."""
        text = f"{story.title} {story.description} {story.goal or ''} {story.benefit or ''}"
        # Remove common words and extract meaningful terms
        words = re.findall(r"\b[a-z]{4,}\b", text.lower())
        # Filter out very common words (simple stopword removal)
        stopwords = {
            "user",
            "want",
            "need",
            "should",
            "must",
            "will",
            "can",
            "able",
            "that",
            "this",
            "with",
            "from",
            "have",
            "been",
            "were",
            "their",
            "would",
            "there",
            "about",
        }
        return {w for w in words if w not in stopwords}

    def _simple_text_similarity(
        self, story: "UserStory", all_stories: List["UserStory"]
    ) -> List[Tuple[str, float]]:
        """Simple Jaccard similarity fallback when embeddings are not available."""
        story_concepts = self._extract_concepts(story)
        similar = []

        for other_story in all_stories:
            other_key = getattr(other_story, "jira_issue_key", None)
            if not other_key or other_key == getattr(story, "jira_issue_key", None):
                continue

            other_concepts = self._extract_concepts(other_story)
            if not story_concepts or not other_concepts:
                continue

            # Jaccard similarity
            intersection = len(story_concepts & other_concepts)
            union = len(story_concepts | other_concepts)
            similarity = intersection / union if union > 0 else 0.0

            if similarity >= self.similarity_threshold:
                similar.append((other_key, similarity))

        return similar

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors using numpy."""
        import numpy as np

        if len(vec1) != len(vec2):
            return 0.0

        v1 = np.array(vec1, dtype=np.float32)
        v2 = np.array(vec2, dtype=np.float32)

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(v1, v2) / (norm1 * norm2))
