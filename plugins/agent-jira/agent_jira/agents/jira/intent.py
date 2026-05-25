import logging
from typing import List

from agent_jira.agents.graph.relationship_detector import RelationshipDetector

logger = logging.getLogger(__name__)


def create_intelligent_relationships(
    stories: List, graph_agent=None, similarity_threshold: float = 0.85
) -> None:
    """
    Detect and create intelligent relationships between user stories.
    """
    if not graph_agent or not stories:
        return

    try:
        detector = RelationshipDetector(similarity_threshold=similarity_threshold)
        relationships = []

        # Filter stories that have Jira keys
        valid_stories = [
            s for s in stories if hasattr(s, "jira_issue_key") and s.jira_issue_key
        ]

        if len(valid_stories) < 2:
            logger.info("Jira/intent: not enough stories for relationship detection")
            return

        for story in valid_stories:
            # Detect blocking dependencies
            blocks = detector.detect_blocking_dependencies(story, valid_stories)
            for blocked_key, reason in blocks:
                relationships.append(
                    {
                        "from_story_id": story.jira_issue_key,
                        "to_story_id": blocked_key,
                        "relationship_type": "BLOCKS",
                        "properties": {"reason": reason, "detected_at": "auto"},
                    }
                )

            # Detect complementary stories
            complements = detector.detect_complementary_stories(story, valid_stories)
            for complement_key, shared_concepts in complements:
                relationships.append(
                    {
                        "from_story_id": story.jira_issue_key,
                        "to_story_id": complement_key,
                        "relationship_type": "COMPLEMENTS",
                        "properties": {
                            "shared_concepts": ",".join(
                                shared_concepts[:5]
                            ),  # Limit to 5
                            "detected_at": "auto",
                        },
                    }
                )

            # Detect semantic similarity
            similar = detector.detect_semantic_similarity(story, valid_stories)
            for similar_key, score in similar:
                relationships.append(
                    {
                        "from_story_id": story.jira_issue_key,
                        "to_story_id": similar_key,
                        "relationship_type": "RELATES_TO",
                        "properties": {
                            "similarity_score": score,
                            "detected_at": "auto",
                        },
                    }
                )

        # Create relationships in batch
        if relationships:
            logger.info(
                f"Jira/intent: creating {len(relationships)} intelligent relationships"
            )
            graph_agent.create_story_relationships_batch(relationships)
        else:
            logger.info("Jira/intent: no intelligent relationships detected")

    except Exception:
        logger.error(
            "Jira/intent: failed to create intelligent relationships", exc_info=True
        )
