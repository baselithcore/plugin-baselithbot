"""
Intent Classifier Module

Handles classification of user intent from text input.
Supports keyword-based heuristics with future extensibility for LLM-based classification.
"""

from __future__ import annotations

import logging
from typing import Literal

from agent_jira.telemetry import telemetry

logger = logging.getLogger(__name__)

IntentType = Literal[
    "qa_docs",
    "jira_generation",
    "graph_impact",
    "graph_completeness",
    "system_status",
    "global_analysis",
]


class IntentClassifier:
    """
    Classifies user intent from text input using keyword-based heuristics.

    Future enhancement: Replace with LLM-based classification for better accuracy.
    """

    def classify(self, text: str) -> IntentType:
        """
        Classifies the user's intent from their input text.

        Args:
            text: User input text to classify

        Returns:
            Intent type: qa_docs, jira_generation, graph_impact, graph_completeness, or system_status
        """
        text_lower = text.lower()

        # 1. System Status
        if any(
            k in text_lower
            for k in [
                "quanti documenti",
                "che documenti",
                "quali documenti",
                "documenti hai",
                "documenti indicizzati",
                "stato del sistema",
                "file caricati",
                "quanti file",
                "quali file",
            ]
        ):
            intent = "system_status"
            telemetry.increment(f"orchestrator.intent.{intent}")
            logger.info("Detected intent: %s", intent)
            return intent

        # 2. Global Analysis (Map-Reduce)
        if any(
            k in text_lower
            for k in [
                "riassumi i documenti",
                "riassumi tutti",
                "confronta i file",
                "riassunto globale",
                "relazioni tra tutti",
                "riassumili",
                "sintetizzali",
                "confrontali",
            ]
        ):
            intent = "global_analysis"
            telemetry.increment(f"orchestrator.intent.{intent}")
            logger.info("Detected intent: %s", intent)
            return intent

        # 3. Jira Generation
        # Explicit Jira terms: direct match
        explicit_jira_terms = [
            "jira",
            "ticket",
            "backlog",
            "user story",
            "user stories",
            "storia utente",
            "storie utente",
            "epica",
            "epiche",
        ]
        # Generic creation verbs only count as Jira when paired with a Jira noun.
        creation_verbs = (
            "crea",
            "crei",
            "creare",
            "crealo",
            "creali",
            "genera",
            "generi",
            "generare",
            "generami",
            "pianifica",
            "pianificare",
            "pianifichi",
        )
        jira_nouns = (
            "jira",
            "ticket",
            "backlog",
            "storia",
            "storie",
            "story",
            "stories",
            "epica",
            "epiche",
            "sprint",
        )
        has_explicit = any(k in text_lower for k in explicit_jira_terms)
        has_verb_noun = any(v in text_lower for v in creation_verbs) and any(
            n in text_lower for n in jira_nouns
        )
        if has_explicit or has_verb_noun:
            intent = "jira_generation"
            telemetry.increment(f"orchestrator.intent.{intent}")
            logger.info("Detected intent: %s", intent)
            return intent

        # 4. Graph: Impact Analysis
        if any(
            k in text_lower
            for k in [
                "impatto",
                "impact analysis",
                "cosa succede se cambio",
                "traceability",
                "conseguenze",
                "dipende da",
                "rompere",
                "rovinare",
            ]
        ):
            intent = "graph_impact"
            telemetry.increment(f"orchestrator.intent.{intent}")
            logger.info("Detected intent: %s", intent)
            return intent

        # 5. Graph: Completeness
        if any(
            k in text_lower
            for k in [
                "completezza",
                "copertura",
                "coverage",
                "completeness",
                "ha storie",
                "ha test",
                "stato del progetto",
                "orfane",
                "senza test",
            ]
        ):
            intent = "graph_completeness"
            telemetry.increment(f"orchestrator.intent.{intent}")
            logger.info("Detected intent: %s", intent)
            return intent

        # 5. Default: Q&A on Documents
        intent = "qa_docs"
        telemetry.increment(f"orchestrator.intent.{intent}")
        logger.info("Detected intent: %s", intent)
        return intent
